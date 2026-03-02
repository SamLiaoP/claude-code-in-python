# SNAPSHOT — 變更紀錄

## 2026-03-02：Log 寫入檔案 + 關閉 Streaming 模式

### 背景
手動測試 Skill 時，LLM 載入 skill 後用了錯誤路徑存取 references/，無法判斷送給 AI 的內容是否正確。需要詳細日誌來 debug，但 console 輸出太多干擾。

### 變更內容

**src/main.py**：
- DEBUG log 全部寫入 `logs/app.log` 檔案（不輸出到 console）
- 預設 LOG_LEVEL=DEBUG，可用環境變數調整

**src/provider.py**：
- 新增 `chat()` 非串流方法：一次呼叫，完整回傳 text + tool_calls
- `chat()` 回傳前 log 完整 response（文字 + tool call 名稱及參數）
- 抽出 `_build_kwargs()` 共用參數組裝 + request log
- `stream_chat()` 保留備用

**src/session/processor.py**：
- `process_turn()` 從 `stream_chat` 改用 `chat`（非串流）
- 核心迴圈簡化：不再逐 chunk 拼裝，直接讀 ChatResult

**src/tool/skill_tool.py**、**src/session/processor.py**：
- 各關鍵點加入 debug log（tool 呼叫、skill 載入、system prompt）

**.gitignore**（新增）：排除 logs/、__pycache__/、*.db、.env

### 查看 log
```bash
tail -f logs/app.log
```

---

## 2026-03-02：範例 Skill 示範 references/ 和 scripts/ 用法

### 背景
現有範例 skill（pubmed-search）只有一個 SKILL.md，沒有示範 references/ 和 scripts/ 的用法。Skill 作者不知道怎麼利用漸進式披露的三層結構。

### 變更內容

**examples/skills/pubmed-search/SKILL.md**：
- 改寫為引導式說明，指向 scripts/ 和 references/ 子資料夾
- allowed-tools 加入 `read_file`（讓 LLM 能讀取 references）
- 用相對路徑描述資源位置，搭配 base directory 注入即可運作

**examples/skills/pubmed-search/references/api_guide.md**（新增）：
- PubMed E-utilities API 參考文件：esearch / efetch 的參數說明與回傳格式
- SKILL.md 只放高層指引，詳細 API 規格放這裡

**examples/skills/pubmed-search/scripts/search.py**（新增）：
- 可獨立執行的搜尋腳本，`python search.py "query" --max N`
- LLM 可直接用 bash tool 執行，不需每次重寫搜尋邏輯

---

## 2026-03-02：Skill 載入注入 Base Directory 路徑

### 背景
LLM 載入 Skill 後無法存取 `references/` 和 `scripts/` 子資料夾，因為不知道 SKILL.md 的實際路徑。參考 OpenCode 原始碼做法，在回傳 skill 內容時附上 base directory 絕對路徑。

### 變更內容

**src/skill.py**：
- 新增 `get_skill_info(name)` 函數，回傳 `SkillInfo`（含 path），供 skill_tool 取得路徑

**src/tool/skill_tool.py**：
- `execute()` 回傳格式從 `Skill loaded: {name}` 改為 `## Skill: {name}` + `**Base directory**: {skill_dir}`
- LLM 拿到路徑後即可用 read_file / bash 工具存取 references 和 scripts

---

## 2026-03-02：Skills 功能手動測試準備

### 背景
LiteLLM 遷移完成後，需要手動測試 Skills 功能是否正常運作。

### 變更內容

**~/.py-opencode/config.json**：
- `providers.claude.model` 加上 `anthropic/` 前綴（`claude-sonnet-4-20250514` → `anthropic/claude-sonnet-4-20250514`），LiteLLM 靠前綴判斷 provider。

**tests/manual_test_skills.sh**（新增，已修正）：
- 建立 Session 時帶 `project_dir`，自動初始化 `.py-opencode/skills/` 目錄
- 流程：健康檢查 → 建立帶 project_dir 的 Session → 確認目錄建立 → 引導放入 Skill → 重新掃描 → WebSocket 對話測試
- 支援自訂 project_dir：`bash tests/manual_test_skills.sh /path/to/project`，預設 `/tmp/py-opencode-test-project`

---

## 2026-03-02：程式碼遷移 Anthropic SDK → LiteLLM

### 背景
規格文件已更新為 LiteLLM，此次將程式碼從 `anthropic` SDK 改為 `litellm`，保持 `LLMEvent` 介面不變。

