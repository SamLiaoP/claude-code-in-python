## ADDED Requirements
### Requirement: 重試狀態推送
系統 MUST 在 LLM API 速率限制重試時，透過 WebSocket 推送 `{ "type": "status", "message": "..." }` 事件，通知前端目前正在重試。

#### Scenario: 前端收到重試提示
- **WHEN** LLM Provider 觸發 429 重試
- **THEN** WebSocket 推送 status 事件，前端顯示帶動畫的等待提示

#### Scenario: 重試成功後提示消失
- **WHEN** 重試成功，LLM 開始回傳內容
- **THEN** 前端自動移除狀態提示，顯示正常回應
