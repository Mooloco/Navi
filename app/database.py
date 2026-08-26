import os
import sqlite3
from contextlib import closing
from pathlib import Path

DEFAULT_DB = str(Path(__file__).resolve().parent.parent / "data" / "nav.db")
DB_PATH = Path(os.environ.get("MOOLO_NAV_DB", DEFAULT_DB))

SCHEMA = """
CREATE TABLE IF NOT EXISTS services (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    url         TEXT NOT NULL,
    description TEXT DEFAULT '',
    icon        TEXT DEFAULT '',
    category    TEXT DEFAULT '其他',
    sort_order  INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now', 'localtime'))
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(SCHEMA)


def list_services() -> list[dict]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM services ORDER BY category, sort_order, id"
        ).fetchall()
    return [dict(r) for r in rows]


def get_service(sid: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM services WHERE id = ?", (sid,)
        ).fetchone()
    return dict(row) if row else None


def add_service(data: dict) -> dict:
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            """INSERT INTO services (name, url, description, icon, category)
               VALUES (:name, :url, :description, :icon, :category)""",
            data,
        )
        sid = cur.lastrowid
    return get_service(sid)


def update_service(sid: int, data: dict) -> dict | None:
    if not data:
        return get_service(sid)
    fields = ", ".join(f"{k} = :{k}" for k in data)
    params = {**data, "id": sid}
    with closing(_connect()) as conn, conn:
        cur = conn.execute(f"UPDATE services SET {fields} WHERE id = :id", params)
        if cur.rowcount == 0:
            return None
    return get_service(sid)


def delete_service(sid: int) -> bool:
    with closing(_connect()) as conn, conn:
        cur = conn.execute("DELETE FROM services WHERE id = ?", (sid,))
    return cur.rowcount > 0


def replace_all(services: list[dict]) -> int:
    """导入:清空后整批写入(事务)。"""
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM services")
        conn.executemany(
            """INSERT INTO services (name, url, description, icon, category)
               VALUES (:name, :url, :description, :icon, :category)""",
            services,
        )
    return len(services)
