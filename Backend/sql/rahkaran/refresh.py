"""Refresh the accounting database from the backup drop folder (idempotent, safe to run on every start).

Drop the company's export (FULL_/DIFF_ .bak files, any sub-folder) into the backup folder (compose mounts it read-only at /backups) and run
this job. It:
  1. picks the newest FULL backup and the newest DIFF that belongs to it (checked via the backup LSNs);
  2. exits quietly if exactly those files were already loaded (marker table master.dbo.rahkaran_restore_state);
  3. restores them into a side database `<DB>_new`  (the live database is untouched while this runs);
  4. applies the `ai` semantic layer + the read-only login (apply.py) to the side database and smoke-tests it;
  5. swaps it in (drop old, rename new) and sets it READ_ONLY. Any failure before step 5 leaves the live database as it was.

Env: RAHKARAN_SA_PASSWORD (required), RAHKARAN_AI_PASSWORD (reader login password, required),
     RAHKARAN_HOST (mssql), RAHKARAN_PORT (1433), RAHKARAN_DB (MehvarGostar),
     RAHKARAN_BACKUP_LOCAL_DIR (/backups: where this process sees the files), RAHKARAN_BACKUP_SQL_DIR (/backups: where SQL Server sees them),
     RAHKARAN_SET_READ_ONLY (1).
Usage: python refresh.py [--dry-run] [--force]
"""
import os
import re
import subprocess
import sys
import time
from datetime import datetime

import pymssql

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("RAHKARAN_DB", "MehvarGostar")
NEW = f"{DB}_new"
HOST = os.environ.get("RAHKARAN_HOST", "mssql")
PORT = int(os.environ.get("RAHKARAN_PORT", "1433"))
LOCAL_DIR = os.environ.get("RAHKARAN_BACKUP_LOCAL_DIR", "/backups")
SQL_DIR = os.environ.get("RAHKARAN_BACKUP_SQL_DIR", "/backups")
NAME_RE = re.compile(r"_(FULL|DIFF)_(\d{8})_(\d{6})\.bak$", re.I)


def log(msg):
    print(f"[refresh {datetime.now():%H:%M:%S}] {msg}", flush=True)


def connect(db="master"):
    return pymssql.connect(HOST, user="sa", password=os.environ["RAHKARAN_SA_PASSWORD"], database=db, port=PORT,
                           charset="UTF-8", login_timeout=30, timeout=0, autocommit=True)


def wait_for_server(minutes=10):
    deadline = time.time() + minutes * 60
    while True:
        try:
            connect().close()
            return
        except Exception as e:
            if time.time() > deadline:
                raise SystemExit(f"SQL Server not reachable at {HOST}:{PORT}: {str(e)[:150]}")
            time.sleep(5)


def scan():
    """-> (fulls, diffs): lists of (timestamp, local_path) sorted ascending."""
    found = {"FULL": [], "DIFF": []}
    for root, _dirs, files in os.walk(LOCAL_DIR):
        for f in files:
            m = NAME_RE.search(f)
            if m:
                found[m.group(1).upper()].append((m.group(2) + m.group(3), os.path.join(root, f)))
    return sorted(found["FULL"]), sorted(found["DIFF"])


def sql_path(local_path):
    return SQL_DIR.rstrip("/") + "/" + os.path.relpath(local_path, LOCAL_DIR).replace(os.sep, "/")


def q(s):
    return "N'" + s.replace("'", "''") + "'"


def headeronly(cur, local_path):
    cur.execute(f"RESTORE HEADERONLY FROM DISK = {q(sql_path(local_path))}")
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, cur.fetchone()))


def choose(cur):
    fulls, diffs = scan()
    if not fulls:
        return None, None
    full_ts, full = fulls[-1]
    base_lsn = headeronly(cur, full)["CheckpointLSN"]
    for ts, d in reversed(diffs):
        if ts <= full_ts:
            break
        if headeronly(cur, d)["DifferentialBaseLSN"] == base_lsn:
            return full, d
    return full, None


def signature(full, diff):
    return "|".join(f"{os.path.basename(p)}:{os.path.getsize(p)}" for p in (full, diff) if p)


def run(cur, stmt):
    log(stmt.split("\n")[0][:110])
    cur.execute(stmt)
    while cur.nextset():
        pass


