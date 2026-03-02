###
# api/sessions.py — Session REST CRUD
#
# 用途：GET/POST/DELETE /api/sessions
# 關聯：使用 auth.py, session/session.py
###

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import get_current_user
from session.session import create_session, delete_session, list_sessions

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# 全域 config 引用（由 main.py 注入）
_app_config = None


def init_sessions_api(config):
    global _app_config
    _app_config = config


class CreateSessionRequest(BaseModel):
    provider: str | None = None
    project_dir: str | None = None


@router.get("")
async def get_sessions(user_id: str = Depends(get_current_user)):
    sessions = await list_sessions(user_id)
    return sessions


@router.post("")
async def post_session(
    req: CreateSessionRequest,
    user_id: str = Depends(get_current_user),
):
    provider = req.provider or (_app_config.default_provider if _app_config else "local")
    session = await create_session(user_id, provider, req.project_dir)
    return session


@router.delete("/{session_id}")
async def remove_session(
    session_id: str,
    user_id: str = Depends(get_current_user),
):
    ok = await delete_session(session_id, user_id)
    return {"ok": ok}
