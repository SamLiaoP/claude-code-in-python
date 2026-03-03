# api-layer Specification

## Purpose
TBD - created by archiving change add-py-opencode-mvp. Update Purpose after archive.
## Requirements
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

### Requirement: Files REST API
系統 MUST 提供 GET /api/files 端點，列出 Session 專案目錄下的檔案與資料夾。path 參數相對於 project_dir，MUST 驗證路徑不超出 project_dir 範圍。

#### Scenario: 列出專案根目錄
- **WHEN** GET /api/files?session_id=xxx&path=.
- **THEN** 回傳 project_dir 下的檔案/資料夾列表，含 name、type、size

#### Scenario: 路徑遍歷防護
- **WHEN** GET /api/files?session_id=xxx&path=../../etc
- **THEN** 回傳 403 錯誤

### Requirement: Providers REST API
系統 MUST 提供 GET /api/providers 端點，列出所有已設定的 LLM Provider 名稱與模型，不洩漏 API Key。

#### Scenario: 列出可用 Provider
- **WHEN** GET /api/providers
- **THEN** 回傳 [{ name, model }] 列表

### Requirement: 靜態前端服務
系統 MUST 透過 FastAPI StaticFiles 在根路徑 / 提供 src/static/ 下的前端靜態檔案。

#### Scenario: 存取前端頁面
- **WHEN** 瀏覽器存取 http://localhost:8000/
- **THEN** 回傳 index.html

