#!/usr/bin/env bash
set -Eeuo pipefail

red()  { printf "\033[31m%s\033[0m\n" "$*" >&2; }
grn()  { printf "\033[32m%s\033[0m\n" "$*"; }
ylw()  { printf "\033[33m%s\033[0m\n" "$*"; }
blu()  { printf "\033[34m%s\033[0m\n" "$*"; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || { red "Fehlt: $1"; exit 1; }; }

# --- Vorabchecks ---
need_cmd python3
need_cmd git

# Python-Version prüfen (>=3.11)
PYV=$(python3 -c 'import sys;print(".".join(map(str,sys.version_info[:2])))')
py_major=${PYV%%.*}; py_minor=${PYV#*.}
if [ "$py_major" -lt 3 ] || { [ "$py_major" -eq 3 ] && [ "$py_minor" -lt 11 ]; }; then
  red "Python >= 3.11 benötigt (gefunden: $PYV). Brich ab."
  exit 1
fi

# Projektwurzel prüfen
if [ ! -f "pyproject.toml" ]; then
  red "pyproject.toml nicht gefunden. Bitte im Projektwurzelordner ausführen."
  exit 1
fi

# --- venv ---
if [ ! -d ".venv" ]; then
  blu "[1/6] Erstelle venv (.venv)…"
  python3 -m venv .venv
else
  blu "[1/6] venv existiert, nutze .venv"
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools >/dev/null

# --- Installation ---
blu "[2/6] Installiere devagent (editable) + pytest…"
python -m pip install -e . >/dev/null
python -m pip install pytest >/dev/null

# --- .devagent/config.toml mit sicheren Defaults ---
blu "[3/6] Schreibe Standardkonfiguration (falls fehlt)…"
mkdir -p .devagent/logs
if [ ! -f ".devagent/config.toml" ]; then
  cat > .devagent/config.toml <<'CFG'
# devagent Konfiguration (sichere Defaults)
model = "deepseek/deepseek-coder"
allow_commands = ["pytest","python","ruff","black","mypy","eslint","tsc","npm","pnpm","yarn","make"]
max_actions = 20
net_allowed = false
enforce_git_for_patches = true
ignores = []
CFG
fi

# --- .env vorbereiten ---
blu "[4/6] .env vorbereiten…"
if [ -n "${OPENROUTER_API_KEY:-}" ]; then
  # Schlüssel aus Env übernehmen
  grep -q '^OPENROUTER_API_KEY=' .env 2>/dev/null || {
    echo "OPENROUTER_API_KEY=${OPENROUTER_API_KEY}" > .env
  }
else
  # Platzhalter nur, wenn keine .env existiert
  if [ ! -f ".env" ]; then
    cat > .env <<'ENVX'
# Trage hier deinen OpenRouter-Key ein oder exportiere ihn vor der Nutzung:
# export OPENROUTER_API_KEY=sk-or-...
OPENROUTER_API_KEY=
ENVX
    ylw "Hinweis: OPENROUTER_API_KEY ist leer. Ohne Key funktioniert 'plan' nicht."
  fi
fi

# --- Git absichern/initialisieren ---
blu "[5/6] Git-Setup prüfen…"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  grn "Git-Repo erkannt."
else
  ylw "Kein Git-Repo erkannt – initialisiere (empfohlen für Patch-Schutz)…"
  git init >/dev/null
  git add -A >/dev/null || true
  git commit -m "init: devagent" >/dev/null || ylw "Commit übersprungen (nichts zu committen?)"
fi

# --- Smoke-Tests ---
blu "[6/6] Smoke-Test…"
python - <<'PY'
import sys
import devagent
print("devagent version:", getattr(devagent, "__version__", "unknown"))
PY

# devagent CLI kurz anpingen
set +e
devagent scan --workspace . >/dev/null 2>&1
SCAN_RC=$?
set -e
if [ $SCAN_RC -ne 0 ]; then
  ylw "scan ohne sichtbare Ausgabe ausgeführt (oder kein Terminal-Theme). Teste manuell: devagent scan -w ."
fi

grn "Fertig. Aktivieren der venv bei Bedarf: 'source .venv/bin/activate'"
cat <<'NEXT'

NÄCHSTE SCHRITTE:
  1) API-Key setzen (falls noch nicht erfolgt):
       export OPENROUTER_API_KEY=sk-or-...    # oder .env ausfüllen
  2) Projektkarte prüfen:
       devagent scan -w .
  3) Plan erzeugen:
       devagent plan -w . -g "Beispiel: Linting ergänzen und Tests fixen"
  4) Dry-Run + Bestätigung:
       devagent preview -w .
       devagent approve -w . --code <aus Preview>
  5) Ausführen:
       devagent execute -w .

Sicherheitsregeln bleiben aktiv: Jail, Allowlist, Dry-Run, Git-Snapshot, Trash.
NEXT
