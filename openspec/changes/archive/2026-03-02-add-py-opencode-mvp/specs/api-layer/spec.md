## ADDED Requirements

### Requirement: WebSocket 對話 API
系統 MUST 提供 `WS /ws/chat/{session_id}?token=<api-key>` 端點，支援串流推送以下事件：text_delta、tool_start、tool_result、question、done、error。

#### Scenario: 串流對話
- **WHEN** 客戶端透過 WebSocket 發送 `{ "type": "message", "content": "..." }`
- **THEN** 伺服器串流推送 text_delta 事件，最後推送 done 事件

#### Scenario: 工具執行事件
- **WHEN** AI 呼叫工具
- **THEN** 伺服器依序推送 tool_start → tool_result 事件

#### Scenario: 中斷對話
- **WHEN** 客戶端發送 `{ "type": "abort" }`
- **THEN** 伺服器中斷當前 LLM 生成

### Requirement: Session REST API
系統 MUST 提供 Session CRUD REST 端點：GET /api/sessions、POST /api/sessions、DELETE /api/sessions/{id}。

#### Scenario: 建立 Session
- **WHEN** POST /api/sessions 帶 `{ "provider": "local" }`
- **THEN** 回傳新 Session 的 id、provider、created_at

### Requirement: Skills REST API
系統 MUST 提供 GET /api/skills（列出所有 Skills）和 POST /api/skills/reload（重新掃描 Skills）。

#### Scenario: 列出 Skills
- **WHEN** GET /api/skills
- **THEN** 回傳所有已索引的 Skill 名稱、描述、來源

### Requirement: Memory REST API
系統 MUST 提供 GET /api/memory 端點，查詢當前使用者的所有記憶。

#### Scenario: 查詢使用者記憶
- **WHEN** GET /api/memory
- **THEN** 回傳該使用者所有 key-value 記憶列表
