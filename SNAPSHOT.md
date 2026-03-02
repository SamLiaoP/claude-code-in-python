# SNAPSHOT — 變更紀錄

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
