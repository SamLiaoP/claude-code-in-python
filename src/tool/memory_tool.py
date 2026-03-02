###
# tool/memory_tool.py — 記憶讀寫工具
#
# 用途：AI 透過此 tool 讀寫當前 Session 的記憶
# 關聯：繼承 tool/base.py Tool，使用 session/memory.py
###

from typing import Any

from tool.base import Tool, ToolContext, ToolResult


class MemoryReadTool(Tool):
    name = "memory_read"
    description = "讀取當前 Session 的記憶。不給 key 則列出全部記憶。"
    parameters = {
        "key": {"type": "string", "description": "記憶的 key（可選，不給則列出全部）", "optional": True},
    }

    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult:
        from session.memory import memory_read
        key = params.get("key")
        memories = await memory_read(ctx.session_id, key)
        if not memories:
            return ToolResult(output="沒有記憶" if not key else f"找不到記憶: {key}")
        lines = [f"- {m['key']}: {m['value']}" for m in memories]
        return ToolResult(output="\n".join(lines))


class MemoryWriteTool(Tool):
    name = "memory_write"
    description = "寫入當前 Session 的記憶。用於記住使用者偏好、研究脈絡等。"
    parameters = {
        "key": {"type": "string", "description": "記憶的 key"},
        "value": {"type": "string", "description": "記憶的 value"},
    }

    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult:
        from session.memory import memory_write
        key = params.get("key", "")
        value = params.get("value", "")
        if not key:
            return ToolResult(error="key 參數必填")
        await memory_write(ctx.session_id, key, value)
        return ToolResult(output=f"已記住: {key} = {value}")
