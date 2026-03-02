###
# tool/bash_tool.py — Shell 沙盒執行
#
# 用途：透過 subprocess 執行 Shell 命令，timeout 60s
# 關聯：繼承 tool/base.py Tool
###

import asyncio
from typing import Any

from tool.base import Tool, ToolContext, ToolResult


class BashTool(Tool):
    name = "bash"
    description = "執行 Shell 命令。用於檔案操作、系統命令等。"
    parameters = {
        "command": {"type": "string", "description": "要執行的 Shell 命令"},
        "cwd": {"type": "string", "description": "工作目錄（可選）", "optional": True},
    }

    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult:
        command = params.get("command", "")
        if not command.strip():
            return ToolResult(error="命令不能為空")

        cwd = params.get("cwd")

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout,
            )
            output = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")
            if proc.returncode != 0:
                return ToolResult(output=output, error=err or f"Exit code: {proc.returncode}")
            combined = output
            if err:
                combined += f"\n[stderr]\n{err}"
            return ToolResult(output=combined)
        except asyncio.TimeoutError:
            proc.kill()
            return ToolResult(error=f"執行超時（{self.timeout} 秒）")
