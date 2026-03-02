###
# tool/ask_user_tool.py — 向使用者提問工具
#
# 用途：AI 向使用者發送結構化問題（含選項），暫停等待回答
# 注意：實際的暫停/等待邏輯在 session/processor.py 中處理，此 tool 僅定義 schema
# 關聯：繼承 tool/base.py Tool，被 processor.py 特殊處理
###

from typing import Any

from tool.base import Tool, ToolContext, ToolResult


class AskUserTool(Tool):
    name = "ask_user"
    description = "向使用者提出問題。可提供選項讓使用者選擇。Processor 會暫停等待使用者回應。"
    parameters = {
        "question": {"type": "string", "description": "問題文字"},
        "options": {
            "type": "array",
            "items": {"type": "string"},
            "description": "選項列表（可選）",
            "optional": True,
        },
    }

    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult:
        # 實際的暫停/等待邏輯在 processor.py 中
        # 這個 execute 不會被直接呼叫
        return ToolResult(output="[由 processor 處理]")
