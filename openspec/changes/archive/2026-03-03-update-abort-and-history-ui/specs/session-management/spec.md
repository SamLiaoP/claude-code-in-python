## MODIFIED Requirements
### Requirement: Session 持久化與續接
Session 和訊息 MUST 持久化至 SQLite。使用者重新連線 WebSocket 時，系統 MUST 載入歷史訊息送給 LLM 維持上下文，並推送歷史訊息到前端供使用者查看。

#### Scenario: 中斷後續接對話
- **WHEN** 使用者斷線後重新連線至已有 Session 的 WebSocket
- **THEN** 系統載入該 Session 歷史訊息，LLM 能延續先前上下文繼續回答

#### Scenario: 前端顯示歷史對話
- **WHEN** 使用者在前端點選既有 Session
- **THEN** 前端顯示該 Session 的完整對話紀錄，包含 user 訊息、assistant 回應及工具呼叫結果
