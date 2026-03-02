# Project Context

## Purpose
py-opencode 是 AI Agent 後端服務，參考 OpenCode / Claude Code 架構，以 Python + FastAPI 實作。目標用戶為 5-10 人研究團隊，支援多模型、Skills 擴展、沙盒執行。

## Tech Stack
- Python 3.11+
- FastAPI + Uvicorn（HTTP + WebSocket）
- litellm（統一呼叫 100+ LLM）
- aiosqlite（SQLite 持久化）
- PyYAML（Skills frontmatter 解析）

## Project Conventions

### Code Style
- 繁體中文註解與錯誤訊息
- 每個檔案開頭包含 `###` spec 描述區塊
- 有意義的變數和函數名稱，避免重複程式碼

### Architecture Patterns
- 單一 FastAPI 入口（`src/main.py`）
- LLM Provider 透過 litellm 統一呼叫，model 字串帶 provider 前綴
- Processor 狀態機：非串流 chat() → 解析 tool_calls → 執行工具 → 送回 LLM 循環
- Tool 基類 + ToolRegistry 自動註冊
- Skills 三層結構：SKILL.md + references/ + scripts/

### Testing Strategy
- pytest + pytest-asyncio
- 目標覆蓋率 70%+
- 提交前執行所有測試

### Git Workflow
- 提交訊息使用中文
- main 分支保持穩定

## Domain Context
研究團隊用 AI 助理：文獻搜尋、資料分析、程式碼執行。Skills 系統讓非工程師可擴展 domain knowledge。

## Important Constraints
- 單機部署（不做叢集）
- 不實作前端（純後端 API）
- subprocess 沙盒（非 Docker 隔離）

## External Dependencies
- LLM API：Claude / GPT / Gemini / Ollama（透過 litellm）
- SQLite：本地持久化（sessions / messages / user_memories）
