###
# main.py — FastAPI 入口
#
# 用途：掛載所有路由，啟動初始化（DB / Auth / Skills / Tools）
# 主要功能：
#   - lifespan: 啟動時初始化 DB、Auth、Skills、Tools
#   - 掛載 api/chat, api/sessions, api/skills, api/memory 路由
# 關聯：整合所有模組
###

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from api.chat import init_chat_api, router as chat_router
from api.memory import router as memory_router
from api.sessions import init_sessions_api, router as sessions_router
from api.skills import router as skills_router
from auth import init_auth
from config import GLOBAL_CONFIG_DIR, load_config
from skill import scan_skills
from storage.database import close_db, init_db
from tool.ask_user_tool import AskUserTool
from tool.base import ToolRegistry
from tool.bash_tool import BashTool
from tool.file_tool import ReadFileTool, WriteFileTool
from tool.memory_tool import MemoryReadTool, MemoryWriteTool
from tool.python_tool import PythonTool
from tool.skill_tool import SkillTool

import os
_log_level = os.environ.get("LOG_LEVEL", "DEBUG").upper()
_log_file = os.path.join(os.path.dirname(__file__), "..", "logs", "app.log")
os.makedirs(os.path.dirname(_log_file), exist_ok=True)
logging.basicConfig(
    level=getattr(logging, _log_level, logging.DEBUG),
    format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(_log_file, encoding="utf-8")],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """啟動與關閉邏輯"""
    # 載入設定
    config = load_config()
    logger.info(f"載入設定完成，預設 provider: {config.default_provider}")

    # 確保設定目錄存在
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # 初始化 DB
    await init_db(config.db_path)
    logger.info(f"資料庫初始化完成: {config.db_path}")

    # 初始化 Auth
    init_auth(config.api_keys)

    # 掃描 Skills
    skill_count = scan_skills()
    logger.info(f"已索引 {skill_count} 個 Skills")

    # 註冊 Tools
    registry = ToolRegistry()
    timeout = config.sandbox.timeout
    registry.register(PythonTool(timeout=timeout))
    registry.register(BashTool(timeout=timeout * 2))  # bash timeout = 2x python
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(MemoryReadTool())
    registry.register(MemoryWriteTool())
    registry.register(AskUserTool())
    registry.register(SkillTool())
    logger.info(f"已註冊 {len(registry.list_tools())} 個 Tools: {registry.list_tools()}")

    # 注入依賴
    init_sessions_api(config)
    init_chat_api(config, registry)

    yield

    # 關閉
    await close_db()
    logger.info("服務已關閉")


app = FastAPI(title="py-opencode", version="0.1.0", lifespan=lifespan)

# 掛載路由
app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(skills_router)
app.include_router(memory_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
