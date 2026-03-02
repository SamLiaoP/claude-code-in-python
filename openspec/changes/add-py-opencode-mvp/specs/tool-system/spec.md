## ADDED Requirements

### Requirement: Tool 基類與註冊表
系統 MUST 提供 Tool 基類和 ToolRegistry，所有工具繼承基類實作 `execute(params, context) → ToolResult`。

#### Scenario: 工具自動註冊
- **WHEN** 系統啟動時
- **THEN** 所有 Tool 子類自動註冊到 ToolRegistry，可透過 tool_id 查詢

### Requirement: Python 沙盒執行
系統 MUST 提供 `python` tool，透過 subprocess 安全執行 AI 產生的 Python 程式碼，timeout 30 秒，stdout 截斷至 10,000 字元。

#### Scenario: 執行 Python 程式碼
- **WHEN** AI 呼叫 `python(code="print(1+1)")`
- **THEN** 系統執行程式碼並回傳 stdout 結果 `"2"`

#### Scenario: 執行超時中斷
- **WHEN** AI 呼叫 `python(code="while True: pass")`
- **THEN** 系統在 30 秒後中斷執行並回傳超時錯誤

### Requirement: Shell 沙盒執行
系統 MUST 提供 `bash` tool，透過 subprocess 執行 Shell 命令，timeout 60 秒。

#### Scenario: 執行 Shell 命令
- **WHEN** AI 呼叫 `bash(command="ls -la")`
- **THEN** 系統執行命令並回傳 stdout 結果

### Requirement: 檔案讀寫工具
系統 MUST 提供 `read_file` 和 `write_file` tool。

#### Scenario: 讀取檔案
- **WHEN** AI 呼叫 `read_file(path="/tmp/data.csv")`
- **THEN** 系統回傳檔案內容

### Requirement: Ask User Tool
系統 MUST 提供 `ask_user` tool，AI 可向使用者發送結構化問題（含選項），Processor 暫停等待使用者回應後繼續。

#### Scenario: AI 向使用者提問
- **WHEN** AI 呼叫 `ask_user(question="要深入哪篇文獻？", options=["文獻A", "文獻B"])`
- **THEN** WebSocket 推送 `question` 事件給前端，Processor 暫停等待回應

#### Scenario: 使用者回答後繼續
- **WHEN** 前端送回 `answer` 事件
- **THEN** 使用者回答作為 tool result 送回 LLM 繼續生成

### Requirement: Skill Meta-Tool
系統 MUST 提供 `skill` meta-tool，其 description 動態聚合所有 SKILL.md 的 name + description。AI 呼叫時讀取完整 SKILL.md 內容作為上下文。

#### Scenario: AI 觸發 Skill 載入
- **WHEN** AI 呼叫 `skill(name="pubmed-search")`
- **THEN** 系統讀取完整 SKILL.md 內容，回傳給 LLM 作為上下文繼續執行

### Requirement: Skills 掃描與索引
系統 MUST 在啟動時掃描 `~/.py-opencode/skills/**/SKILL.md`（全域）和 `<project>/.py-opencode/skills/**/SKILL.md`（專案級），只讀 YAML frontmatter 建索引。專案級同名 Skill 覆蓋全域。

#### Scenario: 掃描並索引 Skills
- **WHEN** 系統啟動時
- **THEN** 掃描所有路徑的 SKILL.md，讀取 frontmatter（name, description, allowed-tools）建立索引

#### Scenario: 對話連線時掃描專案級 Skills
- **WHEN** 使用者連線 WebSocket 開始對話
- **THEN** 系統根據 Session 的 project_dir 重新掃描全域 + 專案級 Skills

#### Scenario: 專案級 Skill 覆蓋全域
- **WHEN** 全域和專案級都有名為 `data-analysis` 的 SKILL.md
- **THEN** 專案級版本覆蓋全域版本

### Requirement: Processor 狀態機
Processor MUST 處理 LLM 串流事件（text_delta / tool_use_start / tool_use_input / tool_use_done / message_stop），自動循環執行 tool_use 並送回 LLM 繼續生成。MUST 實作 doom loop 偵測：同一工具用相同參數呼叫 3 次則中斷。

#### Scenario: 工具呼叫自動循環
- **WHEN** LLM 回應包含 tool_use
- **THEN** Processor 執行工具，將結果送回 LLM 繼續生成，直到 LLM 不再呼叫工具

#### Scenario: Doom Loop 偵測
- **WHEN** 同一工具用相同參數被呼叫 3 次
- **THEN** Processor 中斷循環並回報錯誤
