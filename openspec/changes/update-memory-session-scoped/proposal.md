# Change: 記憶體綁定 Session（不再跨 Session 共享）

## Why
記憶體跨 Session 共享不符合預期使用模式，應該每個 Session 有獨立的記憶空間，互不干擾。刪除 Session 時記憶一起 CASCADE 刪除。

## What Changes
- `user_memories` 表主鍵從 `(user_id, key)` 改為 `(session_id, key)`
- 所有記憶 CRUD 函數的 `user_id` 參數改為 `session_id`
- Memory tool 傳入 `ctx.session_id` 取代 `ctx.user_id`
- Processor 的 `build_system_prompt()` 改用 `memory_read(self.session_id)`
- Memory API 改用 `session_id` query param

## Impact
- Affected specs: `session-management`
- Affected code: `src/storage/database.py`, `src/session/memory.py`, `src/tool/memory_tool.py`, `src/session/processor.py`, `src/api/memory.py`

## BREAKING
舊的 user_memories 資料將無法遷移（無法對應 session），migration 會 DROP 重建。
