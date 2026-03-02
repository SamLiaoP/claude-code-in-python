###
# api/chat.py — WebSocket /ws/chat/{session_id}
#
# 用途：串流對話端點，處理 message / answer / abort 事件
# 主要功能：
#   - 連線時驗證 token，載入歷史訊息
#   - 連線時根據 session project_dir 重新掃描 skills
#   - 接收 user message → 觸發 Processor → 串流推送事件
#   - 處理 ask_user answer 和 abort
# 關聯：使用 auth.py, session/*, provider.py, tool/base.py, skill.py
###

import json
import logging
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from auth import authenticate_ws
from config import AppConfig
from provider import LLMProvider
from session.message import Message
from session.processor import Processor
from session.session import get_session, load_messages, save_message
from skill import scan_skills
from tool.base import ToolRegistry

logger = logging.getLogger(__name__)

router = APIRouter()

# 由 main.py 注入
_app_config: AppConfig | None = None
_tool_registry: ToolRegistry | None = None


def init_chat_api(config: AppConfig, registry: ToolRegistry):
    global _app_config, _tool_registry
    _app_config = config
    _tool_registry = registry


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(
    ws: WebSocket,
    session_id: str,
    token: str = Query(default=""),
):
    # 認證
    user_id = authenticate_ws(token)
    if not user_id:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws.accept()

    # 驗證 session 存在且屬於此使用者
    session = await get_session(session_id, user_id)
    if not session:
        await ws.send_json({"type": "error", "message": "Session 不存在或無權存取"})
        await ws.close()
        return

    # 取得 provider
    provider_name = session["provider"]
    provider_config = _app_config.providers.get(provider_name)
    if not provider_config:
        await ws.send_json({"type": "error", "message": f"Provider 不存在: {provider_name}"})
        await ws.close()
        return

    provider = LLMProvider(provider_config)

    # 根據 session project_dir 重新掃描 skills
    project_dir = session.get("project_dir")
    scan_skills(project_dir)

    # 載入歷史訊息
    history = await load_messages(session_id)

    # 建立 processor
    processor = Processor(
        provider=provider,
        tool_registry=_tool_registry,
        session_id=session_id,
        user_id=user_id,
        project_dir=project_dir,
        max_output=_app_config.sandbox.max_output,
    )

    async def on_event(event: dict[str, Any]):
        """推送事件到 WebSocket"""
        try:
            await ws.send_json(event)
        except Exception:
            pass

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "message": "無效的 JSON"})
                continue

            msg_type = data.get("type")

            if msg_type == "message":
                content = data.get("content", "")
                if not content.strip():
                    continue

                # 建立 user message 並儲存
                user_msg = Message.user(content)
                await save_message(session_id, user_msg)
                history.append(user_msg)

                # 處理一輪對話
                assistant_msg = await processor.process_turn(history, on_event)

                # 儲存 assistant message
                if assistant_msg.parts:
                    await save_message(session_id, assistant_msg)
                    history.append(assistant_msg)

            elif msg_type == "answer":
                # 使用者回答 ask_user 問題
                tool_id = data.get("tool_id", "")
                selected = data.get("selected", [])
                answer_text = ", ".join(selected) if selected else data.get("text", "")
                processor.submit_answer(answer_text)

            elif msg_type == "abort":
                processor.abort()

    except WebSocketDisconnect:
        logger.info(f"WebSocket 斷線: session={session_id}, user={user_id}")
