## ADDED Requirements

### Requirement: 靜態 API Key 認證
系統 MUST 使用 config.json 中的 `api_keys` 物件進行認證，格式為 `{ "key-xxx": "user1" }`。不使用 JWT。

#### Scenario: HTTP 請求認證
- **WHEN** REST 請求帶 `Authorization: Bearer <api-key>` header
- **THEN** 系統驗證 key 並識別對應的 user_id

#### Scenario: WebSocket 連線認證
- **WHEN** WebSocket 連線帶 `?token=<api-key>` query parameter
- **THEN** 系統驗證 key 並識別對應的 user_id

#### Scenario: 無效 API Key
- **WHEN** 請求帶無效的 API Key
- **THEN** 系統回傳 401 Unauthorized
