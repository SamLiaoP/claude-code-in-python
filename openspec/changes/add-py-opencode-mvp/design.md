## Context
py-opencode 是全新的 AI Agent 後端服務，參考 OpenCode / Claude Code 架構，以 Python + FastAPI 實作。目標用戶為 5-10 人研究團隊，需支援多模型、Skills 擴展、沙盒執行。

## Goals / Non-Goals
- Goals：
  - 統一 anthropic SDK 存取多 LLM（Ollama / Claude）
  - Skills 系統讓非工程師可擴展 domain knowledge
  - 多人獨立 Session + 跨 Session Memory
  - 安全沙盒執行 Python / Shell
- Non-Goals：
  - 不引入 langchain / litellm 等重框架
  - 不實作前端（純後端 API）
  - 不做叢集 / 高可用部署
  - 不實作 permission 細粒度權限控制（延後）

## Decisions
- **單一 SDK 策略**：只用 `anthropic` SDK，Ollama v0.14+ 支援 Anthropic API 相容格式，透過 `base_url` 切換
  - 替代方案：多 SDK（openai + anthropic + google-genai）→ 維護成本高，捨棄
- **SQLite 持久化**：使用 aiosqlite，單機部署足夠
  - 替代方案：PostgreSQL → 過重，5-10 人不需要
- **靜態 API Key 認證**：config.json 定義 key-user 對應
  - 替代方案：JWT + bcrypt → 過度設計，移除
- **Skill 載入策略**：啟動時只讀 frontmatter 索引，AI 呼叫時才讀完整內容
  - 理由：減少 system prompt token 消耗
- **Processor 狀態機**：自動循環 tool_use → execute → send back，含 doom loop 偵測（同參數 3 次中斷）

## Risks / Trade-offs
- anthropic SDK 對 Ollama 的相容性取決於 Ollama 版本 → 需 v0.14+
- SQLite 並發寫入限制 → 5-10 人足夠，超過需遷移
- subprocess 沙盒安全性有限 → 足夠研究用途，生產環境需 Docker 隔離

## Architecture

```
FastAPI Server
└── src/              # 所有原始碼
    ├── api/          # HTTP + WebSocket 端點
    ├── session/      # Session CRUD + Processor 狀態機
    ├── tool/         # Tool 基類 + 8 個工具
    ├── storage/      # SQLite 連線管理
    ├── config.py     # 設定載入（全域 + 專案 + env）
    ├── provider.py   # 統一 LLM Provider
    ├── skill.py      # SKILL.md 掃描 + 載入
    └── auth.py       # API Key 認證
```
