# Change: 建立 py-opencode MVP（Phase 1-3）

## Why
建立一個研究導向的 AI Agent 後端服務，供 5-10 人研究團隊使用。參考 OpenCode / Claude Code 架構，以 Python (FastAPI) 實作，支援多模型對話、Skills 擴展、沙盒執行、多人持久化 Session。

## What Changes
- **ADDED** 統一 LLM Provider：使用 `anthropic` SDK，透過 `base_url` 切換 Ollama / Claude / 其他相容服務
- **ADDED** Skills 系統：相容 OpenCode SKILL.md 格式，透過 meta-tool 動態載入 domain knowledge
- **ADDED** Session 管理：SQLite 持久化，支援多人獨立 Session、中斷續接
- **ADDED** Tool 系統：python / bash 沙盒執行、檔案讀寫、memory 讀寫、ask_user 互動、skill meta-tool
- **ADDED** 認證系統：靜態 API Key 認證，支援 HTTP Header 和 WebSocket query parameter
- **ADDED** WebSocket 對話 API：串流推送 text_delta / tool_start / tool_result / question / done 事件
- **ADDED** REST API：Session CRUD、Skills 列表、Memory 查詢
- **ADDED** 個人 Memory：跨 Session 記憶，AI 可主動讀寫
- **ADDED** 專案上下文注入：PROJECT.md 自動注入 system prompt

## Impact
- Affected specs: llm-provider, session-management, tool-system, api-layer, auth-system（全部新建）
- Affected code: 全新專案，建立完整目錄結構（src/ 下：main.py, config.py, provider.py, skill.py, auth.py, tool/, session/, api/, storage/）
