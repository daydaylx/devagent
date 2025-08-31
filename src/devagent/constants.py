DEFAULT_IGNORES = [
    ".git", ".devagent", ".venv", "__pycache__", "node_modules",
    "dist", "build", "coverage", ".mypy_cache", ".pytest_cache"
]
SENSITIVE_NAMES = [".env", ".env.local", "id_rsa", "id_ed25519", "secrets", "credentials"]
MAX_FILE_BYTES = 256 * 1024  # 256 KiB pro Datei in der Projektkarte

PREVIEW_CODE_FILE = ".devagent/approval_code.txt"
PLAN_FILE = ".devagent/plan.yaml"
STATE_FILE = ".devagent/state.json"
LOG_DIR = ".devagent/logs"
TRASH_DIR = ".devagent/trash"
SESSIONS_DIR = ".devagent/sessions"
HOOKS_DIR = ".devagent/hooks"
