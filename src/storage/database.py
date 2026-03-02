###
# storage/database.py — SQLite 連線管理與 schema 初始化
#
# 用途：管理 aiosqlite 連線，初始化 sessions / messages / user_memories 三張表
# 主要功能：
#   - init_db(db_path) 初始化 schema（含 migration）
#   - get_db() 取得全域 db 連線
# 關聯：被 session/session.py, session/memory.py, api/ 引用
###

import aiosqlite

_db: aiosqlite.Connection | None = None

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    provider    TEXT NOT NULL,
    title       TEXT,
    project_dir TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_memories (
    session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (session_id, key)
);
"""


async def _migrate_user_memories(db: aiosqlite.Connection):
    """偵測舊表有 user_id 欄位則 DROP 重建"""
    cursor = await db.execute("PRAGMA table_info(user_memories)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "user_id" in columns:
        await db.execute("DROP TABLE user_memories")
        await db.commit()


async def init_db(db_path: str) -> aiosqlite.Connection:
    """初始化資料庫 schema 並回傳連線"""
    global _db
    _db = await aiosqlite.connect(db_path)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA foreign_keys=ON")
    # migration：舊表有 user_id 則 DROP 重建
    await _migrate_user_memories(_db)
    await _db.executescript(SCHEMA_SQL)
    await _db.commit()
    return _db


def get_db() -> aiosqlite.Connection:
    """取得全域 db 連線"""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db


async def close_db():
    """關閉資料庫連線"""
    global _db
    if _db:
        await _db.close()
        _db = None
