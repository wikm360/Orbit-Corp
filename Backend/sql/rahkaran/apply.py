"""Apply the Rahkaran semantic layer (ai schema) to a restored MehvarGostar database.

Usage:  RAHKARAN_SA_PASSWORD=... python apply.py [file_prefix ...]
Env: RAHKARAN_HOST (127.0.0.1), RAHKARAN_PORT (14330), RAHKARAN_DB (MehvarGostar).
Executes every NN_*.sql in order (batches split on lines containing only GO), then applies descriptions.py
(extended properties MS_Description on views/columns). If the database is READ_ONLY it is switched to READ_WRITE
for the duration of the run and switched back afterwards.
"""
import os, re, sys, glob
import pymssql

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("RAHKARAN_DB", "MehvarGostar")


def connect(db):
    return pymssql.connect(os.environ.get("RAHKARAN_HOST", "127.0.0.1"), user="sa", password=os.environ["RAHKARAN_SA_PASSWORD"],
                           database=db, port=int(os.environ.get("RAHKARAN_PORT", "14330")), charset="UTF-8",
                           login_timeout=30, autocommit=True)


def setup_reader(master, db_conn):
    """Create the least-privilege login/user the application connects with: SELECT on schema ai only.
    Views are owned by dbo like the base tables, so ownership chaining lets them read FIN3/HCM3/... without direct rights."""
    pw = os.environ.get("RAHKARAN_AI_PASSWORD")
    if not pw:
        return
    user = os.environ.get("RAHKARAN_AI_USER", "rahkaran_ai_reader")
    mc = master.cursor()
    mc.execute(f"IF SUSER_ID(N'{user}') IS NULL CREATE LOGIN [{user}] WITH PASSWORD = %s, CHECK_POLICY = OFF, DEFAULT_DATABASE = [{DB}]", (pw,))
    mc.execute(f"ALTER LOGIN [{user}] WITH PASSWORD = %s, CHECK_POLICY = OFF", (pw,))
    c = db_conn.cursor()
    c.execute(f"IF USER_ID(N'{user}') IS NOT NULL DROP USER [{user}]")
    c.execute(f"CREATE USER [{user}] FOR LOGIN [{user}] WITH DEFAULT_SCHEMA = [ai]")
    c.execute(f"GRANT SELECT ON SCHEMA::ai TO [{user}]")
    print(f"reader user {user}: SELECT on schema ai")


def main():
    prefixes = sys.argv[1:]
    master = connect("master")
    cur = master.cursor()
    cur.execute("SELECT is_read_only FROM sys.databases WHERE name = %s", (DB,))
    was_ro = bool(cur.fetchone()[0])
    if was_ro:
        cur.execute(f"ALTER DATABASE [{DB}] SET READ_WRITE WITH ROLLBACK IMMEDIATE")
    if os.environ.get("RAHKARAN_SKIP_TF4138") != "1":
        # Trace flag 4138 disables the "row goal" optimization. Without it, TOP n ... ORDER BY queries over the fact views can pick a
        # catastrophic nested-loop plan (60 s instead of 0.1 s). It is server-wide and lost on restart; production alternative: append
        # OPTION (USE HINT('DISABLE_OPTIMIZER_ROWGOAL')) to every generated query. See sql/rahkaran/README.md.
        try:
            cur.execute("DBCC TRACEON (4138, -1)")
            print("trace flag 4138 enabled (server-wide)")
        except Exception as e:
            print("could not enable trace flag 4138:", str(e)[:100])
    try:
        conn = connect(DB)
        c = conn.cursor()
        files = sorted(glob.glob(os.path.join(HERE, "[0-9][0-9]_*.sql")))
        for f in files:
            if prefixes and not any(os.path.basename(f).startswith(p) for p in prefixes):
                continue
            text = open(f, encoding="utf-8").read()
            batches = [b.strip() for b in re.split(r"^\s*GO\s*$", text, flags=re.M | re.I) if b.strip()]
            for i, b in enumerate(batches, 1):
                try:
                    c.execute(b)
                except Exception as e:
                    print(f"FAILED {os.path.basename(f)} batch {i}: {str(e)[:400]}\n---\n{b[:300]}")
                    raise
            print(f"applied {os.path.basename(f)} ({len(batches)} batches)")
        if not prefixes or "descr" in prefixes:
            import descriptions
            descriptions.apply(conn)
        if not prefixes or "sec" in prefixes:
            setup_reader(master, conn)
    finally:
        if was_ro:
            cur.execute(f"ALTER DATABASE [{DB}] SET READ_ONLY WITH ROLLBACK IMMEDIATE")
        master.close()


if __name__ == "__main__":
    main()
