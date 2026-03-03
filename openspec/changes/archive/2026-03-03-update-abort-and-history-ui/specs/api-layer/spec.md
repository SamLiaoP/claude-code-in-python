## MODIFIED Requirements
### Requirement: WebSocket 對話 API
系統 MUST 提供 `WS /ws/chat/{session_id}?token=<api-key>` 端點，支援串流推送以下事件：text_delta、tool_start、tool_result、question、done、error、history。

WebSocket 連線後，系統 MUST 立即推送 `{ "type": "history", "messages": [...] }` 事件，包含該 Session 的所有歷史訊息。

系統 MUST 將 LLM 處理作為獨立 asyncio Task 執行，確保 abort 訊息能在 LLM 處理期間被即時接收與處理。

#### Scenario: 串流對話
- **WHEN** 客戶端透過 WebSocket 發送 `{ "type": "message", "content": "..." }`
- **THEN** 伺服器串流推送 text_delta 事件，最後推送 done 事件

#### Scenario: 工具執行事件
- **WHEN** AI 呼叫工具
- **THEN** 伺服器依序推送 tool_start → tool_result 事件

#### Scenario: 中斷對話
- **WHEN** 客戶端發送 `{ "type": "abort" }`
- **THEN** 伺服器立即取消正在執行的 LLM Task，中斷當前生成

#### Scenario: 連線後載入歷史
- **WHEN** 客戶端 WebSocket 連線成功
- **THEN** 伺服器推送 history 事件，包含所有歷史訊息（role、parts、created_at）
