## MODIFIED Requirements
### Requirement: Skill Meta-Tool
系統 MUST 提供 `skill` meta-tool，其 description 動態聚合所有 SKILL.md 的 name + description。AI 呼叫時讀取 SKILL.md 內容（去除 YAML frontmatter）作為上下文。找不到指定 skill 時，錯誤訊息 MUST 列出所有可用技能名稱。

#### Scenario: AI 觸發 Skill 載入
- **WHEN** AI 呼叫 `skill(name="pubmed-search")`
- **THEN** 系統讀取 SKILL.md 內容（不含 YAML frontmatter），回傳給 LLM 作為上下文繼續執行

#### Scenario: 找不到指定 Skill
- **WHEN** AI 呼叫 `skill(name="not-exist")`
- **THEN** 系統回傳錯誤訊息，包含所有可用技能名稱供 LLM 參考
