###
# session/message.py — 訊息資料結構
#
# 用途：定義 UserMessage / AssistantMessage / Part（TextPart, ToolPart）
# 主要功能：
#   - 訊息與 Part 的序列化/反序列化（JSON 格式存 SQLite）
#   - 轉換為 OpenAI API 格式（供 LiteLLM 使用）
#   - build_tool_result_messages() 產生 role=tool 訊息列表
# 關聯：被 session/processor.py, session/session.py 引用
###

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class TextPart:
    text: str
    type: str = "text"


@dataclass
class ToolPart:
    tool_id: str
    tool_name: str
    input_data: dict = field(default_factory=dict)
    output: str = ""
    error: str | None = None
    status: str = "pending"  # pending | running | completed | error
    type: str = "tool_use"


@dataclass
class Message:
    id: str
    role: str  # user | assistant
    parts: list[TextPart | ToolPart]
    created_at: str

    @staticmethod
    def user(content: str) -> "Message":
        return Message(
            id=str(uuid4()),
            role="user",
            parts=[TextPart(text=content)],
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def assistant() -> "Message":
        return Message(
            id=str(uuid4()),
            role="assistant",
            parts=[],
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_api_format(self) -> dict[str, Any]:
        """轉換為 OpenAI messages API 格式（供 LiteLLM 使用）"""
        if self.role == "user":
            text = " ".join(p.text for p in self.parts if isinstance(p, TextPart))
            return {"role": "user", "content": text}

        # assistant: 可能有 text + tool_calls
        text_parts = [p.text for p in self.parts if isinstance(p, TextPart)]
        content = " ".join(text_parts) if text_parts else None

        tool_calls = []
        for p in self.parts:
            if isinstance(p, ToolPart):
                tool_calls.append({
                    "id": p.tool_id,
                    "type": "function",
                    "function": {
                        "name": p.tool_name,
                        "arguments": json.dumps(p.input_data, ensure_ascii=False),
                    },
                })

        msg: dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        return msg

    def to_json(self) -> str:
        """序列化為 JSON 字串（存 SQLite）"""
        parts_data = []
        for p in self.parts:
            if isinstance(p, TextPart):
                parts_data.append({"type": "text", "text": p.text})
            elif isinstance(p, ToolPart):
                parts_data.append({
                    "type": "tool_use",
                    "tool_id": p.tool_id,
                    "tool_name": p.tool_name,
                    "input_data": p.input_data,
                    "output": p.output,
                    "error": p.error,
                    "status": p.status,
                })
        return json.dumps(parts_data, ensure_ascii=False)

    @staticmethod
    def from_json(msg_id: str, role: str, content_json: str, created_at: str) -> "Message":
        """從 JSON 反序列化"""
        parts_data = json.loads(content_json)
        parts: list[TextPart | ToolPart] = []
        for p in parts_data:
            if p["type"] == "text":
                parts.append(TextPart(text=p["text"]))
            elif p["type"] == "tool_use":
                parts.append(ToolPart(
                    tool_id=p["tool_id"],
                    tool_name=p["tool_name"],
                    input_data=p.get("input_data", {}),
                    output=p.get("output", ""),
                    error=p.get("error"),
                    status=p.get("status", "completed"),
                ))
        return Message(id=msg_id, role=role, parts=parts, created_at=created_at)


def build_tool_result_messages(tool_parts: list[ToolPart]) -> list[dict[str, Any]]:
    """建構 tool result 訊息列表（OpenAI 格式：每個 tool result 是獨立的 role=tool 訊息）"""
    messages = []
    for tp in tool_parts:
        result_text = tp.error if tp.error else tp.output
        messages.append({
            "role": "tool",
            "tool_call_id": tp.tool_id,
            "content": result_text or "",
        })
    return messages
