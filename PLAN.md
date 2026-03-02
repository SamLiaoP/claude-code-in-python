# py-opencode — 需求書與技術規格

> 版本：v1.1 | 日期：2026-03-01

---

## 一、產品概述

### 1.1 產品定位

**py-opencode** 是一個研究導向的 AI Agent 後端服務，參考 OpenCode / Claude Code 的架構設計，以 Python (FastAPI) 實作。提供多人共用的對話式 AI 研究助理，支援文獻檢索、資料分析、知識問答等場景。

### 1.2 目標用戶

- 5-10 人的研究團隊
- 非軟體開發人員，主要做研究工作
- 需要 AI 協助文獻檢索、資料分析、知識整理

### 1.3 核心價值

- **Skills 擴展**：透過 SKILL.md 檔案注入 domain knowledge（如 PubMed 爬蟲），無需寫程式碼
- **多模型支援**：使用 `litellm` 統一呼叫 100+ LLM（Claude / GPT / Gemini / Ollama 等），單一介面切換
- **多人協作**：每人獨立 Session 和 Memory，可中斷對話後續接
- **沙盒執行**：安全執行 Python 分析腳本
- **微服務架構**：純後端 API，方便前端獨立開發

---

## 二、功能需求（Functional Requirements）

### FR-01：統一 LLM Provider（LiteLLM）

| 項目 | 規格 |
|------|------|
| 描述 | 使用 `litellm` 統一呼叫 100+ LLM 服務（Claude / GPT / Gemini / Ollama 等），provider 前綴格式切換模型 |
| SDK 策略 | **只用 `litellm`**，不直接引入 `anthropic` / `openai` / `google-genai`（litellm 內部處理） |
| 切換方式 | model 字串加 provider 前綴：`anthropic/claude-...`、`openai/gpt-4o`、`gemini/gemini-2.0-flash`、`ollama/llama3` |
| 統一介面 | 單一 LLMProvider 類別，實作 `stream_chat(messages, tools, system)` → `AsyncGenerator[LLMEvent]`，底層使用 `litellm.acompletion(stream=True)` |
| Session 指定 | 每個 Session 建立時可指定使用哪個 Provider |
| API Key 管理 | 透過環境變數引用（`api_key_env` 欄位），不寫死在 config |

**config.json 範例**：
```json
{
  "providers": {
    "local":  { "api_base": "http://localhost:11434", "model": "ollama/llama3" },
    "claude": { "api_key_env": "ANTHROPIC_API_KEY", "model": "anthropic/claude-sonnet-4-20250514" },
    "gpt":    { "api_key_env": "OPENAI_API_KEY", "model": "openai/gpt-4o" },
    "gemini": { "api_key_env": "GEMINI_API_KEY", "model": "gemini/gemini-2.0-flash" }
  },
  "default_provider": "local"
}
```

### FR-02：Skills 系統

| 項目 | 規格 |
|------|------|
| 描述 | 相容 OpenCode SKILL.md 格式，可手動新增 Markdown 檔案擴展 domain knowledge |
| 檔案格式 | YAML frontmatter（name, description, allowed-tools）+ Markdown 指令內容 |
| 掃描路徑 | `~/.py-opencode/skills/**/SKILL.md`（全域）→ `<project>/.py-opencode/skills/**/SKILL.md`（專案級，同名覆蓋） |
| 載入策略 | 啟動時只讀 frontmatter 建索引（~100 tokens），AI 呼叫時才讀完整內容 |
| 暴露方式 | 透過 `skill` meta-tool，在 tool description 中用 XML 列出所有 skill 名稱和描述 |
| 觸發方式 | AI 根據 description 自動判斷是否載入（無 embedding / 無分類器） |

**SKILL.md 範例**：
```markdown
---
name: pubmed-search
description: 當需要搜尋 PubMed 醫學文獻、查詢臨床試驗時使用
allowed-tools: "bash,python"
---

## 使用時機
- 搜尋醫學論文、查詢臨床試驗資料
- 查找特定疾病或藥物相關文獻

## 步驟
1. 用 python tool 呼叫 PubMed E-utilities API
2. 解析 XML 回應，提取 PMID、標題、摘要
3. 整理成結構化摘要回報給使用者

## API 參考
- Base URL: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
- esearch.fcgi: 搜尋取得 PMID 列表
- efetch.fcgi: 取得完整文獻資料
```

