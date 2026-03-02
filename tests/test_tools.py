###
# tests/test_tools.py — Tool 系統測試
###

import os
import tempfile

import pytest

from tool.base import ToolContext, ToolRegistry
from tool.python_tool import PythonTool
from tool.bash_tool import BashTool
from tool.file_tool import ReadFileTool, WriteFileTool


def _ctx() -> ToolContext:
    return ToolContext(session_id="test", user_id="test-user")


@pytest.mark.asyncio
async def test_python_tool_basic():
    tool = PythonTool(timeout=10)
    result = await tool.execute({"code": "print(1 + 1)"}, _ctx())
    assert "2" in result.output
    assert result.error is None


@pytest.mark.asyncio
async def test_python_tool_timeout():
    tool = PythonTool(timeout=2)
    result = await tool.execute({"code": "import time; time.sleep(10)"}, _ctx())
    assert result.error is not None
    assert "超時" in result.error


@pytest.mark.asyncio
async def test_python_tool_error():
    tool = PythonTool(timeout=10)
    result = await tool.execute({"code": "raise ValueError('test error')"}, _ctx())
    assert result.error is not None


@pytest.mark.asyncio
async def test_bash_tool_basic():
    tool = BashTool(timeout=10)
    result = await tool.execute({"command": "echo hello"}, _ctx())
    assert "hello" in result.output


@pytest.mark.asyncio
async def test_bash_tool_with_cwd():
    tool = BashTool(timeout=10)
    result = await tool.execute({"command": "pwd", "cwd": "/tmp"}, _ctx())
    assert "/tmp" in result.output or "/private/tmp" in result.output


@pytest.mark.asyncio
async def test_file_tools():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("line1\nline2\nline3\n")
        tmp_path = f.name

    try:
        # read
        read_tool = ReadFileTool()
        result = await read_tool.execute({"path": tmp_path}, _ctx())
        assert "line1" in result.output
        assert "line3" in result.output

        # read with offset/limit
        result = await read_tool.execute({"path": tmp_path, "offset": 1, "limit": 1}, _ctx())
        assert "line2" in result.output
        assert "line1" not in result.output

        # write
        write_tool = WriteFileTool()
        new_path = tmp_path + ".out"
        result = await write_tool.execute({"path": new_path, "content": "new content"}, _ctx())
        assert "已寫入" in result.output

        # verify write
        result = await read_tool.execute({"path": new_path}, _ctx())
        assert "new content" in result.output
    finally:
        os.unlink(tmp_path)
        if os.path.exists(tmp_path + ".out"):
            os.unlink(tmp_path + ".out")


@pytest.mark.asyncio
async def test_memory_tools(db):
    from tool.memory_tool import MemoryWriteTool, MemoryReadTool

    ctx = ToolContext(session_id="test", user_id="mem-test-user")
    write_tool = MemoryWriteTool()
    read_tool = MemoryReadTool()

    # 寫入
    result = await write_tool.execute({"key": "focus", "value": "AI 安全"}, ctx)
    assert "已記住" in result.output

    # 讀取
    result = await read_tool.execute({"key": "focus"}, ctx)
    assert "AI 安全" in result.output

    # 列出全部
    result = await read_tool.execute({}, ctx)
    assert "focus" in result.output


@pytest.mark.asyncio
async def test_tool_registry():
    registry = ToolRegistry()
    registry.register(PythonTool())
    registry.register(BashTool())

    assert "python" in registry.list_tools()
    assert "bash" in registry.list_tools()

    schemas = registry.get_tools_schema()
    assert len(schemas) == 2
    assert schemas[0]["function"]["name"] in ("python", "bash")

    tool = registry.get_tool("python")
    assert tool is not None
    assert registry.get_tool("nonexistent") is None
