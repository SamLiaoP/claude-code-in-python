###
# session/processor.py — LLM 對話處理 + 工具呼叫狀態機
#
# 用途：處理一輪對話：LLM 回應 → 偵測 tool_use → 執行工具 → 送回 LLM 繼續
# 主要功能：
#   - process_turn(): 一輪對話處理（可能多次 LLM 呼叫），支援 stream 參數切換串流/非串流模式，回傳 list[Message] 包含所有輪次的 assistant messages
#   - 自動循環：tool_use → execute → send back
#   - Doom loop 偵測：同參數 3 次中斷
#   - ask_user 暫停機制
#   - 429 速率限制重試時透過 on_event 推送 status 事件到前端
#   - 使用 session 專屬 logger（日誌寫入 logs/sessions/<session_id>.log）
# 關聯：被 api/chat.py 呼叫，使用 provider.py（LiteLLM）, tool/base.py, session/message.py, log_utils.py
###

import asyncio
import hashlib
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, AsyncGenerator, Callable

from log_utils import get_session_logger
from provider import LLMProvider
from session.message import Message, TextPart, ToolPart, build_tool_result_messages
from session.memory import memory_read

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
        self.logger = get_session_logger(session_id)
        # 把 session logger 注入 provider，讓完整請求/回應寫入 session log
        self.provider.logger = self.logger
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
        stream: bool = False,
    ) -> list[Message]:
        """
        處理一輪對話（可能多次 LLM 呼叫）。
        on_event: callback 推送 WebSocket 事件
        stream: True 使用串流模式逐字輸出，False 使用非串流模式一次回傳
        回傳所有輪次的 assistant Messages（含工具呼叫資訊）
        """
        self.abort_event.clear()
        system = await self.build_system_prompt()
        tools_schema = self.tool_registry.get_tools_schema()
        assistant_msg = Message.assistant()
        all_messages: list[Message] = []
        self._call_counts.clear()

        self.logger.debug("=== PROCESS TURN START (stream=%s) ===", stream)
        self.logger.debug("Tools schema count: %d", len(tools_schema) if tools_schema else 0)
        self.logger.debug("History messages: %d", len(messages))

        # 轉換歷史訊息為 API 格式（assistant 含 tool_calls 時需補上 tool result messages）
        api_messages = []
        for m in messages:
            api_messages.append(m.to_api_format())
            if m.role == "assistant":
                tool_parts = [p for p in m.parts if isinstance(p, ToolPart)]
                if tool_parts:
                    api_messages.extend(build_tool_result_messages(tool_parts))

        # 429 重試時推送狀態到前端
        async def _on_retry(attempt: int, delay: int):
            await on_event({
                "type": "status",
                "message": f"API 忙碌中，{delay} 秒後自動重試（第 {attempt} 次）...",
            })

        while True:
            if self.abort_event.is_set():
                break

            if stream:
                # 串流模式：逐 chunk 推送 text_delta
                text_buf = ""
                current_tool_parts_from_stream: list[ToolPart] = []
                # 累積 tool call arguments（index -> args_str）
                tool_args_buf: dict[int, str] = {}
                tool_info_buf: dict[int, dict] = {}

                async for event in self.provider.stream_chat(
                    messages=api_messages,
                    tools=tools_schema if tools_schema else None,
                    system=system,
                    on_retry=_on_retry,
                ):
                    if self.abort_event.is_set():
                        break

                    if event.type == "text_delta":
                        text_buf += event.text
                        await on_event({"type": "text_delta", "text": event.text})

                    elif event.type == "tool_use_start":
                        idx = len(tool_info_buf)
                        tool_info_buf[idx] = {"id": event.tool_id, "name": event.tool_name}
                        tool_args_buf[idx] = ""
                        await on_event({
                            "type": "tool_start",
                            "tool_id": event.tool_id,
                            "name": event.tool_name,
                        })

                    elif event.type == "tool_use_input":
                        # 累積 arguments JSON 片段到最新的 tool
                        if tool_args_buf:
                            last_idx = max(tool_args_buf.keys())
                            tool_args_buf[last_idx] += event.input_json

                    elif event.type == "tool_use_done":
                        # 找到對應的 tool，組裝 ToolPart
                        for idx, info in tool_info_buf.items():
                            if info["id"] == event.tool_id:
                                try:
                                    input_data = json.loads(tool_args_buf.get(idx, "{}"))
                                except json.JSONDecodeError:
                                    input_data = {}
                                current_tool_parts_from_stream.append(ToolPart(
                                    tool_id=info["id"],
                                    tool_name=info["name"],
                                    input_data=input_data,
                                    status="pending",
                                ))
                                break

                if text_buf:
                    assistant_msg.parts.append(TextPart(text=text_buf))

                current_tool_parts = current_tool_parts_from_stream
            else:
                # 非串流模式：一次回傳
                chat_result = await self.provider.chat(
                    messages=api_messages,
                    tools=tools_schema if tools_schema else None,
                    system=system,
                    on_retry=_on_retry,
                )

                # 處理文字回應
                if chat_result.text:
                    assistant_msg.parts.append(TextPart(text=chat_result.text))
                    await on_event({"type": "text_delta", "text": chat_result.text})

                # 解析 tool_calls（非串流分支）
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
                    all_messages.append(assistant_msg)
                    await on_event({"type": "done"})
                    return all_messages

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
                    self.logger.debug("=== TOOL CALL: %s ===", tp.tool_name)
                    self.logger.debug("  params: %s", json.dumps(tp.input_data, ensure_ascii=False)[:1000])
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
                        self.logger.debug("  result status=%s, output(%d chars): %s",
                                     tp.status, len(tp.output or ""),
                                     (tp.output or tp.error or "")[:500])
                    else:
                        tp.error = f"未知工具: {tp.tool_name}"
                        tp.status = "error"
                        self.logger.debug("  ERROR: %s", tp.error)

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

            # 收集當前輪次的 assistant_msg，重置給下一輪
            if assistant_msg.parts:
                all_messages.append(assistant_msg)
            assistant_msg = Message.assistant()

        # 最後一輪（無工具呼叫的純文字回應）
        if assistant_msg.parts:
            all_messages.append(assistant_msg)
        await on_event({"type": "done"})
        return all_messages

    def submit_answer(self, answer: str):
        """使用者回答 ask_user 問題"""
        if self._question_future and not self._question_future.done():
            self._question_future.set_result(answer)

    def abort(self):
        """中斷處理"""
        self.abort_event.set()
        if self._question_future and not self._question_future.done():
            self._question_future.set_result("[使用者中斷]")
