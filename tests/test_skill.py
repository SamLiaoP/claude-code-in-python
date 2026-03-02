###
# tests/test_skill.py — Skills 系統測試
###

import os
import tempfile

from skill import scan_skills, list_skills, get_skill_content, get_skill_names_xml


def test_scan_skills_empty():
    count = scan_skills()
    # 可能有全域 skills，也可能沒有
    assert isinstance(count, int)


def test_scan_skills_with_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = os.path.join(tmpdir, ".py-opencode", "skills", "test-skill")
        os.makedirs(skills_dir)
        with open(os.path.join(skills_dir, "SKILL.md"), "w") as f:
            f.write("---\nname: test-skill\ndescription: A test skill\nallowed-tools: python\n---\n\n## Test\nThis is a test skill.\n")

        count = scan_skills(project_dir=tmpdir)
        assert count >= 1

        skills = list_skills()
        names = [s["name"] for s in skills]
        assert "test-skill" in names

        content = get_skill_content("test-skill")
        assert content is not None
        assert "This is a test skill" in content

        xml = get_skill_names_xml()
        assert "test-skill" in xml
        assert "A test skill" in xml


def test_create_session_inits_project_dir():
    """建立 session 帶 project_dir 後，.py-opencode/ 結構正確建立"""
    from session.session import _init_project_dir

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_project_dir(tmpdir)

        base = os.path.join(tmpdir, ".py-opencode")
        assert os.path.isdir(os.path.join(base, "skills"))
        assert os.path.isdir(os.path.join(base, "context"))
        assert os.path.isfile(os.path.join(base, "context", "PROJECT.md"))

        # 再次呼叫不會覆蓋已存在的 PROJECT.md
        custom_content = "# 自訂內容"
        with open(os.path.join(base, "context", "PROJECT.md"), "w") as f:
            f.write(custom_content)
        _init_project_dir(tmpdir)
        with open(os.path.join(base, "context", "PROJECT.md")) as f:
            assert f.read() == custom_content


def test_get_nonexistent_skill():
    assert get_skill_content("nonexistent-skill-xyz") is None
