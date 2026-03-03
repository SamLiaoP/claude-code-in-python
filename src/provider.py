###
# provider.py — 統一 LLM Provider
#
# 用途：使用 litellm 統一呼叫 100+ LLM（Ollama / Claude / GPT / Gemini 等）
# 主要功能：
#   - LLMEvent 資料類別（text_delta / tool_use_start / tool_use_input / tool_use_done / message_stop）
#   - LLMProvider.chat() — 非串流模式，一次回傳完整結果（含 tool_calls）
#   - LLMProvider.stream_chat() — 串流模式（保留備用）
#   - system prompt 注入為 {"role": "system"} 訊息（LiteLLM 慣例）
#   - 429 速率限制自動重試（最多 3 次，間隔遞增 5→15→30 秒），支援 on_retry callback
# 關聯：被 session/processor.py 呼叫，讀取 config.ProviderConfig
#   - 支援外部注入 logger（Processor 注入 session logger），完整記錄請求/回應到 session log
###

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable

import litellm
from litellm.exceptions import RateLimitError

from config import ProviderConfig

logger = logging.getLogger(__name__)


@dataclass
class LLMEvent:
    """LLM 串流事件"""
    type: str  # text_delta | tool_use_start | tool_use_input | tool_use_done | message_stop
    text: str = ""
    tool_id: str = ""
    tool_name: str = ""
    input_json: str = ""


class LLMProvider:
    """統一 LLM Provider，透過 litellm 存取不同後端"""

    def __init__(self, config: ProviderConfig, logger: logging.Logger | None = None):
        self.config = config
        self.model = config.model
        self.api_key = config.resolve_api_key()
        self.api_base = config.api_base
        self.logger = logger or logging.getLogger(__name__)

    def _build_kwargs(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        system: str,
        max_tokens: int,
        stream: bool,
    ) -> tuple[list[dict], dict[str, Any]]:
        """組裝 litellm 呼叫參數，回傳 (all_messages, kwargs)"""
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": all_messages,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if tools:
            kwargs["tools"] = tools

        # --- DEBUG LOG ---
        self.logger.debug("=== LLM REQUEST (stream=%s) ===", stream)
        self.logger.debug("Model: %s", self.model)
        for i, msg in enumerate(all_messages):
            role = msg.get("role", "?")
            content = msg.get("content", "")
            self.logger.debug("Message[%d] role=%s: %s", i, role, content)
            if msg.get("tool_calls"):
                self.logger.debug("  tool_calls: %s", json.dumps(msg["tool_calls"], ensure_ascii=False))
        if tools:
            tool_names = [t.get("function", {}).get("name", t.get("name", "?")) for t in tools]
            self.logger.debug("Tools: %s", tool_names)
        self.logger.debug("=== END LLM REQUEST ===")

        return all_messages, kwargs

    @dataclass
    class ChatResult:
        """非串流模式的回傳結果"""
        text: str = ""
        tool_calls: list[dict] = None  # [{"id", "name", "arguments"}]

        def __post_init__(self):
            if self.tool_calls is None:
                self.tool_calls = []

    # 重試間隔（秒）
    RETRY_DELAYS = [5, 15, 30]

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str = "",
        max_tokens: int = 4096,
        on_retry: Callable[[int, int], Any] | None = None,
    ) -> "LLMProvider.ChatResult":
        """非串流對話，一次回傳完整結果。遇到 429 自動重試。"""
        _, kwargs = self._build_kwargs(messages, tools, system, max_tokens, stream=False)

        last_err = None
        for attempt in range(1 + len(self.RETRY_DELAYS)):
            try:
                response = await litellm.acompletion(**kwargs)
                break
            except RateLimitError as e:
                last_err = e
                if attempt < len(self.RETRY_DELAYS):
                    delay = self.RETRY_DELAYS[attempt]
                    self.logger.warning("429 RateLimitError, 第 %d 次重試，等待 %d 秒", attempt + 1, delay)
                    if on_retry:
                        await on_retry(attempt + 1, delay)
                    await asyncio.sleep(delay)
                else:
                    self.logger.error("429 重試用盡（%d 次），拋出例外", len(self.RETRY_DELAYS))
                    raise last_err

        result = LLMProvider.ChatResult()
        choice = response.choices[0] if response.choices else None
        if choice and choice.message:
            result.text = choice.message.content or ""
            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    result.tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    })

        self.logger.debug("=== LLM RESPONSE ===")
        self.logger.debug("Text (%d chars): %s", len(result.text), result.text)
        if result.tool_calls:
            for tc in result.tool_calls:
                self.logger.debug("Tool call: %s(%s)", tc["name"], tc["arguments"])
        self.logger.debug("=== END LLM RESPONSE ===")

        return result

    async def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str = "",
        max_tokens: int = 4096,
        on_retry: Callable[[int, int], Any] | None = None,
    ) -> AsyncGenerator[LLMEvent, None]:
        """串流對話，產生 LLMEvent（保留備用）。遇到 429 自動重試。"""
        _, kwargs = self._build_kwargs(messages, tools, system, max_tokens, stream=True)

        # 追蹤 tool_calls 狀態（index -> {id, name, arguments}）
        active_tools: dict[int, dict] = {}

        last_err = None
        for attempt in range(1 + len(self.RETRY_DELAYS)):
            try:
                response = await litellm.acompletion(**kwargs)
                break
            except RateLimitError as e:
                last_err = e
                if attempt < len(self.RETRY_DELAYS):
                    delay = self.RETRY_DELAYS[attempt]
                    self.logger.warning("429 RateLimitError (stream), 第 %d 次重試，等待 %d 秒", attempt + 1, delay)
                    if on_retry:
                        await on_retry(attempt + 1, delay)
                    await asyncio.sleep(delay)
                else:
                    self.logger.error("429 重試用盡（stream, %d 次），拋出例外", len(self.RETRY_DELAYS))
                    raise last_err

        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            finish_reason = chunk.choices[0].finish_reason if chunk.choices else None

            if delta:
                # 文字內容
                if delta.content:
                    yield LLMEvent(type="text_delta", text=delta.content)

                # tool_calls 處理
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index if tc.index is not None else 0

                        if idx not in active_tools:
                            tool_id = tc.id or ""
                            tool_name = tc.function.name if tc.function and tc.function.name else ""
                            active_tools[idx] = {
                                "id": tool_id,
                                "name": tool_name,
                            }
                            if tool_id and tool_name:
                                yield LLMEvent(
                                    type="tool_use_start",
                                    tool_id=tool_id,
                                    tool_name=tool_name,
                                )
                        else:
                            if tc.id and not active_tools[idx]["id"]:
                                active_tools[idx]["id"] = tc.id
                            if tc.function and tc.function.name and not active_tools[idx]["name"]:
                                active_tools[idx]["name"] = tc.function.name
                                yield LLMEvent(
                                    type="tool_use_start",
                                    tool_id=active_tools[idx]["id"],
                                    tool_name=active_tools[idx]["name"],
                                )

                        if tc.function and tc.function.arguments:
                            yield LLMEvent(
                                type="tool_use_input",
                                input_json=tc.function.arguments,
                            )

            if finish_reason == "tool_calls" or finish_reason == "stop":
                for idx, tool_info in active_tools.items():
                    yield LLMEvent(
                        type="tool_use_done",
                        tool_id=tool_info["id"],
                        tool_name=tool_info["name"],
                    )
                yield LLMEvent(type="message_stop")
