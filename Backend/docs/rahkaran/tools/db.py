"""Connection helper for exploring the restored Rahkaran DB (read-only use).

Env: RAHKARAN_SA_PASSWORD (required), RAHKARAN_HOST (default 127.0.0.1), RAHKARAN_PORT (default 14330).
Needs: pip install pymssql   (use a scratch venv, not the project's requirements)
"""
import os
import pymssql


def conn():
    return pymssql.connect(
        os.environ.get("RAHKARAN_HOST", "127.0.0.1"),
        user="sa",
        password=os.environ["RAHKARAN_SA_PASSWORD"],
        database="MehvarGostar",
        port=int(os.environ.get("RAHKARAN_PORT", "14330")),
        charset="UTF-8",
        login_timeout=30,
    )


def q(sql, args=None):
    c = conn()
    cur = c.cursor(as_dict=True)
    cur.execute(sql, args or ())
    rows = cur.fetchall()
    c.close()
    return rows
