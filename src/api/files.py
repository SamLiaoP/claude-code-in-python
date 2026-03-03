###
# api/files.py — 目錄瀏覽 REST API
#
# 用途：GET /api/files 列出檔案、POST /api/files/open 在本機開啟資料夾
# 主要功能：
#   - 根據 session_id 取得 project_dir
#   - 列出指定 path 下的檔案/資料夾（name, type, size）
#   - 路徑遍歷防護：驗證 resolved path 不超出 project_dir
#   - 在本機 Finder/Explorer 開啟指定資料夾
# 關聯：使用 auth.py, session/session.py
###

import logging
import platform
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_user
from session.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])


def _resolve_and_validate(project_dir: str, path: str) -> tuple[Path, Path]:
    """解析並驗證路徑，回傳 (base, target)"""
    base = Path(project_dir).resolve()
    target = (base / path).resolve()
    if not target.is_relative_to(base):
        raise HTTPException(status_code=403, detail="禁止存取工作目錄以外的路徑")
    return base, target


@router.get("")
async def list_files(
    session_id: str = Query(...),
    path: str = Query(default="."),
    user_id: str = Depends(get_current_user),
):
    """列出 Session 專案目錄下的檔案與資料夾"""
    session = await get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session 不存在或無權存取")

    project_dir = session.get("project_dir")
    if not project_dir:
        raise HTTPException(status_code=400, detail="此 Session 沒有設定工作目錄")

    base, target = _resolve_and_validate(project_dir, path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="路徑不存在")

    if not target.is_dir():
        raise HTTPException(status_code=400, detail="指定路徑不是資料夾")

    entries = []
    for item in sorted(target.iterdir()):
        entry = {
            "name": item.name,
            "type": "directory" if item.is_dir() else "file",
        }
        if item.is_file():
            try:
                entry["size"] = item.stat().st_size
            except OSError:
                entry["size"] = 0
        entries.append(entry)

    return {
        "base": str(base),
        "path": path,
        "entries": entries,
    }


class OpenFolderRequest(BaseModel):
    session_id: str
    path: str = "."


@router.post("/open")
async def open_folder(
    req: OpenFolderRequest,
    user_id: str = Depends(get_current_user),
):
    """在本機 Finder/Explorer 開啟指定資料夾"""
    session = await get_session(req.session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session 不存在或無權存取")

    project_dir = session.get("project_dir")
    if not project_dir:
        raise HTTPException(status_code=400, detail="此 Session 沒有設定工作目錄")

    _, target = _resolve_and_validate(project_dir, req.path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="路徑不存在")

    # 如果是檔案，開啟其所在資料夾
    folder = target if target.is_dir() else target.parent

    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", str(folder)])
        elif system == "Windows":
            subprocess.Popen(["explorer", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法開啟資料夾: {e}")

    return {"ok": True, "path": str(folder)}
