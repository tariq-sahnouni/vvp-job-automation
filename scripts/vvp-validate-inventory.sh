#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

if [ "${1:-}" = "--help" ]; then
  printf 'Usage:\n  vvp-validate-inventory.sh [inventory-directory]\n'
  exit 0
fi

INVENTORY_PATH="${1:-$REPO_DIR/deployments}"

command -v python3 >/dev/null 2>&1 || { printf '[ERROR] python3 is required\n' >&2; exit 1; }

python3 - "$INVENTORY_PATH" <<'PY'
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML is required; install services/vvp-gitops-sync/requirements.txt", file=sys.stderr)
    raise SystemExit(1)

root = Path(sys.argv[1])
if not root.is_dir():
    print(f"[ERROR] inventory directory does not exist: {root}", file=sys.stderr)
    raise SystemExit(1)

variables = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
names = {}
count = 0
for path in sorted(p for p in root.rglob("*") if p.suffix.lower() in {".yaml", ".yml", ".json"}):
    text = path.read_text(encoding="utf-8")
    missing = sorted({name for name in variables.findall(text) if name not in os.environ})
    if missing:
        print(f"[ERROR] {path}: unset inventory variables: {', '.join(missing)}", file=sys.stderr)
        raise SystemExit(1)
    text = variables.sub(lambda match: os.environ[match.group(1)], text)
    for document in yaml.safe_load_all(text):
        if document is None:
            continue
        if not isinstance(document, dict) or document.get("kind") != "Deployment":
            print(f"[ERROR] {path}: every document must be a VVP Deployment", file=sys.stderr)
            raise SystemExit(1)
        name = str((document.get("metadata") or {}).get("name") or "").strip()
        if not name:
            print(f"[ERROR] {path}: metadata.name is required", file=sys.stderr)
            raise SystemExit(1)
        if name in names:
            print(f"[ERROR] duplicate deployment {name}: {names[name]} and {path}", file=sys.stderr)
            raise SystemExit(1)
        names[name] = path
        count += 1

print(f"[OK] validated {count} VVP deployment definition(s) in {root}")
PY
