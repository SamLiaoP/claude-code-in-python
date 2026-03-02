###
# api/skills.py — Skills REST API
#
# 用途：GET /api/skills（列出）、POST /api/skills/reload（重新掃描，可帶 project_dir）
# 關聯：使用 auth.py, skill.py
###

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import get_current_user
from skill import list_skills, scan_skills

router = APIRouter(prefix="/api/skills", tags=["skills"])


class ReloadSkillsRequest(BaseModel):
    project_dir: str | None = None


@router.get("")
async def get_skills(user_id: str = Depends(get_current_user)):
    return list_skills()


@router.post("/reload")
async def reload_skills(
    req: ReloadSkillsRequest | None = None,
    user_id: str = Depends(get_current_user),
):
    project_dir = req.project_dir if req else None
    count = scan_skills(project_dir)
    return {"count": count}
