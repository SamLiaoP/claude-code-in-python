###
# api/sessions.py — Session REST CRUD + Provider/Model 查詢
#
# 用途：GET/POST/DELETE /api/sessions, PATCH /api/sessions/{id},
#       GET /api/providers, GET /api/models
# 關聯：使用 auth.py, session/session.py, config.py
###

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from session.session import (
    create_session, delete_session, list_sessions,
    update_session_model, update_session_provider, update_session_title,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])
providers_router = APIRouter(prefix="/api/providers", tags=["providers"])
models_router = APIRouter(prefix="/api/models", tags=["models"])

# 全域 config 引用（由 main.py 注入）
_app_config = None

# Claude 可用模型（litellm 格式：anthropic/<model_id>）
CLAUDE_MODELS = [
    {"id": "anthropic/claude-opus-4-6", "name": "Claude Opus 4.6", "tier": "最強"},
    {"id": "anthropic/claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "tier": "平衡"},
    {"id": "anthropic/claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "tier": "最快"},
    {"id": "anthropic/claude-sonnet-4-5", "name": "Claude Sonnet 4.5", "tier": "Legacy"},
    {"id": "anthropic/claude-opus-4-5", "name": "Claude Opus 4.5", "tier": "Legacy"},
    {"id": "anthropic/claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "tier": "Legacy"},
]


def init_sessions_api(config):
    global _app_config
    _app_config = config


class CreateSessionRequest(BaseModel):
    provider: str | None = None
    project_dir: str | None = None
    skip_workdir: bool = False
    model: str | None = None


class UpdateSessionRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    title: str | None = None


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
    session = await create_session(user_id, provider, req.project_dir, req.skip_workdir, req.model)
    return session


@router.patch("/{session_id}")
async def patch_session(
    session_id: str,
    req: UpdateSessionRequest,
    user_id: str = Depends(get_current_user),
):
    """更新 Session 的 title / provider / model"""
    if req.title is not None:
        ok = await update_session_title(session_id, user_id, req.title)
        if not ok:
            raise HTTPException(status_code=404, detail="Session 不存在或無權存取")

    if req.provider is not None:
        if _app_config and req.provider not in _app_config.providers:
            raise HTTPException(status_code=400, detail=f"Provider 不存在: {req.provider}")
        ok = await update_session_provider(session_id, user_id, req.provider)
        if not ok:
            raise HTTPException(status_code=404, detail="Session 不存在或無權存取")

    if req.model is not None:
        ok = await update_session_model(session_id, user_id, req.model)
        if not ok:
            raise HTTPException(status_code=404, detail="Session 不存在或無權存取")

    return {"ok": True, "provider": req.provider, "model": req.model}


@router.delete("/{session_id}")
async def remove_session(
    session_id: str,
    user_id: str = Depends(get_current_user),
):
    ok = await delete_session(session_id, user_id)
    return {"ok": ok}


@providers_router.get("")
async def get_providers(user_id: str = Depends(get_current_user)):
    """列出所有可用的 LLM Provider（不洩漏 API Key）"""
    if not _app_config:
        return []
    return [
        {"name": name, "model": pc.model}
        for name, pc in _app_config.providers.items()
    ]


@models_router.get("")
async def get_models(user_id: str = Depends(get_current_user)):
    """列出可用的 Claude 模型"""
    return CLAUDE_MODELS
