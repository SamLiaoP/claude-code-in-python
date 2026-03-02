###
# auth.py — 靜態 API Key 認證
#
# 用途：驗證 HTTP Header (Authorization: Bearer <key>) 和 WebSocket query param (?token=<key>)
# 主要功能：
#   - authenticate(api_key) -> user_id 或拋出 HTTPException
#   - get_current_user dependency（FastAPI Depends）
#   - authenticate_ws(token) -> user_id 或 None
# 關聯：被 api/ 路由引用，讀取 config.api_keys
###

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_api_keys: dict[str, str] = {}  # key -> user_id

_bearer_scheme = HTTPBearer()


def init_auth(api_keys: dict[str, str]):
    """初始化 API Key 對照表"""
    global _api_keys
    _api_keys = api_keys


def authenticate(api_key: str) -> str:
    """驗證 API Key，回傳 user_id"""
    user_id = _api_keys.get(api_key)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="無效的 API Key")
    return user_id


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    """FastAPI dependency：從 Authorization header 取得 user_id"""
    return authenticate(credentials.credentials)


def authenticate_ws(token: str | None) -> str | None:
    """WebSocket 認證：從 query param 取得 user_id，失敗回傳 None"""
    if not token:
        return None
    return _api_keys.get(token)
