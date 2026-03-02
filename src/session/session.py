###
# session/session.py — Session CRUD + SQLite 持久化 + 專案目錄初始化
#
# 用途：管理對話 Session 的生命週期
# 主要功能：
#   - create_session / list_sessions / get_session / delete_session
#   - save_message / load_messages（訊息持久化與載入）
#   - _init_project_dir：建立 .py-opencode/{skills/, context/} 並初始化 PROJECT.md
#   - create_session 預設自動建立工作目錄 ~/.py-opencode/projects/<session_id>/，
#     可透過 skip_workdir=True 跳過
# 關聯：被 api/sessions.py, api/chat.py 引用，使用 storage/database.py, session/message.py
###

import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from session.message import Message
from storage.database import get_db

logger = logging.getLogger(__name__)


def _init_project_dir(project_dir: str) -> None:
    """在 project_dir 下建立 .py-opencode/{skills/, context/} 並初始化 PROJECT.md"""
    base = Path(project_dir) / ".py-opencode"
    (base / "skills").mkdir(parents=True, exist_ok=True)
    (base / "context").mkdir(parents=True, exist_ok=True)

    project_md = base / "context" / "PROJECT.md"
    if not project_md.exists():
        project_md.write_text(
            "# 專案上下文\n\n<!-- 在此描述專案背景，內容會自動注入 system prompt -->\n",
            encoding="utf-8",
        )
    logger.info(f"已初始化專案目錄: {base}")


async def create_session(user_id: str, provider: str, project_dir: str | None = None, skip_workdir: bool = False) -> dict:
    """建立新 Session"""
    db = get_db()
    session_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # 決定 project_dir
    if project_dir:
        _init_project_dir(project_dir)
    elif not skip_workdir:
        project_dir = str(Path.home() / ".py-opencode" / "projects" / session_id)
        _init_project_dir(project_dir)

    await db.execute(
        "INSERT INTO sessions (id, user_id, provider, project_dir, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, user_id, provider, project_dir, now, now),
    )
    await db.commit()
    return {"id": session_id, "provider": provider, "project_dir": project_dir, "created_at": now}


async def list_sessions(user_id: str) -> list[dict]:
    """列出使用者的所有 Session"""
    db = get_db()
    cursor = await db.execute(
        "SELECT id, provider, title, project_dir, created_at, updated_at FROM sessions WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [
        {"id": r[0], "provider": r[1], "title": r[2], "project_dir": r[3], "created_at": r[4], "updated_at": r[5]}
        for r in rows
    ]


async def get_session(session_id: str, user_id: str) -> dict | None:
    """取得 Session（含權限驗證）"""
    db = get_db()
    cursor = await db.execute(
        "SELECT id, user_id, provider, title, project_dir, created_at, updated_at FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return {
        "id": row[0], "user_id": row[1], "provider": row[2], "title": row[3],
        "project_dir": row[4], "created_at": row[5], "updated_at": row[6],
    }


async def delete_session(session_id: str, user_id: str) -> bool:
    """刪除 Session（含權限驗證）"""
    db = get_db()
    cursor = await db.execute(
        "DELETE FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def save_message(session_id: str, message: Message) -> None:
    """儲存訊息至 SQLite"""
    db = get_db()
    await db.execute(
        "INSERT INTO messages (id, session_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (message.id, session_id, message.role, message.to_json(), message.created_at),
    )
    # 更新 session updated_at
    now = datetime.now(timezone.utc).isoformat()
    await db.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
    # 自動生成 title（從第一則 user 訊息）
    if message.role == "user":
        cursor = await db.execute("SELECT title FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        if row and row[0] is None:
            from session.message import TextPart
            text = " ".join(p.text for p in message.parts if isinstance(p, TextPart))
            title = text[:50] + ("..." if len(text) > 50 else "")
            await db.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))
    await db.commit()


async def load_messages(session_id: str) -> list[Message]:
    """載入 Session 歷史訊息"""
    db = get_db()
    cursor = await db.execute(
        "SELECT id, role, content, created_at FROM messages WHERE session_id = ? ORDER BY created_at",
        (session_id,),
    )
    rows = await cursor.fetchall()
    return [Message.from_json(r[0], r[1], r[2], r[3]) for r in rows]