### 變更內容

**requirements.txt**：`anthropic` → `litellm`

**src/config.py**：
- `base_url` → `api_base`（LiteLLM 慣例）
- `model` 預設值 `"llama3"` → `"ollama/llama3"`（帶 provider 前綴）

**src/tool/base.py**：
- `get_schema()` 從 Anthropic 格式改為 OpenAI function calling 格式（`{"type": "function", "function": {...}}`）

**src/session/message.py**：
- `to_api_format()` assistant 訊息改為 OpenAI `tool_calls` 格式
- `build_tool_result_message()` → `build_tool_result_messages()`（複數），回傳 `list[dict]`（每個 tool result 是獨立 `role=tool` 訊息）

**src/provider.py**（核心重寫）：
- `import anthropic` → `import litellm`
- 不再建立 client 物件，改存 model/api_key/api_base
- system prompt 注入為 `{"role": "system"}` 訊息
- 呼叫 `litellm.acompletion(stream=True)` 串流
- 解析 OpenAI 格式 chunk → 轉換為同樣的 LLMEvent
- LLMEvent dataclass 完全不變

**src/session/processor.py**（2 行改動）：
- import `build_tool_result_message` → `build_tool_result_messages`
- `api_messages.append(...)` → `api_messages.extend(...)`

**tests/test_tools.py**：
- 斷言路徑 `schemas[0]["name"]` → `schemas[0]["function"]["name"]`

---

## 2026-03-02：LLM Provider 規格改用 LiteLLM

### 背景
經調查 Claude Agent SDK、OpenAI Agents SDK、LiteLLM 三個方案後，確認 LiteLLM 最適合本專案。Claude Agent SDK 是單用戶 CLI 工具不支援多人 Web 後端；OpenAI Agents SDK 整合成本高；LiteLLM 只替換 provider 層，100+ 模型統一介面。

### 變更內容（僅規格文件，不改程式碼）

**PLAN.md（多處修正）**：
1. **FR-01**：SDK 策略從「只用 anthropic SDK，透過 base_url 切換」改為「使用 litellm 統一呼叫 100+ LLM」；config.json 範例加入 GPT、Gemini provider
2. **§4.4 config.json 規格**：`base_url` 欄位改為 `api_base`（LiteLLM 慣例）；model 字串加 provider 前綴
3. **§十 依賴套件**：`anthropic` 改為 `litellm`
4. **§5.1 架構圖**、**§5.2 目錄結構**、**§十一 Phase 1/4**：所有 anthropic SDK 引用更新為 litellm
5. **§三 非功能需求**：可擴展性描述更新

**openspec llm-provider/spec.md**：
- Requirement 改為使用 litellm 統一呼叫介面
- model 字串格式改為 `anthropic/claude-...`、`ollama/llama3`、`openai/gpt-4o`、`gemini/gemini-2.0-flash`
- 新增 Scenario：使用 GPT 模型對話、使用 Gemini 模型對話
- Ollama scenario 改用 `api_base` + `ollama/llama3` 格式

---

## 2026-03-02：專案目錄初始化 + Skill 按 Session 掃描

### 背景
`project_dir` 只是存進 DB 的字串，建立 session 時不會初始化目錄，WebSocket 連線時也不會掃描專案級 skills。

### 變更內容

**規格文件**：
- `PLAN.md` FR-03 表格加「專案目錄初始化」行；§4.1 目錄結構加「由 POST /api/sessions 時自動建立」註解
- `session-management/spec.md` 新增「建立 Session 時初始化專案目錄」scenario
- `tool-system/spec.md` 新增「對話連線時掃描專案級 Skills」scenario

**程式碼**：
- `src/session/session.py`：新增 `_init_project_dir()`，`create_session()` 帶 project_dir 時自動建立 `.py-opencode/{skills/, context/}` 及空白 PROJECT.md
- `src/api/chat.py`：WebSocket 連線建立 Processor 前呼叫 `scan_skills(project_dir)` 重新掃描 skills
- `src/api/skills.py`：`/reload` endpoint 支援 `project_dir` body 參數

**測試**：
- `tests/test_skill.py`：新增 `test_create_session_inits_project_dir`（驗證目錄建立 + 不覆蓋已存在 PROJECT.md）
- `tests/test_api.py`：新增 `test_create_session_with_project_dir`（驗證 API 帶 project_dir 後目錄存在）

---

## 2026-03-02：專案目錄結構重整

