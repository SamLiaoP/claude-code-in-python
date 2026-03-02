###
# api/memory.py — Memory REST API
#
# 用途：GET /api/memory?session_id=xxx — 查詢指定 Session 的所有記憶
# 關聯：使用 auth.py, session/memory.py
###

from fastapi import APIRouter, Depends, Query

from auth import get_current_user
from session.memory import memory_read

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("")
async def get_memory(
    session_id: str = Query(..., description="要查詢的 Session ID"),
    user_id: str = Depends(get_current_user),
):
    memories = await memory_read(session_id)
    return memories
