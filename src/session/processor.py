###
# session/processor.py — LLM 串流事件處理 + 工具呼叫狀態機
#
# 用途：處理一輪對話：串流 LLM 回應 → 偵測 tool_use → 執行工具 → 送回 LLM 繼續
# 主要功能：
#   - process_turn(): 一輪對話處理（可能多次 LLM 呼叫）
#   - 自動循環：tool_use → execute → send back
#   - Doom loop 偵測：同參數 3 次中斷
#   - ask_user 暫停機制
# 關聯：被 api/chat.py 呼叫，使用 provider.py（LiteLLM）, tool/base.py, session/message.py
###

import asyncio
import hashlib
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, AsyncGenerator, Callable

from provider import LLMProvider
from session.message import Message, TextPart, ToolPart, build_tool_result_messages
from session.memory import memory_read

logger = logging.getLogger(__name__)

# Doom loop 偵測門檻
DOOM_LOOP_THRESHOLD = 3

# 內建 system prompt
BASE_SYSTEM = """你是一個研究助理 AI。請用繁體中文回答，除非使用者使用其他語言。
你可以使用提供的工具來完成任務。執行程式碼時請注意安全性。"""


class Processor:
    """處理一輪對話的狀態機"""

    def __init__(
        self,
        provider: LLMProvider,
        tool_registry: Any,  # ToolRegistry
        session_id: str,
        user_id: str,
        project_dir: str | None = None,
        max_output: int = 10000,
    ):
        self.provider = provider
        self.tool_registry = tool_registry
        self.session_id = session_id
        self.user_id = user_id
        self.project_dir = project_dir
        self.max_output = max_output
        self.abort_event = asyncio.Event()
        # doom loop 追蹤：hash(tool_name + params) -> count
        self._call_counts: dict[str, int] = defaultdict(int)
        # ask_user 暫停機制
        self._question_future: asyncio.Future | None = None

    async def build_system_prompt(self) -> str:
        """組裝 system prompt"""
        parts = []

        # PROJECT.md 注入
        if self.project_dir:
            project_md = Path(self.project_dir) / ".py-opencode" / "context" / "PROJECT.md"
            if project_md.exists():
                parts.append(project_md.read_text(encoding="utf-8"))

        parts.append(BASE_SYSTEM)

        # Session 記憶摘要
        memories = await memory_read(self.session_id)
        if memories:
            mem_lines = [f"- {m['key']}: {m['value']}" for m in memories[:20]]
            parts.append("## 使用者記憶\n" + "\n".join(mem_lines))

        return "\n\n".join(parts)

    async def process_turn(
        self,
        messages: list[Message],
        on_event: Callable[[dict], Any],
    ) -> Message:
        """
        處理一輪對話（可能多次 LLM 呼叫）。
        on_event: callback 推送 WebSocket 事件
        回傳最終的 assistant Message
        """
        system = await self.build_system_prompt()
        tools_schema = self.tool_registry.get_tools_schema()
        assistant_msg = Message.assistant()
        self._call_counts.clear()

        logger.debug("=== PROCESS TURN START ===")
        logger.debug("System prompt (%d chars): %s", len(system), system[:800] + ("..." if len(system) > 800 else ""))
        logger.debug("Tools schema count: %d", len(tools_schema) if tools_schema else 0)
        logger.debug("History messages: %d", len(messages))

        # 轉換歷史訊息為 API 格式
        api_messages = [m.to_api_format() for m in messages]

        while True:
            if self.abort_event.is_set():
                break

            # 非串流呼叫 LLM
            chat_result = await self.provider.chat(
                messages=api_messages,
                tools=tools_schema if tools_schema else None,
                system=system,
            )

            # 處理文字回應
            if chat_result.text:
                assistant_msg.parts.append(TextPart(text=chat_result.text))
                await on_event({"type": "text_delta", "text": chat_result.text})

            # 解析 tool_calls
            current_tool_parts: list[ToolPart] = []
            for tc in chat_result.tool_calls:
                try:
                    input_data = json.loads(tc["arguments"]) if tc["arguments"] else {}
                except json.JSONDecodeError:
                    input_data = {}
                current_tool_parts.append(ToolPart(
                    tool_id=tc["id"],
                    tool_name=tc["name"],
                    input_data=input_data,
                    status="pending",
                ))
                await on_event({
                    "type": "tool_start",
                    "tool_id": tc["id"],
                    "name": tc["name"],
                })

            # 沒有工具呼叫 → 結束
            if not current_tool_parts:
                break

            # 執行工具
            for tp in current_tool_parts:
                # doom loop 偵測
                call_hash = hashlib.md5(
                    f"{tp.tool_name}:{json.dumps(tp.input_data, sort_keys=True)}".encode()
                ).hexdigest()
                self._call_counts[call_hash] += 1
                if self._call_counts[call_hash] >= DOOM_LOOP_THRESHOLD:
                    tp.status = "error"
                    tp.error = f"Doom loop 偵測：工具 {tp.tool_name} 以相同參數被呼叫 {DOOM_LOOP_THRESHOLD} 次，已中斷"
                    await on_event({
                        "type": "tool_result", "tool_id": tp.tool_id,
                        "output": tp.error, "is_error": True,
                    })
                    assistant_msg.parts.append(tp)
                    # doom loop → 結束整個 turn
                    await on_event({"type": "done"})
                    return assistant_msg

                # ask_user 特殊處理：暫停等使用者回應
                if tp.tool_name == "ask_user":
                    tp.status = "running"
                    question = tp.input_data.get("question", "")
                    options = tp.input_data.get("options", [])
                    await on_event({
                        "type": "question",
                        "tool_id": tp.tool_id,
                        "question": question,
                        "options": options,
                    })
                    # 等待使用者回應
                    loop = asyncio.get_event_loop()
                    self._question_future = loop.create_future()
                    answer = await self._question_future
                    self._question_future = None
                    tp.output = answer
                    tp.status = "completed"
                    await on_event({
                        "type": "tool_result", "tool_id": tp.tool_id, "output": answer,
                    })
                else:
                    # 一般工具執行
                    tp.status = "running"
                    logger.debug("=== TOOL CALL: %s ===", tp.tool_name)
                    logger.debug("  params: %s", json.dumps(tp.input_data, ensure_ascii=False)[:1000])
                    tool = self.tool_registry.get_tool(tp.tool_name)
                    if tool:
                        from tool.base import ToolContext
                        ctx = ToolContext(
                            session_id=self.session_id,
                            user_id=self.user_id,
                            abort=self.abort_event,
                        )
                        result = await tool.execute(tp.input_data, ctx)
                        # 截斷輸出
                        output = result.output
                        if len(output) > self.max_output:
                            output = output[:self.max_output] + "\n[截斷]"
                        tp.output = output
                        tp.error = result.error
                        tp.status = "error" if result.error else "completed"
                        logger.debug("  result status=%s, output(%d chars): %s",
                                     tp.status, len(tp.output or ""),
                                     (tp.output or tp.error or "")[:500])
                    else:
                        tp.error = f"未知工具: {tp.tool_name}"
                        tp.status = "error"
                        logger.debug("  ERROR: %s", tp.error)

                    await on_event({
                        "type": "tool_result",
                        "tool_id": tp.tool_id,
                        "output": tp.error if tp.error else tp.output,
                        "is_error": bool(tp.error),
                    })

                assistant_msg.parts.append(tp)

            # 把 assistant 訊息和 tool results 加到 api_messages，繼續循環
            api_messages.append(assistant_msg.to_api_format())
            api_messages.extend(build_tool_result_messages(current_tool_parts))

            # 重置 assistant_msg 給下一輪
            assistant_msg = Message.assistant()

        await on_event({"type": "done"})
        return assistant_msg

    def submit_answer(self, answer: str):
        """使用者回答 ask_user 問題"""
        if self._question_future and not self._question_future.done():
            self._question_future.set_result(answer)

    def abort(self):
        """中斷處理"""
        self.abort_event.set()
        if self._question_future and not self._question_future.done():
            self._question_future.set_result("[使用者中斷]")
