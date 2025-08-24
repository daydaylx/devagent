from __future__ import annotations

DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
STATE_DIR_NAME = ".devagent"
CONFIG_FILE_NAME = "config.toml"
LAST_PLAN_FILE = "last_plan.md"
LAST_PATCH_FILE = "last_patch.diff"
INDEX_FILE = "index.json"
SESSION_FILE = "session.json"

DEFAULT_MAX_USD = 0.50

EXCLUDE_DIRS = {
    ".git", "node_modules", ".venv", "venv", ".mypy_cache", ".pytest_cache",
    "dist", "build", ".dist", "__pycache__",
}
