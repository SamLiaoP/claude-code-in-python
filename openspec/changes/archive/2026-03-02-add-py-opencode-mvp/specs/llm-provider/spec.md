## ADDED Requirements

### Requirement: Unified LLM Provider
系統 SHALL 提供統一的 LLM Provider，使用 `litellm` 統一呼叫 100+ LLM 服務（Claude / GPT / Gemini / Ollama 等）。

- model 字串使用 provider 前綴格式：`anthropic/claude-...`、`openai/gpt-4o`、`gemini/gemini-2.0-flash`、`ollama/llama3`
- 底層使用 `litellm.acompletion(stream=False)` 進行非串流呼叫
- 不直接引入 `anthropic` / `openai` / `google-genai` SDK（litellm 內部處理）

Provider 類別 MUST 實作 `chat(messages, tools, system) → ChatResult` 介面（非串流，一次回傳完整結果含 text + tool_calls）。`stream_chat()` 保留備用。

#### Scenario: 使用 Ollama 本地模型對話
- **WHEN** config.json 設定 provider 為 `{ "api_base": "http://localhost:11434", "model": "ollama/llama3" }`
- **THEN** 系統透過 litellm 連線至 Ollama 進行對話

#### Scenario: 使用 Claude API 對話
- **WHEN** config.json 設定 provider 為 `{ "api_key_env": "ANTHROPIC_API_KEY", "model": "anthropic/claude-sonnet-4-20250514" }`
- **THEN** 系統透過 litellm 連線至 Claude API 進行對話

#### Scenario: 使用 GPT 模型對話
- **WHEN** config.json 設定 provider 為 `{ "api_key_env": "OPENAI_API_KEY", "model": "openai/gpt-4o" }`
- **THEN** 系統透過 litellm 連線至 OpenAI API 進行對話

#### Scenario: 使用 Gemini 模型對話
- **WHEN** config.json 設定 provider 為 `{ "api_key_env": "GEMINI_API_KEY", "model": "gemini/gemini-2.0-flash" }`
- **THEN** 系統透過 litellm 連線至 Google Gemini API 進行對話

#### Scenario: Session 指定 Provider
- **WHEN** 建立 Session 時指定 `provider: "local"`
- **THEN** 該 Session 的所有 LLM 呼叫 MUST 使用指定的 provider 設定

### Requirement: API Key 環境變數管理
Provider 的 API Key MUST 支援透過環境變數引用（`api_key_env` 欄位），不得寫死在 config 中。

#### Scenario: 環境變數 API Key
- **WHEN** config 設定 `"api_key_env": "ANTHROPIC_API_KEY"`
- **THEN** 系統從環境變數 `ANTHROPIC_API_KEY` 讀取實際 key 值

### Requirement: Config 載入優先級
系統 MUST 按以下順序載入設定（低→高）：程式內建預設 → `~/.py-opencode/config.json` → `<project>/.py-opencode/config.json`（深度合併）→ 環境變數 `PY_OPENCODE_*`。

#### Scenario: 專案級設定覆蓋全域
- **WHEN** 全域 config 設定 `default_provider: "local"` 且專案級 config 設定 `default_provider: "claude"`
- **THEN** 最終使用 `"claude"` 作為預設 provider
