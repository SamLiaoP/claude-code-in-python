# session-management Specification

## Purpose
TBD - created by archiving change add-py-opencode-mvp. Update Purpose after archive.
## Requirements
### Requirement: Session CRUD
系統 MUST 提供 Session 的建立、列出、續接、刪除功能。每個 Session 綁定 user_id，只有本人可存取。

#### Scenario: 建立新 Session
- **WHEN** 使用者發送 POST /api/sessions 帶 provider 和 project_dir
- **THEN** 系統建立新 Session 並回傳 id、provider、created_at

#### Scenario: 建立 Session 時初始化專案目錄
- **WHEN** 使用者發送 POST /api/sessions 帶 project_dir
- **THEN** 系統在 project_dir 下建立 .py-opencode/skills/ 和 .py-opencode/context/ 目錄
- **AND** 若 .py-opencode/context/PROJECT.md 不存在，建立空白範本

#### Scenario: 列出使用者 Session
- **WHEN** 使用者發送 GET /api/sessions
- **THEN** 系統回傳該使用者所有 Session 列表（不含其他使用者）

#### Scenario: 刪除 Session
- **WHEN** 使用者發送 DELETE /api/sessions/{id}
- **THEN** 系統刪除該 Session 及其所有訊息

### Requirement: Session 持久化與續接
Session 和訊息 MUST 持久化至 SQLite。使用者重新連線 WebSocket 時，系統 MUST 載入歷史訊息送給 LLM 維持上下文。

#### Scenario: 中斷後續接對話
- **WHEN** 使用者斷線後重新連線至已有 Session 的 WebSocket
- **THEN** 系統載入該 Session 歷史訊息，LLM 能延續先前上下文繼續回答

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

### Requirement: 專案上下文注入
系統 MUST 在建立 Session 時讀取 `<project>/.py-opencode/context/PROJECT.md`，自動注入 system prompt。

#### Scenario: PROJECT.md 存在時注入
- **WHEN** Session 指定的 project_dir 下存在 `.py-opencode/context/PROJECT.md`
- **THEN** 系統將其內容注入 system prompt 開頭

