# SNAPSHOT — 變更紀錄

## 2026-03-03：Session Log 補完 — 記錄完整 LLM 請求/回應

讓 session log 包含 provider 層的完整 LLM 請求和回應，方便 debug。

**修改檔案**：
- `src/provider.py`：`LLMProvider.__init__()` 新增 `logger` 可選參數，所有 debug log 改用 `self.logger`；移除 message content 500 字截斷和 tool arguments 300 字截斷，改為完整記錄
- `src/session/processor.py`：`__init__` 中將 session logger 注入 `self.provider.logger`；移除 `process_turn()` 的 system prompt 截斷摘要（provider 層已完整記錄）

---

## 2026-03-03：三項功能改進 — Session 日誌分離 + Streaming 切換 + 側欄收合

### 1. Logs 按 Session 區分
- 新增 `src/log_utils.py`：`get_session_logger(session_id)` 回傳寫入 `logs/sessions/<session_id>.log` 的 logger
- `src/session/processor.py`：改用 session 專屬 logger（`self.logger`），所有 LLM/Tool 日誌寫入 session 專屬檔案
- `src/api/chat.py`：WebSocket 連線/斷線事件寫入 session logger
- 全域 `logs/app.log` 保留，記錄啟動/路由等非 session 事件

### 2. Streaming / 非 Streaming 模式切換
- `src/session/processor.py`：`process_turn()` 新增 `stream: bool` 參數
  - `stream=False`（預設）：呼叫 `provider.chat()`，完成後一次推送
  - `stream=True`：呼叫 `provider.stream_chat()`，逐 chunk 推送 `text_delta`
- `src/api/chat.py`：從 WebSocket message 解析 `stream` 欄位傳給 processor
- `src/static/index.html`：Model section 下方加 Streaming checkbox
- `src/static/app.js`：發送訊息時帶 `stream: true/false`

### Bug 修正：Skills 切換 Session 時未即時更新
- `src/api/skills.py`：`GET /api/skills` 新增 `session_id` query param，有帶時先根據 session 的 `project_dir` 重新掃描再回傳
- `src/static/app.js`：`loadSkills()` 帶上 `currentSessionId`

### 3. 右側欄可伸縮顯示
- `src/static/index.html`：Skills/Model/Files 的 `<h3>` 改成可點擊 toggle header（含 ▶/▼ 箭頭）
- `src/static/style.css`：`.section-collapsed .section-content { display: none }` 收合樣式
- `src/static/app.js`：`toggleSection()` 函數切換 `.section-collapsed` class
- Skills 預設收合，Model 和 Files 預設展開

---

## 2026-03-03：封存已完成的 OpenSpec Changes

將 3 個已完成的變更提案封存至 `openspec/changes/archive/`：
- `update-skill-tool-align` → `2026-03-03-update-skill-tool-align`
- `update-memory-session-scoped` → `2026-03-03-update-memory-session-scoped`
- `update-session-default-workdir` → `2026-03-03-update-session-default-workdir`

剩餘進行中：`add-frontend-demo-ui`（0/10 tasks）

---

## 2026-03-03：前端功能增強 — 開啟資料夾、Model 切換、移除 API Key

**新功能**：
- 目錄瀏覽加「在 Finder 中開啟」按鈕（`POST /api/files/open`，支援 macOS/Windows/Linux）
- Claude Model 切換（`GET /api/models` 回傳 6 個 Claude 模型 + `PATCH /api/sessions/{id}` 支援 model 欄位）
  - Opus 4.6, Sonnet 4.6, Haiku 4.5, Sonnet 4.5, Opus 4.5, Sonnet 4
- sessions 表新增 `model` 欄位（自動 ALTER TABLE migration）
- chat.py 連線時若 session 有指定 model，覆蓋 provider 預設 model
- 移除頂部 API Key 輸入欄（後端已支援無 token 預設使用者）

**修改檔案**：
- `src/storage/database.py`：新增 `_migrate_add_model_column` migration
- `src/session/session.py`：create/get/list 加 model 欄位、新增 `update_session_model()`
- `src/api/sessions.py`：新增 `models_router`（GET /api/models）、PATCH 支援 model
- `src/api/chat.py`：session model 覆蓋 provider 預設 model
- `src/api/files.py`：新增 `POST /api/files/open`
- `src/main.py`：掛載 models_router
- `src/static/`：移除 API Key、加 model 下拉選單、加開啟資料夾按鈕

---

## 2026-03-03：新增前端展示介面 + Provider 切換

新增純 HTML + Vanilla JS + CSS 前端，由 FastAPI StaticFiles 直接提供。零建構步驟。

**後端新增/修改**：
- `src/api/files.py`：新增 GET /api/files 目錄瀏覽 API，含路徑遍歷防護
- `src/api/sessions.py`：新增 GET /api/providers（列出可用 LLM）、PATCH /api/sessions/{id}（切換 Provider）
- `src/session/session.py`：新增 `update_session_provider()` 更新 DB provider 欄位
- `src/main.py`：掛載 files router、providers router、StaticFiles（html=True）

**前端**：
- `src/static/index.html`：三欄佈局（Session 列表 / 聊天區 / Provider+Skills+目錄）
- `src/static/style.css`：暗色主題 UI
- `src/static/app.js`：Session 管理、WebSocket 串流聊天（text_delta/tool_start/tool_result/question/done/error）、Provider 切換、Skills 顯示、目錄瀏覽（懶載入展開）、Markdown 渲染（marked.js CDN）、ask_user 互動卡片

