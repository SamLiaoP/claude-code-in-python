###
# session/memory.py — 個人 Memory 管理
#
# 用途：每人一個跨 Session 記憶空間（key-value），AI 可透過 tool 讀寫
# 主要功能：
#   - memory_read(user_id, key?) -> 讀取記憶
#   - memory_write(user_id, key, value) -> 寫入/更新記憶
#   - memory_list(user_id) -> 列出全部記憶
# 關聯：被 tool/memory_tool.py, api/memory.py 引用，使用 storage/database.py
###

from datetime import datetime, timezone

from storage.database import get_db


async def memory_read(user_id: str, key: str | None = None) -> list[dict]:
    """讀取記憶。key=None 時列出全部"""
    db = get_db()
    if key:
        cursor = await db.execute(
            "SELECT key, value, updated_at FROM user_memories WHERE user_id = ? AND key = ?",
            (user_id, key),
        )
    else:
        cursor = await db.execute(
            "SELECT key, value, updated_at FROM user_memories WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        )
    rows = await cursor.fetchall()
    return [{"key": r[0], "value": r[1], "updated_at": r[2]} for r in rows]


async def memory_write(user_id: str, key: str, value: str) -> None:
    """寫入或更新記憶"""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO user_memories (user_id, key, value, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
        (user_id, key, value, now),
    )
    await db.commit()


async def memory_delete(user_id: str, key: str) -> bool:
    """刪除記憶"""
    db = get_db()
    cursor = await db.execute(
        "DELETE FROM user_memories WHERE user_id = ? AND key = ?",
        (user_id, key),
    )
    await db.commit()
    return cursor.rowcount > 0