### FR-03：Session 管理（可中斷續接）

| 項目 | 規格 |
|------|------|
| 描述 | 每個使用者可建立多個對話 Session，中斷後隨時續接 |
| 持久化 | SQLite 存儲（sessions 表 + messages 表） |
| 使用者綁定 | 每個 session 綁定 user_id，只有本人可存取 |
| 續接機制 | 重新連線 WebSocket 時載入歷史訊息，送給 LLM 維持上下文 |
| CRUD | 建立 / 列出 / 續接 / 刪除 |
| 專案目錄初始化 | 建立 Session 時若指定 project_dir，自動建立 .py-opencode/{skills/, context/} 並初始化 PROJECT.md |

### FR-04：個人 Memory（跨 Session 記憶）

| 項目 | 規格 |
|------|------|
| 描述 | 每人一個跨 session 的記憶空間，AI 可主動讀寫 |
| 存取方式 | LLM 透過 `memory_read` / `memory_write` tool 操作 |
| 存放內容 | 使用者偏好、研究脈絡、常用關鍵字、重要發現摘要 |
| 存儲 | SQLite `user_memories` 表（user_id, key, value, updated_at） |

### FR-05：沙盒執行

| 項目 | 規格 |
|------|------|
| 描述 | 安全執行 AI 產生的 Python / Shell 程式碼 |
| 執行方式 | `subprocess` + `asyncio.wait_for` timeout |
| 超時限制 | Python 30s / Shell 60s（可在 config 調整） |
| 輸出限制 | stdout 截斷至 10,000 字元 |
| 圖片支援 | matplotlib 輸出存檔，回傳檔案路徑 |

### FR-06：認證系統（簡單 API Key）

| 項目 | 規格 |
|------|------|
| 描述 | 簡單 API Key 認證，支援 5-10 人 |
| 使用者定義 | 在 config.json 的 `api_keys` 物件中定義 `{ "key-xxx": "user1", "key-yyy": "user2" }` |
| HTTP 驗證 | 請求帶 `Authorization: Bearer <api-key>` header |
| WebSocket 驗證 | 連線時帶 `?token=<api-key>` query parameter |
| ~~JWT~~ | **已移除**，不再需要 `python-jose` 和 `passlib` 依賴 |

### FR-07：專案上下文注入（PROJECT.md）

| 項目 | 規格 |
|------|------|
| 描述 | 類似 Claude Code 的 CLAUDE.md，自動注入 system prompt |
| 位置 | `<project>/.py-opencode/context/PROJECT.md` |
| 載入時機 | 建立 Session 時讀取，注入 system prompt |
| 用途 | 描述研究專案背景、常用資料庫、注意事項 |

### FR-08：ask_user Tool（向使用者提問）

| 項目 | 規格 |
|------|------|
| 描述 | AI 可透過此 tool 向使用者發送結構化問題（含選項），等待回答後繼續執行 |
| 暫停機制 | Processor 收到 `tool_use(ask_user)` 時暫停 LLM 循環，等使用者回應後才繼續 |
| 參數 | `question: str`（問題文字）、`options: list[str]`（可選，選項列表） |
| WebSocket 事件 | Server → Client: `{ "type": "question", "tool_id": "uuid", "question": "...", "options": [...] }` |
| 使用者回應 | Client → Server: `{ "type": "answer", "tool_id": "uuid", "selected": [...] }` |
| 回傳值 | 使用者的回答文字，作為 tool result 送回 LLM 繼續生成 |

---

## 三、非功能需求（Non-Functional Requirements）

| 項目 | 規格 |
|------|------|
| 效能 | 支援 5-10 人同時使用，單機部署 |
| 延遲 | 首 token 回應 < 2s（取決於模型） |
| 可用性 | 單機運行，無需叢集 |
| 安全性 | API Key 認證、沙盒 timeout 限制、LLM API key 環境變數 |
| 可擴展性 | 新增 Provider 只需在 config.json 加一筆設定（LiteLLM 統一介面） |
| 可維護性 | 每個檔案開頭 spec 註解、詳細行內註解 |

---

