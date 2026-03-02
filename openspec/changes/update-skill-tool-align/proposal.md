# Change: Skill Tool 行為對齊 OpenCode

## Why
比對 claudecodeinpython 與 opencode 的 skill tool 實作，發現兩處行為差異：
1. `get_skill_content()` 回傳完整檔案含 YAML frontmatter，opencode 會移除 frontmatter 只回傳純內容
2. 找不到 skill 時錯誤訊息未列出可用技能名稱，opencode 會列出方便 LLM 自行修正

## What Changes
- `src/skill.py` 的 `get_skill_content()` 改用 `frontmatter.load()` 解析，回傳 `post.content`（不含 YAML frontmatter）
- `src/tool/skill_tool.py` 的 `execute()` 找不到 skill 時，錯誤訊息附上所有可用技能名稱

## Impact
- Affected specs: `tool-system`（Skill Meta-Tool requirement）
- Affected code: `src/skill.py`, `src/tool/skill_tool.py`
