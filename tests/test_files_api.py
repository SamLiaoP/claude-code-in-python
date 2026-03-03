###
# tests/test_files_api.py — Files API 測試
#
# 用途：測試 GET /api/files 目錄瀏覽端點
# 主要功能：
#   - 測試正常列出檔案
#   - 測試路徑遍歷防護
#   - 測試不存在的 Session
# 關聯：測試 src/api/files.py, src/session/session.py
###

import pytest
import pytest_asyncio
from pathlib import Path
from httpx import ASGITransport, AsyncClient

from auth import init_auth
from config import AppConfig, ProviderConfig
from main import app
from storage.database import init_db, close_db
from session.session import create_session


@pytest_asyncio.fixture
async def client(tmp_path):
    """建立測試用 HTTP client"""
    # 初始化 DB
    await init_db(":memory:")

    # 初始化 Auth
    init_auth({"test-key": "user1"})

    # 注入 config
    from api.sessions import init_sessions_api
    from api.chat import init_chat_api
    from tool.base import ToolRegistry

    config = AppConfig(
        providers={"local": ProviderConfig(model="ollama/llama3")},
        default_provider="local",
        api_keys={"test-key": "user1"},
    )
    init_sessions_api(config)
    init_chat_api(config, ToolRegistry())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    await close_db()


@pytest.mark.asyncio
async def test_list_files(client, tmp_path):
    """測試正常列出檔案"""
    # 建立測試目錄結構
    project_dir = str(tmp_path / "project")
    Path(project_dir).mkdir()
    (Path(project_dir) / "hello.txt").write_text("hello")
    (Path(project_dir) / "subdir").mkdir()

    # 建立 session 指定此 project_dir
    session = await create_session("user1", "local", project_dir, skip_workdir=True)
    sid = session["id"]

    res = await client.get(
        f"/api/files?session_id={sid}&path=.",
        headers={"Authorization": "Bearer test-key"},
    )
    assert res.status_code == 200
    data = res.json()
    names = [e["name"] for e in data["entries"]]
    assert "hello.txt" in names
    assert "subdir" in names

    # 驗證 type
    for e in data["entries"]:
        if e["name"] == "hello.txt":
            assert e["type"] == "file"
            assert e["size"] == 5
        if e["name"] == "subdir":
            assert e["type"] == "directory"


@pytest.mark.asyncio
async def test_path_traversal_blocked(client, tmp_path):
    """測試路徑遍歷防護"""
    project_dir = str(tmp_path / "project")
    Path(project_dir).mkdir()

    session = await create_session("user1", "local", project_dir, skip_workdir=True)
    sid = session["id"]

    res = await client.get(
        f"/api/files?session_id={sid}&path=../../etc",
        headers={"Authorization": "Bearer test-key"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_files_invalid_session(client):
    """測試不存在的 Session"""
    res = await client.get(
        "/api/files?session_id=nonexistent&path=.",
        headers={"Authorization": "Bearer test-key"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_providers_api(client):
    """測試 GET /api/providers"""
    res = await client.get(
        "/api/providers",
        headers={"Authorization": "Bearer test-key"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["name"] == "local"
    assert data[0]["model"] == "ollama/llama3"


@pytest.mark.asyncio
async def test_patch_session_provider(client, tmp_path):
    """測試 PATCH /api/sessions/{id} 切換 Provider"""
    session = await create_session("user1", "local", skip_workdir=True)
    sid = session["id"]

    # 切換到存在的 provider
    res = await client.patch(
        f"/api/sessions/{sid}",
        json={"provider": "local"},
        headers={"Authorization": "Bearer test-key"},
    )
    assert res.status_code == 200
    assert res.json()["provider"] == "local"


@pytest.mark.asyncio
async def test_patch_session_invalid_provider(client):
    """測試切換到不存在的 Provider"""
    session = await create_session("user1", "local", skip_workdir=True)
    sid = session["id"]

    res = await client.patch(
        f"/api/sessions/{sid}",
        json={"provider": "nonexistent"},
        headers={"Authorization": "Bearer test-key"},
    )
    assert res.status_code == 400
