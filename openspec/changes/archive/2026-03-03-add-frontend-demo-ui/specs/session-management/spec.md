## ADDED Requirements
### Requirement: 切換 Session Provider
系統 MUST 提供 PATCH /api/sessions/{id} 端點，允許更新 Session 的 provider 欄位。更新後，前端需重新連線 WebSocket 使新 Provider 生效。

#### Scenario: 切換 Provider
- **WHEN** PATCH /api/sessions/{id} 帶 { "provider": "claude" }
- **THEN** 該 Session 的 provider 欄位更新為 "claude"
- **AND** 下次 WebSocket 連線使用新的 Provider

#### Scenario: 指定不存在的 Provider
- **WHEN** PATCH /api/sessions/{id} 帶 { "provider": "不存在" }
- **THEN** 回傳 400 錯誤