**測試**：
- `tests/test_files_api.py`：6 個測試（列出檔案、路徑遍歷防護、無效 Session、providers API、PATCH provider、無效 provider），全部通過

**OpenSpec proposal**：`openspec/changes/add-frontend-demo-ui/`

---

## 2026-03-03：記憶體綁定 Session（不再跨 Session 共享）

**BREAKING CHANGE**：`user_memories` 表主鍵從 `(user_id, key)` 改為 `(session_id, key)`，舊資料無法遷移。

- `src/storage/database.py`：Schema 改用 `session_id` + FK 到 sessions + CASCADE 刪除；新增 migration 偵測舊表自動 DROP 重建
- `src/session/memory.py`：所有 CRUD 函數 `user_id` → `session_id`
- `src/tool/memory_tool.py`：改用 `ctx.session_id`，description 移除「跨 Session」
- `src/session/processor.py`：`build_system_prompt()` 改用 `memory_read(self.session_id)`
- `src/api/memory.py`：新增 `session_id` 必填 query param
- 測試：新增 `test_memory_session_isolation`、`test_memory_cascade_on_session_delete`；修復 `test_memory_api`、`test_memory_tools`
- OpenSpec proposal: `update-memory-session-scoped`

---

## 2026-03-03：Skill Tool 行為對齊 OpenCode

- `src/skill.py`：`get_skill_content()` 改用 `frontmatter.load()` 解析，回傳 `post.content`（去除 YAML frontmatter）
- `src/tool/skill_tool.py`：找不到 skill 時錯誤訊息列出所有可用技能名稱
- `tests/test_skill.py`：新增 frontmatter 移除斷言，4 個測試全部通過
- OpenSpec proposal: `update-skill-tool-align`

---

## 2026-03-03：Session 建立時預設自動建立工作目錄

- `src/session/session.py`：`create_session` 新增 `skip_workdir` 參數；無 `project_dir` 時自動生成 `~/.py-opencode/projects/<session_id>/` 並初始化目錄結構
- `src/api/sessions.py`：`CreateSessionRequest` 新增 `skip_workdir: bool = False`，傳遞給 `create_session`
- `tests/test_api.py`：新增 `test_create_session_default_workdir`、`test_create_session_skip_workdir` 兩個測試
- 8 個測試全部通過

---

## 2026-03-02：OpenSpec 封存 + spec 同步更新

將 `add-py-opencode-mvp` 提案封存至 `changes/archive/`，同時修正 spec 與程式碼的不一致：
- `design.md`、`llm-provider/spec.md`：anthropic SDK → litellm
- `llm-provider/spec.md`、`tool-system/spec.md`：串流 `stream_chat()` → 非串流 `chat()`
- `project.md`：從空白範本填入實際專案資訊
- 20 個 requirements 寫入 `openspec/specs/`，5 個 capability 全部驗證通過

---

## 2026-03-02：Anthropic SDK → LiteLLM + 非串流模式

**架構決策**：經評估 Claude Agent SDK、OpenAI Agents SDK、LiteLLM 後，選擇 LiteLLM 統一呼叫 100+ LLM。model 字串帶 provider 前綴（`anthropic/claude-...`、`openai/gpt-4o`、`ollama/llama3`）。

**程式碼變更**：
- `requirements.txt`：`anthropic` → `litellm`
- `src/provider.py`：重寫為 litellm 呼叫；新增非串流 `chat() → ChatResult`，`stream_chat()` 保留備用
- `src/session/processor.py`：`process_turn()` 改用 `chat()`，核心迴圈簡化
- `src/tool/base.py`、`src/session/message.py`：Anthropic 格式 → OpenAI function calling 格式
- `src/config.py`：`base_url` → `api_base`，model 預設值加 provider 前綴

**日誌**：DEBUG log 寫入 `logs/app.log`（`tail -f logs/app.log`）

---

## 2026-03-02：Skills 系統增強

- `src/skill.py`：新增 `get_skill_info()` 回傳 SkillInfo（含 path）
- `src/tool/skill_tool.py`：回傳 base directory 絕對路徑，LLM 可存取 references/ 和 scripts/
- `examples/skills/pubmed-search/`：新增 `references/api_guide.md` + `scripts/search.py` 示範三層結構
- `src/session/session.py`：建立 Session 時自動初始化 `.py-opencode/{skills/, context/}` 目錄
- `src/api/chat.py`：WebSocket 連線時重新掃描專案級 skills

---

## 2026-03-02：實作 py-opencode MVP（Phase 1-3）

從零建構 AI Agent 後端服務，26 個測試全部通過。

**核心模組**：
- `src/provider.py` — 統一 LLM Provider（litellm）
- `src/session/processor.py` — Processor 狀態機（tool 自動循環 + doom loop 偵測 + ask_user 暫停）
- `src/session/session.py` — Session CRUD + SQLite 持久化
- `src/session/memory.py` — 個人 Memory CRUD
- `src/tool/` — Tool 基類 + 6 個工具（python, bash, read_file, write_file, memory, ask_user, skill）
- `src/skill.py` — SKILL.md 掃描 + frontmatter 快取
- `src/api/` — FastAPI 端點（WebSocket chat + REST sessions/skills/memory）
- `src/config.py` — 設定載入（全域 + 專案級 + env）
- `src/auth.py` — 靜態 API Key 認證

**專案結構**：所有原始碼在 `src/`，啟動方式 `uvicorn main:app --reload --app-dir src`
