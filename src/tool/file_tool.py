###
# tool/file_tool.py — 檔案讀寫工具
#
# 用途：提供 read_file / write_file 工具
# 關聯：繼承 tool/base.py Tool
###

from pathlib import Path
from typing import Any

from tool.base import Tool, ToolContext, ToolResult


class ReadFileTool(Tool):
    name = "read_file"
    description = "讀取檔案內容。可指定 offset 和 limit 讀取部分內容。"
    parameters = {
        "path": {"type": "string", "description": "檔案路徑"},
        "offset": {"type": "integer", "description": "起始行數（0-based）", "optional": True},
        "limit": {"type": "integer", "description": "讀取行數", "optional": True},
    }

    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = params.get("path", "")
        if not path:
            return ToolResult(error="path 參數必填")

        p = Path(path)
        if not p.exists():
            return ToolResult(error=f"檔案不存在: {path}")
        if not p.is_file():
            return ToolResult(error=f"不是檔案: {path}")

        try:
            lines = p.read_text(encoding="utf-8").splitlines()
            offset = params.get("offset", 0) or 0
            limit = params.get("limit")
            if limit:
                lines = lines[offset:offset + limit]
            else:
                lines = lines[offset:]
            return ToolResult(output="\n".join(lines))
        except Exception as e:
            return ToolResult(error=str(e))


class WriteFileTool(Tool):
    name = "write_file"
    description = "寫入檔案內容。會建立不存在的目錄。"
    parameters = {
        "path": {"type": "string", "description": "檔案路徑"},
        "content": {"type": "string", "description": "要寫入的內容"},
    }

    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = params.get("path", "")
        content = params.get("content", "")
        if not path:
            return ToolResult(error="path 參數必填")

        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return ToolResult(output=f"已寫入 {path}（{len(content)} 字元）")
        except Exception as e:
            return ToolResult(error=str(e))