## 四、`.py-opencode/` 設定目錄規格

### 4.1 目錄結構

```
~/.py-opencode/                              # 全域設定（使用者家目錄）
├── config.json                              # 全域設定
├── skills/                                  # 全域 Skills
│   ├── pubmed-search/
│   │   └── SKILL.md
│   ├── data-analysis/
│   │   └── SKILL.md
│   └── [skill-name]/
│       ├── SKILL.md                         # 必要：主檔案
│       ├── scripts/                         # 可選：可執行腳本
│       │   └── search.py
│       └── references/                      # 可選：參考文件
│           └── api_guide.md

<project>/.py-opencode/                      # 專案級設定（由 POST /api/sessions 時自動建立）
├── config.json                              # 專案級設定覆蓋
├── skills/                                  # 專案級 Skills（覆蓋全域同名）
│   └── domain-specific/
│       └── SKILL.md
└── context/
    └── PROJECT.md                           # 專案上下文（自動注入 system prompt）
```

### 4.2 設定載入優先級（低→高）

```
1. 程式內建預設值
2. ~/.py-opencode/config.json          （全域）
3. <project>/.py-opencode/config.json  （專案級，深度合併覆蓋全域）
4. 環境變數 PY_OPENCODE_*              （最高優先）
```

### 4.3 Skill 掃描順序（低→高，同名後者覆蓋）

```
1. ~/.py-opencode/skills/**/SKILL.md          （全域 skills）
2. <project>/.py-opencode/skills/**/SKILL.md  （專案級 skills）
```

### 4.4 完整 config.json 規格

```json
{
  "providers": {
    "<provider-name>": {
      "api_base": "(可選) API endpoint URL，如 Ollama 的 http://localhost:11434",
      "api_key": "(可選) 直接填 API key",
      "api_key_env": "(可選) 環境變數名稱（優先於 api_key）",
      "model": "provider前綴/模型ID，如 anthropic/claude-sonnet-4-20250514、ollama/llama3、openai/gpt-4o"
    }
  },
  "default_provider": "<provider-name>",
  "api_keys": {
    "key-abc123": "researcher1",
    "key-def456": "researcher2"
  },
  "sandbox": {
    "timeout": 30,
    "max_output": 10000
  }
}
```

> **已移除**：`permission` 區塊（延後實作）、`users` 陣列（改用 `api_keys`）、`type` 欄位（LiteLLM 透過 model 前綴自動辨識 provider）
> **欄位更名**：`base_url` → `api_base`（LiteLLM 慣例）

---

## 五、系統架構

### 5.1 整體架構

```
前端（任意框架）
    ↕ HTTP REST + WebSocket
┌─────────────────────────────────────────────┐
│  FastAPI Server（main.py）                    │
│  ├── api/chat.py         WebSocket 對話串流    │
│  ├── api/sessions.py     Session REST CRUD    │
│  └── api/skills.py       Skill 列表 + reload  │
└──────────┬──────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────┐
│  Session Layer                                │
│  ├── session.py      Session CRUD + 持久化     │
│  ├── message.py      訊息資料結構               │
│  ├── memory.py       個人記憶管理               │
│  └── processor.py    LLM 串流 + 工具呼叫循環    │
└──────────┬──────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────┐
│  Tool + Skill + Provider                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ Tools    │ │ Skills   │ │ Provider     │ │
│  │ 8 個工具  │ │ SKILL.md │ │ litellm      │ │
│  └──────────┘ └──────────┘ │ (單一類別)    │ │
│                             └──────────────┘ │
└──────────┬──────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────┐
│  Storage: SQLite（aiosqlite）                  │
│  ├── sessions 表                              │
│  ├── messages 表                              │
│  └── user_memories 表                         │
└─────────────────────────────────────────────┘
```

### 5.2 專案目錄結構

