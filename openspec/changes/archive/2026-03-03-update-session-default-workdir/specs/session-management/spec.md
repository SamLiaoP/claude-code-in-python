## MODIFIED Requirements
### Requirement: Session CRUD
系統 MUST 提供 Session 的建立、列出、續接、刪除功能。每個 Session 綁定 user_id，只有本人可存取。

#### Scenario: 建立新 Session
- **WHEN** 使用者發送 POST /api/sessions 帶 provider 和 project_dir
- **THEN** 系統建立新 Session 並回傳 id、provider、project_dir、created_at

#### Scenario: 建立 Session 未指定 project_dir 時自動建立工作目錄
- **WHEN** 使用者發送 POST /api/sessions 未帶 project_dir 且 skip_workdir 為 false（預設）
- **THEN** 系統自動使用 `~/.py-opencode/projects/<session_id>/` 作為 project_dir
- **AND** 初始化該目錄下的 .py-opencode/skills/ 和 .py-opencode/context/ 結構

#### Scenario: 建立 Session 時跳過工作目錄
- **WHEN** 使用者發送 POST /api/sessions 帶 skip_workdir=true
- **THEN** 系統不建立任何工作目錄，project_dir 為 null

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
