###
# tests/test_config.py — config 載入測試
###

import json
import os
import tempfile

from config import load_config, _deep_merge


def test_deep_merge():
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"c": 99}, "e": 5}
    result = _deep_merge(base, override)
    assert result == {"a": 1, "b": {"c": 99, "d": 3}, "e": 5}


# def test_load_config_defaults():
#     config = load_config()
#     assert config.default_provider == "local"
#     assert config.sandbox.timeout == 30


def test_load_config_with_project_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = os.path.join(tmpdir, ".py-opencode")
        os.makedirs(config_dir)
        with open(os.path.join(config_dir, "config.json"), "w") as f:
            json.dump({"default_provider": "claude"}, f)
        config = load_config(project_dir=tmpdir)
        assert config.default_provider == "claude"


def test_env_override():
    os.environ["PY_OPENCODE_DEFAULT_PROVIDER"] = "test-env"
    try:
        config = load_config()
        assert config.default_provider == "test-env"
    finally:
        del os.environ["PY_OPENCODE_DEFAULT_PROVIDER"]