```
py-opencode/
├── CLAUDE.md, AGENTS.md, PLAN.md, SNAPSHOT.md   # 文件
├── requirements.txt                              # 設定
├── openspec/                                     # 規格提案
├── examples/                                     # 範例 Skills
├── tests/                                        # 測試
│
└── src/                                          # 所有原始碼
    ├── main.py              # FastAPI 入口，掛載路由，啟動初始化
    ├── config.py            # 設定載入（合併全域 + 專案 + env）
    ├── provider.py          # LLM Provider（單一檔案，統一 litellm 呼叫介面）
    ├── skill.py             # SKILL.md 掃描、frontmatter 快取、完整內容讀取
    ├── auth.py              # 簡單 API Key 認證
    │
    ├── tool/
    │   ├── base.py          # Tool 基類 + ToolRegistry 註冊表
    │   ├── skill_tool.py    # Skill meta-tool（XML 描述 + 動態載入）
    │   ├── bash_tool.py     # Shell 執行（subprocess + timeout）
    │   ├── python_tool.py   # Python 沙盒執行（subprocess + timeout）
    │   ├── file_tool.py     # read_file / write_file
    │   ├── memory_tool.py   # memory_read / memory_write
    │   └── ask_user_tool.py # 向使用者提問（暫停等待回答）
    │
    ├── session/
    │   ├── session.py       # Session CRUD + SQLite 持久化
    │   ├── message.py       # UserMessage / AssistantMessage / Part 資料結構
    │   ├── memory.py        # 個人 Memory 管理（CRUD）
    │   └── processor.py     # LLM 串流事件處理 + 工具呼叫狀態機
    │
    ├── api/
    │   ├── chat.py          # WebSocket /ws/chat/{session_id}
    │   ├── sessions.py      # REST: GET/POST/DELETE /api/sessions
    │   └── skills.py        # REST: GET /api/skills, POST /api/skills/reload
    │
    └── storage/
        └── database.py      # SQLite schema 初始化 + 連線管理
```

> **已移除**：`provider/` 多檔案目錄（合併為單一 `provider.py`，使用 litellm）、`auth/` 目錄（簡化為 `auth.py`）、`skill/` 目錄（簡化為 `skill.py`）、`web_search_tool.py`（延後）、`sandbox.py` API（功能已含在 tool 中）
> **新增**：`ask_user_tool.py`

---

## 六、API 規格

### 6.1 REST API

#### 認證

> **已簡化**：移除 JWT login endpoint，改用靜態 API Key 認證。
> 所有 REST 請求帶 `Authorization: Bearer <api-key>` header。

#### Session 管理

```
GET /api/sessions
Headers: Authorization: Bearer <api-key>
Response: [
  { "id": "uuid", "title": "自動生成", "provider": "local", "created_at": "iso8601", "updated_at": "iso8601" }
]

POST /api/sessions
Headers: Authorization: Bearer <api-key>
Request:  { "provider": "local", "project_dir": "/path/to/project" }  // provider 可選，預設 default_provider
Response: { "id": "uuid", "provider": "local", "created_at": "iso8601" }

DELETE /api/sessions/{id}
Headers: Authorization: Bearer <api-key>
Response: { "ok": true }
```

#### Skills

```
GET /api/skills
Headers: Authorization: Bearer <api-key>
Response: [
  { "name": "pubmed-search", "description": "...", "source": "global" }
]

POST /api/skills/reload
Headers: Authorization: Bearer <api-key>
Response: { "count": 5 }
```

#### Memory

```
GET /api/memory
Headers: Authorization: Bearer <api-key>
Response: [ { "key": "research_focus", "value": "心血管藥物", "updated_at": "iso8601" } ]
```

> **已移除**：`POST /api/sandbox/run`（沙盒執行功能已包含在 tool 系統中）

### 6.2 WebSocket API

```
WS /ws/chat/{session_id}?token=<api-key>
```

**客戶端 → 伺服器**：
```json
{ "type": "message", "content": "幫我搜尋 PubMed 關於 statins 的最新研究" }
{ "type": "answer",  "tool_id": "uuid", "selected": ["選項A"] }
{ "type": "abort" }
```

**伺服器 → 客戶端**：
```json
{ "type": "text_delta",  "text": "我來幫你搜尋..." }
{ "type": "tool_start",  "tool_id": "uuid", "name": "skill",  "input": {"name": "pubmed-search"} }
{ "type": "tool_result", "tool_id": "uuid", "output": "Skill loaded: pubmed-search" }
{ "type": "tool_start",  "tool_id": "uuid", "name": "python", "input": {"code": "import requests..."} }
{ "type": "tool_result", "tool_id": "uuid", "output": "Found 15 articles..." }
{ "type": "question",    "tool_id": "uuid", "question": "要深入哪篇文獻？", "options": ["文獻A", "文獻B"] }
{ "type": "text_delta",  "text": "根據搜尋結果，以下是..." }
{ "type": "done" }
{ "type": "error",       "message": "Provider connection failed" }
```

