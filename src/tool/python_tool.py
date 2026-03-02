###
# tool/python_tool.py — Python 沙盒執行
#
# 用途：透過 subprocess 安全執行 AI 產生的 Python 程式碼
# 主要功能：subprocess + asyncio.wait_for timeout 30s，stdout 截斷至 max_output
# 關聯：繼承 tool/base.py Tool
###

import asyncio
import tempfile
from typing import Any

from tool.base import Tool, ToolContext, ToolResult


class PythonTool(Tool):
    name = "python"
    description = "執行 Python 程式碼。用於資料分析、計算、API 呼叫等。程式碼會在獨立 subprocess 中執行。"
    parameters = {
        "code": {"type": "string", "description": "要執行的 Python 程式碼"},
    }

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult:
        code = params.get("code", "")
        if not code.strip():
            return ToolResult(error="程式碼不能為空")

        # 寫入臨時檔案執行
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            tmp_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout,
            )
            output = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")
            if proc.returncode != 0:
                return ToolResult(output=output, error=err or f"Exit code: {proc.returncode}")
            # 合併 stdout + stderr
            combined = output
            if err:
                combined += f"\n[stderr]\n{err}"
            return ToolResult(output=combined)
        except asyncio.TimeoutError:
            proc.kill()
            return ToolResult(error=f"執行超時（{self.timeout} 秒）")
        finally:
            import os
            os.unlink(tmp_path)