### 背景
根目錄原始碼與文件混在一起，難以分辨。將所有原始碼移入 `src/` 子目錄，根目錄只保留文件和設定檔。

### 變更內容
- 建立 `src/` 目錄，搬入 `main.py`, `config.py`, `auth.py`, `provider.py`, `skill.py` 及 `api/`, `session/`, `tool/`, `storage/` 子目錄
- `test_ws_client.py` 從根目錄搬入 `tests/`
- `tests/conftest.py`：`sys.path` 改指向 `src/` 目錄
- `PLAN.md` §5.2：更新專案目錄結構圖
- 所有 `src/` 內部 import 不需修改（相對位置不變）

### 啟動方式變更
```bash
uvicorn main:app --reload --app-dir src
```

---

## 2026-03-02：實作 py-opencode MVP（Phase 1-3 全部完成）

### 背景
執行 `openspec/changes/add-py-opencode-mvp/` 提案，從零建構完整的 AI Agent 後端服務。

### 新增檔案

**基礎設施**：
- `requirements.txt` — 7 個依賴套件
- `config.py` — 設定載入（全域 + 專案級 + 環境變數合併）
- `storage/database.py` — SQLite schema 初始化（sessions / messages / user_memories）
- `auth.py` — 靜態 API Key 認證

**LLM Provider**：
- `provider.py` — 統一 LLM Provider（anthropic SDK，base_url 切換，stream_chat → AsyncGenerator[LLMEvent]）

**Session 模組**：
- `session/message.py` — Message / TextPart / ToolPart 資料結構 + 序列化
- `session/processor.py` — LLM 串流事件處理 + 工具呼叫狀態機（自動循環 + doom loop 偵測 + ask_user 暫停）
- `session/session.py` — Session CRUD + SQLite 持久化 + 自動 title
- `session/memory.py` — 個人 Memory CRUD

**Tool 系統**：
- `tool/base.py` — Tool 基類 + ToolRegistry
- `tool/python_tool.py` — Python 沙盒（subprocess + timeout）
- `tool/bash_tool.py` — Shell 沙盒
- `tool/file_tool.py` — read_file / write_file
- `tool/memory_tool.py` — memory_read / memory_write
- `tool/ask_user_tool.py` — 向使用者提問

**Skills 系統**：
- `skill.py` — SKILL.md 掃描 + frontmatter 快取 + 完整內容讀取 + XML 描述產生
- `tool/skill_tool.py` — Skill meta-tool（動態 description）
- `examples/skills/pubmed-search/SKILL.md` — 範例 Skill

**API 層**：
- `api/chat.py` — WebSocket /ws/chat/{session_id}（串流推送 + question/answer + abort）
- `api/sessions.py` — REST Session CRUD
- `api/skills.py` — REST Skills 列表 + reload
- `api/memory.py` — REST Memory 查詢
- `main.py` — FastAPI 入口，lifespan 初始化

**測試**：
- `tests/test_config.py` — config 載入測試（4 個）
- `tests/test_session_memory.py` — Session + Memory 隔離測試（6 個）
- `tests/test_tools.py` — Tool 系統測試（8 個）
- `tests/test_skill.py` — Skills 系統測試（3 個）
- `tests/test_api.py` — REST API 測試（5 個）

共 26 個測試全部通過。

## 2026-03-01：PLAN.md 與 OpenSpec 提案一致性修正

### 背景
審查 `openspec/changes/add-py-opencode-mvp/` 提案與 `PLAN.md`（需求書 v1.1）的一致性，發現 PLAN.md 有 4 處未跟上設計決策更新。

### 修改內容

**PLAN.md（4 處修正）**：
1. **§十 依賴套件**：移除 `openai`、`google-genai`、`python-jose[cryptography]`、`passlib[bcrypt]`，套件數從 11 改為 7
2. **§十一 Phase 1 交付物**：將 `provider/base.py`、`provider/openai_provider.py`、`provider/anthropic_provider.py` 三項合併為 `provider.py`（單一檔案，anthropic SDK）
3. **§十一 Phase 3 交付物**：`auth/auth.py — JWT 認證` 改為 `auth.py — 靜態 API Key 認證`
4. **§4.1 目錄結構**：移除 `memory/` 子目錄（user1.json、user2.json），memory 統一由 SQLite 管理

**tasks.md（1 項補漏）**：
- 新增 `6.5 實作 api/memory.py — GET /api/memory endpoint`，對應 api-layer spec 中定義但 tasks 未列的 Memory REST API
