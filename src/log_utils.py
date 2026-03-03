###
# log_utils.py — Session 專屬日誌工具
#
# 用途：為每個 session 建立獨立的 log 檔案
# 主要功能：
#   - get_session_logger(session_id): 回傳寫入 logs/sessions/<session_id>.log 的 logger
# 關聯：被 session/processor.py, api/chat.py 使用
###

import logging
import os

_LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs", "sessions")
_LOG_FORMAT = "%(asctime)s %(name)s [%(levelname)s] %(message)s"

# 快取已建立的 logger，避免重複加 handler
_session_loggers: dict[str, logging.Logger] = {}


def get_session_logger(session_id: str) -> logging.Logger:
    """取得 session 專屬 logger，日誌寫入 logs/sessions/<session_id>.log"""
    if session_id in _session_loggers:
        return _session_loggers[session_id]

    os.makedirs(_LOGS_DIR, exist_ok=True)
    log_path = os.path.join(_LOGS_DIR, f"{session_id}.log")

    logger = logging.getLogger(f"session.{session_id}")
    logger.setLevel(logging.DEBUG)

    # 避免重複加 handler（防禦性檢查）
    if not logger.handlers:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(fh)

    _session_loggers[session_id] = logger
    return logger
