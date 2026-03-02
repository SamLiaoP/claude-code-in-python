###
# tests/test_api.py — REST API + WebSocket 測試
###

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from main import app
from auth import init_auth
from storage.database import init_db, close_db
from api.sessions import init_sessions_api
from api.chat import init_chat_api
from config import load_config
from tool.base import ToolRegistry


@pytest_asyncio.fixture(autouse=True)
async def setup_app():
    """初始化 DB 和 Auth 供 API 測試使用"""
    init_auth({"test-key-1": "user1", "test-key-2": "user2"})
    await init_db(":memory:")
    config = load_config()
    init_sessions_api(config)
    init_chat_api(config, ToolRegistry())
    yield
    await close_db()


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_session_crud_api():
    transport = ASGITransport(app=app)
    headers = {"Authorization": "Bearer test-key-1"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 建立
        resp = await client.post("/api/sessions", json={"provider": "local"}, headers=headers)
        assert resp.status_code == 200
        session_id = resp.json()["id"]

        # 列出
        resp = await client.get("/api/sessions", headers=headers)
        assert resp.status_code == 200
        sessions = resp.json()
        assert any(s["id"] == session_id for s in sessions)

        # user2 看不到
        headers2 = {"Authorization": "Bearer test-key-2"}
        resp = await client.get("/api/sessions", headers=headers2)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

        # 刪除
        resp = await client.delete(f"/api/sessions/{session_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/sessions", headers={"Authorization": "Bearer bad-key"})
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_skills_api():
    transport = ASGITransport(app=app)
    headers = {"Authorization": "Bearer test-key-1"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/skills", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_session_with_project_dir():
    """POST /api/sessions 帶 project_dir 後目錄被初始化"""
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        transport = ASGITransport(app=app)
        headers = {"Authorization": "Bearer test-key-1"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/sessions",
                json={"provider": "local", "project_dir": tmpdir},
                headers=headers,
            )
            assert resp.status_code == 200
            assert resp.json()["project_dir"] == tmpdir

        # 檢查目錄結構
        base = os.path.join(tmpdir, ".py-opencode")
        assert os.path.isdir(os.path.join(base, "skills"))
        assert os.path.isdir(os.path.join(base, "context"))
        assert os.path.isfile(os.path.join(base, "context", "PROJECT.md"))


@pytest.mark.asyncio
async def test_create_session_default_workdir():
    """POST /api/sessions 不帶 project_dir 時自動建立工作目錄"""
    import os, shutil
    transport = ASGITransport(app=app)
    headers = {"Authorization": "Bearer test-key-1"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/sessions",
            json={"provider": "local"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        project_dir = data["project_dir"]
        assert project_dir is not None
        assert data["id"] in project_dir
        # 驗證目錄結構
        base = os.path.join(project_dir, ".py-opencode")
        assert os.path.isdir(os.path.join(base, "skills"))
        assert os.path.isdir(os.path.join(base, "context"))
    # 清理
    if os.path.isdir(project_dir):
        shutil.rmtree(project_dir)


@pytest.mark.asyncio
async def test_create_session_skip_workdir():
    """POST /api/sessions 帶 skip_workdir=True 時 project_dir 為 None"""
    transport = ASGITransport(app=app)
    headers = {"Authorization": "Bearer test-key-1"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/sessions",
            json={"provider": "local", "skip_workdir": True},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["project_dir"] is None


@pytest.mark.asyncio
async def test_memory_api():
    transport = ASGITransport(app=app)
    headers = {"Authorization": "Bearer test-key-1"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/memory", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
