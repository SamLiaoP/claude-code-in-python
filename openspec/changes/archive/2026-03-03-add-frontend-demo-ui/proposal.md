# Change: 新增前端展示介面

## Why
py-opencode 目前是純後端 API，沒有任何 UI。需要一個前端讓使用者可以視覺化管理 Sessions、查看 Skills 和目錄、切換 Provider。

## What Changes
- 新增 Files REST API（目錄瀏覽）
- 新增 Providers REST API（列出可用 LLM）
- 新增 PATCH /api/sessions/{id}（切換 Provider）
- 新增前端靜態檔案（HTML + JS + CSS）
- 修改 main.py mount StaticFiles

## Impact
- Affected specs: api-layer, session-management
- Affected code: src/main.py, src/api/sessions.py, src/session/session.py, 新增 src/api/files.py + src/static/