def main():
    dry = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    if not os.path.isdir(LOCAL_DIR) or not scan()[0]:
        log(f"no FULL backup found under {LOCAL_DIR} - nothing to do")
        return 0
    wait_for_server()
    master = connect()
    cur = master.cursor()
    full, diff = choose(cur)
    sig = signature(full, diff)
    log(f"selected FULL={os.path.basename(full)}  DIFF={os.path.basename(diff) if diff else '(none)'}")

    cur.execute("""IF OBJECT_ID('dbo.rahkaran_restore_state') IS NULL
                   CREATE TABLE dbo.rahkaran_restore_state (id int PRIMARY KEY, signature nvarchar(1000), restored_at datetime2)""")
    cur.execute("SELECT signature FROM dbo.rahkaran_restore_state WHERE id = 1")
    row = cur.fetchone()
    cur.execute("SELECT state_desc FROM sys.databases WHERE name = %s", (DB,))
    live = cur.fetchone()
    if not force and row and row[0] == sig and live and live[0] == "ONLINE":
        log("database is already up to date - nothing to do")
        return 0
    if dry:
        log("dry run: would restore the files above")
        return 0

    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    cur.execute("SELECT name FROM sys.databases WHERE name = %s", (NEW,))
    if cur.fetchone():
        run(cur, f"ALTER DATABASE [{NEW}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
        run(cur, f"DROP DATABASE [{NEW}]")
    cur.execute(f"RESTORE FILELISTONLY FROM DISK = {q(sql_path(full))}")
    files = [(r[0], r[2]) for r in cur.fetchall()]              # (LogicalName, Type)
    moves, i = [], 0
    for logical, ftype in files:
        i += 1
        ext = "ldf" if ftype == "L" else "mdf"
        moves.append(f"MOVE {q(logical)} TO {q(f'/var/opt/mssql/data/{DB}_{stamp}_{i}.{ext}')}")
    mode = "NORECOVERY" if diff else "RECOVERY"
    try:
        run(cur, f"RESTORE DATABASE [{NEW}] FROM DISK = {q(sql_path(full))}\nWITH {', '.join(moves)}, {mode}, STATS = 10")
        if diff:
            run(cur, f"RESTORE DATABASE [{NEW}] FROM DISK = {q(sql_path(diff))} WITH RECOVERY, STATS = 10")
        env = dict(os.environ, RAHKARAN_DB=NEW, RAHKARAN_HOST=HOST, RAHKARAN_PORT=str(PORT))
        log("applying the ai semantic layer to the new database (apply.py)")
        subprocess.run([sys.executable, os.path.join(HERE, "apply.py")], check=True, cwd=HERE, env=env)
        smoke_conn = connect(NEW)
        smoke = smoke_conn.cursor()
        smoke.execute("SELECT COUNT(*) FROM ai.view_catalog")
        n_views = smoke.fetchone()[0]
        smoke.execute("SELECT TOP 1 * FROM ai.data_freshness")
        log(f"smoke test ok: {n_views} documented views, data_freshness={smoke.fetchone()}")
        smoke_conn.close()
    except BaseException:
        log("FAILED before the swap - the live database was NOT changed; removing the half-restored copy")
        try:
            c2 = connect().cursor()
            c2.execute(f"IF DB_ID(N'{NEW}') IS NOT NULL BEGIN ALTER DATABASE [{NEW}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [{NEW}]; END")
        except Exception as e:
            log(f"cleanup failed: {str(e)[:150]}")
        raise

    # --- swap (the only moment the database is briefly unavailable). The old database is renamed aside first and
    # dropped only after the new one is live, so a failure here is rolled back to the previous database.
    old = f"{DB}_old"
    cur.execute(f"IF DB_ID(N'{old}') IS NOT NULL BEGIN ALTER DATABASE [{old}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [{old}]; END")
    cur.execute(f"SELECT DB_ID(N'{DB}'), (SELECT is_read_only FROM sys.databases WHERE name = N'{DB}')")
    live_id, was_ro = cur.fetchone()
    had_old = live_id is not None
    try:
        run(cur, f"ALTER DATABASE [{NEW}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
        if had_old:
            if was_ro:      # a READ_ONLY database cannot be renamed (no checkpoint possible)
                run(cur, f"ALTER DATABASE [{DB}] SET READ_WRITE WITH ROLLBACK IMMEDIATE")
            run(cur, f"ALTER DATABASE [{DB}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
            run(cur, f"ALTER DATABASE [{DB}] MODIFY NAME = [{old}]")
        run(cur, f"ALTER DATABASE [{NEW}] MODIFY NAME = [{DB}]")
    except BaseException:
        log("swap failed - restoring the previous database")
        try:
            cur.execute(f"IF DB_ID(N'{DB}') IS NULL AND DB_ID(N'{old}') IS NOT NULL ALTER DATABASE [{old}] MODIFY NAME = [{DB}]")
            if had_old:
                cur.execute(f"ALTER DATABASE [{DB}] SET MULTI_USER")
                if was_ro:
                    cur.execute(f"ALTER DATABASE [{DB}] SET READ_ONLY WITH ROLLBACK IMMEDIATE")
            cur.execute(f"IF DB_ID(N'{NEW}') IS NOT NULL BEGIN ALTER DATABASE [{NEW}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [{NEW}]; END")
        except Exception as e:
            log(f"rollback incomplete, check the server manually: {str(e)[:150]}")
        raise
    run(cur, f"ALTER DATABASE [{DB}] SET MULTI_USER")
    if os.environ.get("RAHKARAN_SET_READ_ONLY", "1") == "1":
        run(cur, f"ALTER DATABASE [{DB}] SET READ_ONLY WITH ROLLBACK IMMEDIATE")
    if had_old:
        cur.execute(f"ALTER DATABASE [{old}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [{old}]")
        log("dropped the previous database")
    cur.execute("DELETE FROM dbo.rahkaran_restore_state WHERE id = 1")
    cur.execute("INSERT INTO dbo.rahkaran_restore_state (id, signature, restored_at) VALUES (1, %s, SYSUTCDATETIME())", (sig,))
    log("done - the new data is live")
    return 0


if __name__ == "__main__":
    sys.exit(main())
