###
# api/skills.py — Skills REST API
#
# 用途：GET /api/skills（列出，可帶 session_id 自動重新掃描該 session 的 project skills）
#       POST /api/skills/reload（重新掃描，可帶 project_dir）
# 關聯：使用 auth.py, skill.py, session/session.py
###

from fastapi import APIRouter, Depends, Query

from pydantic import BaseModel

from auth import get_current_user
from session.session import get_session
from skill import list_skills, scan_skills

router = APIRouter(prefix="/api/skills", tags=["skills"])


class ReloadSkillsRequest(BaseModel):
    project_dir: str | None = None


@router.get("")
async def get_skills(
    session_id: str = Query(default=""),
    user_id: str = Depends(get_current_user),
):
    # 若有帶 session_id，先根據該 session 的 project_dir 重新掃描
    if session_id:
        session = await get_session(session_id, user_id)
        if session:
            scan_skills(session.get("project_dir"))
    return list_skills()


@router.post("/reload")
async def reload_skills(
    req: ReloadSkillsRequest | None = None,
    user_id: str = Depends(get_current_user),
):
    project_dir = req.project_dir if req else None
    count = scan_skills(project_dir)
    return {"count": count}
