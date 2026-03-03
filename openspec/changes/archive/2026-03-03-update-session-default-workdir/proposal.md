# Change: Session 建立時預設自動建立工作目錄

## Why
目前建立 Session 時若未傳入 `project_dir`，不會初始化任何工作目錄，使用者容易遺漏。應改為預設自動建立，同時保留可選擇不建立的彈性。

## What Changes
- `POST /api/sessions` 不帶 `project_dir` 時，自動使用預設路徑（`~/.py-opencode/projects/<session_id>/`）建立工作目錄
- 新增 `skip_workdir` 欄位（預設 `false`），設為 `true` 時跳過工作目錄初始化
- `session.py` 的 `create_session` 邏輯調整：無 project_dir 時自動生成預設路徑

## Impact
- Affected specs: `session-management`
- Affected code: `src/api/sessions.py`, `src/session/session.py`