> **新增事件**：`question`（Server → Client，ask_user tool 觸發）和 `answer`（Client → Server，使用者回應）

---

## 七、Tool 規格

### 7.1 Tool 介面定義

```python
class ToolResult:
    output: str           # 主要輸出（給 LLM 看）
    metadata: dict        # 結構化元資料（給前端用）
    error: str | None     # 錯誤訊息

class ToolContext:
    session_id: str
    user_id: str
    messages: list        # 對話歷史
    abort: asyncio.Event  # 中斷信號
```

### 7.2 工具清單

| Tool ID | 描述 | 參數 |
|---------|------|------|
| `skill` | Meta-tool，載入 domain knowledge。tool description 動態聚合所有 SKILL.md 的 name + description | `name: str` |
| `python` | 沙盒執行 Python 程式碼 | `code: str` |
| `bash` | 沙盒執行 Shell 命令 | `command: str, cwd: str(optional)` |
| `read_file` | 讀取檔案內容 | `path: str, offset: int(opt), limit: int(opt)` |
| `write_file` | 寫入檔案 | `path: str, content: str` |
| `memory_read` | 讀取當前使用者的記憶 | `key: str(optional)` — 不給 key 則列出全部 |
| `memory_write` | 寫入當前使用者的記憶 | `key: str, value: str` |
| `web_search` | 搜尋網路（可選，後續擴充） | `query: str` |

### 7.3 Skill Meta-Tool 運作流程

```
1. 啟動時：掃描所有 SKILL.md，只讀 frontmatter（name + description）
2. 初始化 skill tool 時：將所有 skill 的 name + description 組裝成 XML，
   放入 skill tool 的 description 欄位
3. LLM 看到 skill tool description 中的列表，
   根據使用者問題自行決定是否呼叫 skill(name="pubmed-search")
4. 執行時：讀取完整 SKILL.md 內容，回傳給 LLM 作為上下文
5. LLM 根據 SKILL.md 中的指令繼續執行（例如呼叫 python tool 跑爬蟲）
```

---

## 八、Processor 狀態機規格

### 8.1 LLM 串流事件處理

```
接收 LLM 串流回應
  ↓
事件分類處理：
  text_delta     → 累積文字，透過 WebSocket 即時推送
  tool_use_start → 建立 ToolPart（status: pending）
  tool_use_input → 累積工具參數 JSON
  tool_use_done  → 設為 running → 執行工具 → 設為 completed/error
                   → 將工具結果送回 LLM 繼續生成
  message_stop   → 結束本輪

特殊機制：
  - 自動循環：如果 LLM 回應包含 tool_use，執行完工具後自動送回 LLM 繼續
  - Doom Loop 偵測：同一工具用相同參數呼叫 3 次 → 中斷並回報錯誤
  - 輸出截斷：工具輸出超過 max_output → 截斷並附註 "[截斷]"
```

### 8.2 System Prompt 組裝

```
system_prompt = concat(
  PROJECT.md 內容（如果存在）,
  內建基礎指令（角色定義、回答格式）,
  使用者記憶摘要（最近 N 筆）
)
```

---

## 九、資料庫 Schema

```sql
-- Session 表
CREATE TABLE sessions (
    id          TEXT PRIMARY KEY,     -- UUID
    user_id     TEXT NOT NULL,
    provider    TEXT NOT NULL,        -- provider name from config
    title       TEXT,                 -- 自動從第一則訊息生成
    project_dir TEXT,                 -- 專案目錄路徑（可選）
    created_at  TEXT NOT NULL,        -- ISO 8601
    updated_at  TEXT NOT NULL
);

-- Message 表
CREATE TABLE messages (
    id          TEXT PRIMARY KEY,     -- UUID
    session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,        -- 'user' | 'assistant'
    content     TEXT NOT NULL,        -- JSON: 純文字或 Part 陣列
    created_at  TEXT NOT NULL
);

-- 個人記憶表
CREATE TABLE user_memories (
    user_id     TEXT NOT NULL,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (user_id, key)
);
```

