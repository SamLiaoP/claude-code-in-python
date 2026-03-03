## ADDED Requirements
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
