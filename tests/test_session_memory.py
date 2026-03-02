###
# tests/test_session_memory.py — Session + Memory 隔離測試
###

import pytest

from session.session import create_session, list_sessions, get_session, delete_session, save_message, load_messages
from session.memory import memory_read, memory_write, memory_delete
from session.message import Message


@pytest.mark.asyncio
async def test_session_crud(db):
    """建立、列出、刪除 Session"""
    s = await create_session("user1", "local")
    assert s["provider"] == "local"

    sessions = await list_sessions("user1")
    assert len(sessions) == 1
    assert sessions[0]["id"] == s["id"]

    # 其他使用者看不到
    sessions2 = await list_sessions("user2")
    assert len(sessions2) == 0

    # 刪除
    ok = await delete_session(s["id"], "user1")
    assert ok
    sessions = await list_sessions("user1")
    assert len(sessions) == 0


@pytest.mark.asyncio
async def test_session_ownership(db):
    """使用者只能存取自己的 Session"""
    s = await create_session("user1", "local")
    # user2 無法取得
    result = await get_session(s["id"], "user2")
    assert result is None
    # user1 可以取得
    result = await get_session(s["id"], "user1")
    assert result is not None


@pytest.mark.asyncio
async def test_message_persistence(db):
    """訊息儲存與載入"""
    s = await create_session("user1", "local")
    msg = Message.user("Hello")
    await save_message(s["id"], msg)

    messages = await load_messages(s["id"])
    assert len(messages) == 1
    assert messages[0].parts[0].text == "Hello"


@pytest.mark.asyncio
async def test_auto_title(db):
    """自動從第一則訊息生成 title"""
    s = await create_session("user1", "local")
    msg = Message.user("幫我搜尋 PubMed 關於 statins 的文獻")
    await save_message(s["id"], msg)

    session = await get_session(s["id"], "user1")
    assert session["title"] is not None
    assert "statins" in session["title"]


@pytest.mark.asyncio
async def test_memory_isolation(db):
    """不同使用者的記憶互相隔離"""
    await memory_write("user1", "focus", "心血管")
    await memory_write("user2", "focus", "腫瘤學")

    m1 = await memory_read("user1", "focus")
    assert len(m1) == 1
    assert m1[0]["value"] == "心血管"

    m2 = await memory_read("user2", "focus")
    assert len(m2) == 1
    assert m2[0]["value"] == "腫瘤學"


@pytest.mark.asyncio
async def test_memory_crud(db):
    """記憶的讀寫刪"""
    await memory_write("user1", "key1", "val1")
    await memory_write("user1", "key2", "val2")

    all_mem = await memory_read("user1")
    assert len(all_mem) == 2

    # 更新
    await memory_write("user1", "key1", "updated")
    m = await memory_read("user1", "key1")
    assert m[0]["value"] == "updated"

    # 刪除
    ok = await memory_delete("user1", "key1")
    assert ok
    all_mem = await memory_read("user1")
    assert len(all_mem) == 1
