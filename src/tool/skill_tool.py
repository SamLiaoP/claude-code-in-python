###
# tool/skill_tool.py — Skill meta-tool
#
# 用途：LLM 透過此 tool 載入 domain knowledge（SKILL.md 完整內容）
# 主要功能：tool description 動態聚合所有 SKILL.md 的 name + description（XML 格式）
#           載入時注入 base directory 路徑，讓 LLM 能存取 references/ 和 scripts/
# 關聯：繼承 tool/base.py Tool，使用 skill.py（get_skill_content, get_skill_info）
###

import logging
from typing import Any

from tool.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)


class SkillTool(Tool):
    name = "skill"
    parameters = {
        "name": {"type": "string", "description": "要載入的 Skill 名稱"},
    }

    @property
    def description(self) -> str:
        """動態產生 description，包含所有可用 skill 列表"""
        from skill import get_skill_names_xml
        return (
            "載入 domain knowledge（Skill）。根據使用者的問題，選擇合適的 Skill 載入。\n"
            "可用的 Skills:\n" + get_skill_names_xml()
        )

    def get_schema(self) -> dict:
        """覆寫以使用動態 description"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": ["name"],
            },
        }

    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult:
        from skill import get_skill_content
        name = params.get("name", "")
        if not name:
            return ToolResult(error="name 參數必填")

        content = get_skill_content(name)
        if content is None:
            return ToolResult(error=f"找不到 Skill: {name}")

        from skill import get_skill_info
        skill_info = get_skill_info(name)
        skill_dir = str(skill_info.path.parent) if skill_info else ""
        output = f"## Skill: {name}\n\n**Base directory**: {skill_dir}\n\n{content}"
        logger.debug("=== SKILL LOADED: %s ===", name)
        logger.debug("  base_dir: %s", skill_dir)
        logger.debug("  content (%d chars): %s", len(output), output[:500])
        return ToolResult(output=output)
