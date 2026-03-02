###
# skill.py — SKILL.md 掃描、frontmatter 快取、完整內容讀取
#
# 用途：相容 OpenCode SKILL.md 格式，掃描全域 + 專案級 skills 目錄
# 主要功能：
#   - scan_skills(): 掃描並索引所有 SKILL.md（只讀 frontmatter）
#   - get_skill_info(name): 取得 SkillInfo（含 path），供 skill_tool 注入 base directory
#   - get_skill_content(name): 讀取 SKILL.md 內容，去除 YAML frontmatter（lazy load）
#   - list_skills(): 列出所有已索引的 skill
# 關聯：被 tool/skill_tool.py, api/skills.py 引用
###

import logging
from dataclasses import dataclass
from pathlib import Path

import frontmatter

from config import GLOBAL_CONFIG_DIR

logger = logging.getLogger(__name__)


@dataclass
class SkillInfo:
    name: str
    description: str
    allowed_tools: str
    source: str  # "global" | "project"
    path: Path  # SKILL.md 完整路徑


# 全域 skill 索引
_skills: dict[str, SkillInfo] = {}


def scan_skills(project_dir: str | None = None) -> int:
    """掃描全域 + 專案級 SKILL.md，回傳 skill 數量"""
    global _skills
    _skills.clear()

    # 1. 全域 skills
    global_skills_dir = GLOBAL_CONFIG_DIR / "skills"
    _scan_dir(global_skills_dir, "global")

    # 2. 專案級 skills（同名覆蓋全域）
    if project_dir:
        project_skills_dir = Path(project_dir) / ".py-opencode" / "skills"
        _scan_dir(project_skills_dir, "project")

    logger.info(f"已索引 {len(_skills)} 個 Skills")
    return len(_skills)


def _scan_dir(skills_dir: Path, source: str):
    """掃描一個 skills 目錄"""
    if not skills_dir.exists():
        return
    for skill_md in skills_dir.rglob("SKILL.md"):
        try:
            post = frontmatter.load(str(skill_md))
            name = post.get("name", skill_md.parent.name)
            desc = post.get("description", "")
            allowed = post.get("allowed-tools", "")
            _skills[name] = SkillInfo(
                name=name,
                description=desc,
                allowed_tools=allowed,
                source=source,
                path=skill_md,
            )
        except Exception as e:
            logger.warning(f"解析 SKILL.md 失敗: {skill_md} — {e}")


def list_skills() -> list[dict]:
    """列出所有已索引的 skill（不含完整內容）"""
    return [
        {"name": s.name, "description": s.description, "source": s.source}
        for s in _skills.values()
    ]


def get_skill_info(name: str) -> SkillInfo | None:
    """取得 SkillInfo（含 path），供 skill_tool 注入 base directory"""
    return _skills.get(name)


def get_skill_content(name: str) -> str | None:
    """讀取 SKILL.md 內容（去除 YAML frontmatter）"""
    skill = _skills.get(name)
    if not skill:
        return None
    try:
        post = frontmatter.load(str(skill.path))
        return post.content
    except Exception as e:
        logger.error(f"讀取 SKILL.md 失敗: {skill.path} — {e}")
        return None


def get_skill_names_xml() -> str:
    """產生所有 skill 的 XML 描述（用於 skill tool 的 description）"""
    if not _skills:
        return "<skills>目前沒有可用的 Skills</skills>"
    lines = ["<skills>"]
    for s in _skills.values():
        lines.append(f'  <skill name="{s.name}">{s.description}</skill>')
    lines.append("</skills>")
    return "\n".join(lines)
