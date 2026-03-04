## ADDED Requirements
### Requirement: API 速率限制自動重試
Provider MUST 在收到 429 Too Many Requests 時自動重試，最多 3 次，間隔遞增（5秒 → 15秒 → 30秒）。每次重試 MUST 透過可選的 on_retry callback 通知呼叫方。重試全部失敗後 MUST 拋出原始例外。

#### Scenario: 429 自動重試成功
- **WHEN** LLM API 回傳 429 狀態碼
- **THEN** 系統等待後自動重試，成功後回傳正常結果

#### Scenario: 重試全部失敗
- **WHEN** LLM API 連續 4 次（初始 + 3 次重試）回傳 429
- **THEN** 系統拋出 RateLimitError 例外