---

## 十、依賴套件

```
fastapi                        # Web 框架
uvicorn[standard]              # ASGI Server（含 WebSocket）
litellm                        # 統一 LLM 呼叫介面（100+ 模型，含 Claude/GPT/Gemini/Ollama）
python-frontmatter             # 解析 SKILL.md YAML frontmatter
pydantic                       # 資料驗證
pydantic-settings              # 設定管理
aiosqlite                      # 非同步 SQLite
```

共 7 個套件。**不引入** langchain / llamaindex 等重框架。

> **變更**：`anthropic` → `litellm`（統一呼叫介面，不再需要直接引入各家 SDK）
> **已移除**：`openai`、`google-genai`、`python-jose[cryptography]`、`passlib[bcrypt]`

---

## 十一、實作分期

### Phase 1 — 能對話（核心串流）

**目標**：透過 WebSocket 和任意 config 設定的 LLM 對話

**交付物**：
1. `config.py` — 載入 `~/.py-opencode/config.json` + 環境變數
2. `provider.py` — 統一 LLM Provider（單一檔案，litellm 統一呼叫介面）
3. `session/message.py` — 訊息資料結構
4. `session/processor.py` — 串流 + 工具呼叫循環
5. `api/chat.py` — WebSocket 端點
6. `main.py` — FastAPI 啟動

**驗收標準**：
- 設定 config.json 指向 Ollama，用 WebSocket 客戶端能正常對話
- 切換 provider 到 Claude，同樣能正常對話
- 串流回應即時推送

### Phase 2 — `.py-opencode/` + Skill + Tool

**目標**：AI 能自動偵測並載入 Skill，執行 Python/Shell 程式碼

**交付物**：
1. `.py-opencode/` 目錄結構初始化邏輯
2. `skill/skill.py` — SKILL.md 掃描（走 `.py-opencode/skills/`）
3. `tool/base.py` — Tool 基類 + ToolRegistry
4. `tool/skill_tool.py` — Skill meta-tool
5. `tool/python_tool.py` — Python 沙盒
6. `tool/bash_tool.py` — Shell 沙盒
7. `tool/file_tool.py` — 檔案讀寫
8. 範例：`pubmed-search` SKILL.md

**驗收標準**：
- 在 `~/.py-opencode/skills/pubmed-search/SKILL.md` 放入 PubMed skill
- 詢問「幫我搜尋 PubMed 關於 statins 的文獻」，AI 自動觸發 skill 並執行 Python 爬蟲
- GET /api/skills 能列出所有可用 skills

### Phase 3 — 多人 + 持久化

**目標**：多人登入，對話可中斷續接，記憶跨 session 保留

**交付物**：
1. `storage/database.py` — SQLite schema 初始化
2. `session/session.py` — Session CRUD
3. `session/memory.py` — 個人記憶管理
4. `tool/memory_tool.py` — 記憶讀寫 tool
5. `auth.py` — 靜態 API Key 認證
6. `api/sessions.py` — Session REST API

**驗收標準**：
- 兩個不同帳號登入，各自的 session 和 memory 完全隔離
- 中斷對話 → 重新連線 → 歷史訊息正確載入 → AI 有上下文
- AI 主動寫入 memory → 新 session 中 AI 能讀取先前記憶

### Phase 4 — 穩定化

**交付物**（依需求）：
- PROJECT.md 自動注入 system prompt
- Doom loop 偵測（同一工具同參數 3 次）
- 訊息過長時自動摘要壓縮
- 結構化日誌系統
- ~~`provider/gemini_provider.py`~~（已不需要，litellm 原生支援 Gemini）

---

## 十二、參考架構來源

| 來源 | 參考內容 |
|------|---------|
| OpenCode (`/opencode/`) | Skill 系統、Tool 定義模式、Processor 狀態機、Config 目錄結構 |
| ClaudeCodeUI (`/claudecodeui/`) | Skill meta-tool 設計、兩條訊息注入、contextModifier |
| 架構文件 (`OPENCODE_ARCHITECTURE.md`) | 完整系統拆解、Python 對應庫對照 |