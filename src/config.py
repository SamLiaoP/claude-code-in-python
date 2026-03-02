###
# config.py — 設定載入模組
#
# 用途：載入 ~/.py-opencode/config.json（全域）+ <project>/.py-opencode/config.json（專案級）+ 環境變數合併
# 主要功能：
#   - 程式內建預設值 → 全域 config → 專案級 config（深度合併）→ 環境變數 PY_OPENCODE_*
#   - 提供 ProviderConfig / AppConfig 資料結構
#   - ProviderConfig 使用 LiteLLM 慣例：api_base（非 base_url）、model 帶 provider 前綴（如 ollama/llama3）
# 關聯：被 provider.py / auth.py / main.py 引用
###

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel

# 全域設定目錄
GLOBAL_CONFIG_DIR = Path.home() / ".py-opencode"
GLOBAL_CONFIG_FILE = GLOBAL_CONFIG_DIR / "config.json"


class ProviderConfig(BaseModel):
    api_base: str | None = None
    api_key: str | None = None
    api_key_env: str | None = None
    model: str = "ollama/llama3"

    def resolve_api_key(self) -> str:
        """解析 API Key：優先環境變數，其次直接設定值"""
        if self.api_key_env:
            val = os.environ.get(self.api_key_env)
            if val:
                return val
        return self.api_key or ""


class SandboxConfig(BaseModel):
    timeout: int = 30
    max_output: int = 10000


class AppConfig(BaseModel):
    providers: dict[str, ProviderConfig] = {}
    default_provider: str = "local"
    api_keys: dict[str, str] = {}  # key -> user_id
    sandbox: SandboxConfig = SandboxConfig()
    db_path: str = ""  # 自動設定


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合併兩個 dict，override 覆蓋 base"""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _load_json(path: Path) -> dict[str, Any]:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _apply_env_overrides(data: dict) -> dict:
    """套用 PY_OPENCODE_* 環境變數覆蓋"""
    prefix = "PY_OPENCODE_"
    for key, val in os.environ.items():
        if key.startswith(prefix):
            # PY_OPENCODE_DEFAULT_PROVIDER -> default_provider
            config_key = key[len(prefix):].lower()
            data[config_key] = val
    return data


def load_config(project_dir: str | None = None) -> AppConfig:
    """載入合併後的設定"""
    # 1. 內建預設
    data: dict[str, Any] = {}

    # 2. 全域 config
    global_data = _load_json(GLOBAL_CONFIG_FILE)
    data = _deep_merge(data, global_data)

    # 3. 專案級 config
    if project_dir:
        project_config = Path(project_dir) / ".py-opencode" / "config.json"
        project_data = _load_json(project_config)
        data = _deep_merge(data, project_data)

    # 4. 環境變數覆蓋
    data = _apply_env_overrides(data)

    # 設定 db_path 預設值
    if not data.get("db_path"):
        data["db_path"] = str(GLOBAL_CONFIG_DIR / "data.db")

    config = AppConfig(**data)
    return config
