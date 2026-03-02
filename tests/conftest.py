###
# tests/conftest.py — 測試共用 fixtures
###

import sys
from pathlib import Path

import pytest
import pytest_asyncio

# 確保 src/ 目錄在 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest_asyncio.fixture
async def db():
    """建立記憶體中的測試資料庫"""
    from storage.database import init_db, close_db
    conn = await init_db(":memory:")
    yield conn
    await close_db()


@pytest.fixture
def tool_registry():
    """建立包含所有工具的 registry"""
    from tool.base import ToolRegistry
    from tool.python_tool import PythonTool
    from tool.bash_tool import BashTool
    from tool.file_tool import ReadFileTool, WriteFileTool
    from tool.memory_tool import MemoryReadTool, MemoryWriteTool
    from tool.ask_user_tool import AskUserTool
    from tool.skill_tool import SkillTool

    registry = ToolRegistry()
    registry.register(PythonTool(timeout=10))
    registry.register(BashTool(timeout=10))
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(MemoryReadTool())
    registry.register(MemoryWriteTool())
    registry.register(AskUserTool())
    registry.register(SkillTool())
    return registry
