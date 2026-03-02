# session-management Specification — MODIFIED「個人 Memory」

### Requirement: 個人 Memory
系統 MUST 提供每個 Session 獨立的記憶空間，AI 可透過 `memory_read` / `memory_write` tool 操作。存儲於 SQLite `user_memories` 表，主鍵為 `(session_id, key)`。

#### Scenario: AI 寫入 Session 記憶
- **WHEN** AI 呼叫 `memory_write(key="research_focus", value="心血管藥物")`
- **THEN** 該記憶存入 user_memories 表，綁定當前 session_id

#### Scenario: 不同 Session 記憶不共享
- **WHEN** 同一使用者在 Session A 寫入記憶 `research_focus=心血管藥物`
- **AND** 在 Session B 呼叫 `memory_read(key="research_focus")`
- **THEN** 系統回傳空結果（找不到記憶）

#### Scenario: 刪除 Session 時記憶一起刪除
- **WHEN** 使用者刪除 Session A
- **THEN** Session A 的所有記憶透過 CASCADE 一起刪除
