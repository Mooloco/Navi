import json
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

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(_connect()) as conn:
        conn.executescript(SCHEMA)  # 多条语句需 executescript


def list_services() -> list[dict]:
    """按自定义分类顺序 + 分类内 sort_order 排序返回。"""
    with closing(_connect()) as conn:
        rows = conn.execute("SELECT * FROM services").fetchall()
    services = [dict(r) for r in rows]
    try:
        cat_order = json.loads(get_setting("category_order") or "[]")
    except json.JSONDecodeError:
        cat_order = []
    rank = {c: i for i, c in enumerate(cat_order)}
    services.sort(key=lambda s: (rank.get(s["category"], 10**9), s["sort_order"], s["id"]))
    return services


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


def get_setting(key: str) -> str | None:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else None


def set_setting(key: str, value: str) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def reorder(categories: list[str], service_ids: dict[str, list[int]]) -> None:
    """保存分类顺序 + 各分类内服务顺序(单事务)。"""
    with closing(_connect()) as conn, conn:
        for cat, ids in service_ids.items():
            for i, sid in enumerate(ids):
                conn.execute(
                    "UPDATE services SET sort_order = ?, category = ? WHERE id = ?",
                    (i, cat, sid),
                )
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('category_order', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (json.dumps(categories, ensure_ascii=False),),
        )
