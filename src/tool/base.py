###
# tool/base.py — Tool 基類 + ToolRegistry 註冊表
#
# 用途：定義所有工具的基礎介面和全域註冊表
# 主要功能：
#   - Tool 基類：name, description, parameters, execute()
#   - get_schema() 回傳 OpenAI function calling 格式（供 LiteLLM 使用）
#   - ToolResult 資料類別
#   - ToolContext 執行上下文
#   - ToolRegistry 單例註冊表
# 關聯：被 tool/*.py 繼承，被 session/processor.py 使用
###

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    output: str = ""
    metadata: dict = field(default_factory=dict)
    error: str | None = None


@dataclass
class ToolContext:
    session_id: str
    user_id: str
    abort: asyncio.Event = field(default_factory=asyncio.Event)


class Tool(ABC):
    """工具基類"""
    name: str = ""
    description: str = ""
    parameters: dict = {}  # JSON Schema

    @abstractmethod
    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult:
        ...

    def get_schema(self) -> dict:
        """回傳 OpenAI function calling 格式（供 LiteLLM 使用）"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": [k for k, v in self.parameters.items() if not v.get("optional")],
                },
            },
        }


class ToolRegistry:
    """工具註冊表"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def get_tools_schema(self) -> list[dict]:
        return [t.get_schema() for t in self._tools.values()]

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())
