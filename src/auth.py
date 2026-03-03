###
# auth.py — 靜態 API Key 認證
#
# 用途：驗證 HTTP Header (Authorization: Bearer <key>) 和 WebSocket query param (?token=<key>)
# 主要功能：
#   - authenticate(api_key) -> user_id 或拋出 HTTPException
#   - get_current_user dependency（FastAPI Depends）：有帶 Bearer token 則驗證，未帶則用預設使用者
#   - authenticate_ws(token) -> user_id 或 None（未帶 token 時自動用預設使用者）
# 關聯：被 api/ 路由引用，讀取 config.api_keys
###

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_api_keys: dict[str, str] = {}  # key -> user_id

# auto_error=False：未帶 token 時不自動 403，改由我們處理
_bearer_scheme = HTTPBearer(auto_error=False)


def init_auth(api_keys: dict[str, str]):
    """初始化 API Key 對照表"""
    global _api_keys
    _api_keys = api_keys


def _default_user_id() -> str | None:
    """取得第一個 api_key 對應的 user_id 作為預設"""
    if _api_keys:
        return next(iter(_api_keys.values()))
    return None


def authenticate(api_key: str) -> str:
    """驗證 API Key，回傳 user_id"""
    user_id = _api_keys.get(api_key)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="無效的 API Key")
    return user_id


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """FastAPI dependency：有帶 Bearer token 則驗證，未帶則用預設使用者"""
    if credentials:
        return authenticate(credentials.credentials)
    # 未帶 token，用預設使用者（本地開發模式）
    default = _default_user_id()
    if default:
        return default
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未設定 API Key，請在 config.json 中設定 api_keys")


def authenticate_ws(token: str | None) -> str | None:
    """WebSocket 認證：從 query param 取得 user_id，未帶 token 時用預設使用者"""
    if token:
        return _api_keys.get(token)
    return _default_user_id()
