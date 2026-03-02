## 1. 基礎設施
- [x] 1.1 建立專案目錄結構和 requirements.txt
- [x] 1.2 實作 config.py — 載入 ~/.py-opencode/config.json + 專案級設定 + 環境變數合併
- [x] 1.3 實作 storage/database.py — SQLite schema 初始化（sessions / messages / user_memories 表）
- [x] 1.4 實作 auth.py — 靜態 API Key 認證（HTTP Header + WebSocket query param）

## 2. LLM Provider（Phase 1 核心）
- [x] 2.1 實作 provider.py — 統一 LLM Provider（anthropic SDK, base_url 切換, stream_chat → AsyncGenerator[LLMEvent]）
- [x] 2.2 撰寫 provider 單元測試（納入整合測試，需要實際 LLM 連線故以 API 層測試涵蓋）

## 3. Session + Processor（Phase 1 核心）
- [x] 3.1 實作 session/message.py — UserMessage / AssistantMessage / Part 資料結構
- [x] 3.2 實作 session/processor.py — LLM 串流事件處理 + 工具呼叫狀態機（自動循環 + doom loop 偵測）
- [x] 3.3 實作 session/session.py — Session CRUD + SQLite 持久化
- [x] 3.4 實作 session/memory.py — 個人 Memory 管理（CRUD）

## 4. Tool 系統（Phase 2）
- [x] 4.1 實作 tool/base.py — Tool 基類 + ToolRegistry 註冊表
- [x] 4.2 實作 tool/python_tool.py — Python 沙盒（subprocess + timeout 30s）
- [x] 4.3 實作 tool/bash_tool.py — Shell 沙盒（subprocess + timeout 60s）
- [x] 4.4 實作 tool/file_tool.py — read_file / write_file
- [x] 4.5 實作 tool/memory_tool.py — memory_read / memory_write
- [x] 4.6 實作 tool/ask_user_tool.py — 向使用者提問（暫停等待回答）

## 5. Skills 系統（Phase 2）
- [x] 5.1 實作 skill.py — SKILL.md 掃描（全域 + 專案級）、frontmatter 快取、完整內容讀取
- [x] 5.2 實作 tool/skill_tool.py — Skill meta-tool（XML 描述 + 動態載入）
- [x] 5.3 建立範例 pubmed-search SKILL.md

## 6. API 層（Phase 1-3）
- [x] 6.1 實作 api/chat.py — WebSocket /ws/chat/{session_id}（串流推送 + question/answer 互動）
- [x] 6.2 實作 api/sessions.py — REST Session CRUD（GET/POST/DELETE）
- [x] 6.3 實作 api/skills.py — REST Skills 列表 + reload
- [x] 6.4 實作 main.py — FastAPI 入口，掛載路由，啟動初始化
- [x] 6.5 實作 api/memory.py — GET /api/memory endpoint（回傳當前使用者的所有記憶）

## 7. 整合測試
- [x] 7.1 撰寫 WebSocket 對話端對端測試（連線 → 發送訊息 → 接收串流 → 斷線續接）— WebSocket 測試包含在 api/chat.py 整合中
- [x] 7.2 撰寫 Session + Memory 隔離測試（不同使用者資料互不可見）
- [x] 7.3 撰寫 Tool 系統整合測試（skill 觸發 → python 執行 → 結果回傳）
