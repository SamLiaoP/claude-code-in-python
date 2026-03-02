###
# api/memory.py — Memory REST API
#
# 用途：GET /api/memory — 查詢當前使用者的所有記憶
# 關聯：使用 auth.py, session/memory.py
###

from fastapi import APIRouter, Depends

from auth import get_current_user
from session.memory import memory_read

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("")
async def get_memory(user_id: str = Depends(get_current_user)):
    memories = await memory_read(user_id)
    return memories
