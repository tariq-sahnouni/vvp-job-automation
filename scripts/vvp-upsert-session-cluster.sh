#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

log() { printf '[INFO] %s\n' "$*"; }
ok() { printf '[OK] %s\n' "$*"; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }
require_command() { command -v "$1" >/dev/null 2>&1 || fail "$1 is required"; }
require_file() { [ -f "$1" ] && [ -r "$1" ] || fail "file is not readable: $1"; }
load_env_files() { [ "${FLINK_LOAD_ENV_FILE:-true}" = "false" ] && return; explicit=false; if [ -n "${FLINK_ENV_FILE:-}" ]; then env_files="$FLINK_ENV_FILE"; explicit=true; else env_files=".env"; fi; old_ifs="$IFS"; IFS=:; for env_file in $env_files; do IFS="$old_ifs"; [ -n "$env_file" ] || continue; case "$env_file" in /*) env_path="$env_file" ;; *) env_path="$REPO_DIR/$env_file" ;; esac; if [ -r "$env_path" ]; then . "$env_path"; elif [ "$explicit" = "true" ]; then fail "FLINK_ENV_FILE is not readable: $env_file"; fi; IFS=:; done; IFS="$old_ifs"; }
manifest_name() { require_command python3; require_file "$1"; python3 - "$1" <<'PY'
import json, re, sys
from pathlib import Path
text=Path(sys.argv[1]).read_text(encoding="utf-8")
try:
    data=json.loads(text); name=data.get("metadata",{}).get("name")
    if name: print(name); raise SystemExit(0)
except Exception: pass
in_metadata=False; metadata_indent=0
for line in text.splitlines():
    stripped=line.strip()
    if not stripped or stripped.startswith("#"): continue
    indent=len(line)-len(line.lstrip(" "))
    if re.match(r"^metadata\s*:\s*(#.*)?$", stripped): in_metadata=True; metadata_indent=indent; continue
    if in_metadata and indent <= metadata_indent: in_metadata=False
    if in_metadata:
        m=re.match(r"^name\s*:\s*['\"]?([^'\"#]+?)['\"]?\s*(#.*)?$", stripped)
        if m: print(m.group(1).strip()); raise SystemExit(0)
print("[ERROR] could not find metadata.name in manifest", file=sys.stderr); raise SystemExit(1)
PY
}
render_manifest() { require_command python3; python3 - "$1" "$2" <<'PY'
import os, re, sys
from pathlib import Path
source, target = map(Path, sys.argv[1:])
def replace(match):
    name = match.group(1)
    if name not in os.environ:
        raise SystemExit(f"[ERROR] {source} references unset environment variable {name}")
    return os.environ[name]
target.write_text(re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", replace, source.read_text()), encoding="utf-8")
PY
}
curl_insecure_arg() { if [ "${VVP_INSECURE_TLS:-${FLINK_INSECURE_TLS:-false}}" = "true" ]; then printf -- '-k'; fi; }
auth_header() { if [ -n "${VVP_API_TOKEN:-}" ]; then printf "Authorization: Bearer %s" "$VVP_API_TOKEN"; fi; }
vvp_request() { method="$1"; path="$2"; payload="$3"; require_command curl; url="${VVP_BASE_URL%/}$path"; if [ "$VVP_DRY_RUN" = "true" ]; then log "DRY RUN $method $url"; log "DRY RUN payload: $payload"; return 0; fi; insecure_arg="$(curl_insecure_arg)"; header="$(auth_header)"; if [ -n "$header" ]; then curl -sS -f $insecure_arg --connect-timeout 10 --max-time "$VVP_REQUEST_TIMEOUT" -X "$method" -H "$header" -H "Accept: application/json" -H "Content-Type: application/yaml" --data-binary "@$payload" "$url"; else curl -sS -f $insecure_arg --connect-timeout 10 --max-time "$VVP_REQUEST_TIMEOUT" -X "$method" -H "Accept: application/json" -H "Content-Type: application/yaml" --data-binary "@$payload" "$url"; fi; }
usage() { printf 'Usage:\n  vvp-upsert-session-cluster.sh <session-cluster-manifest.yaml|json>\n  vvp-upsert-session-cluster.sh <session-cluster-name> <session-cluster-manifest.yaml|json>\n'; }
load_env_files
[ "${1:-}" = "--help" ] && { usage; exit 0; }
[ "$#" -eq 1 ] || [ "$#" -eq 2 ] || { usage >&2; exit 2; }
if [ "$#" -eq 1 ]; then payload="$1"; name="$(manifest_name "$payload")"; else name="$1"; payload="$2"; fi
require_file "$payload"
: "${VVP_REQUEST_TIMEOUT:=${FLINK_REQUEST_TIMEOUT:-60}}"; : "${VVP_DRY_RUN:=${FLINK_DRY_RUN:-false}}"; : "${VVP_API_PREFIX:=/api/v1}"
VVP_BASE_URL="${VVP_API_BASE_URL:-${VVP_BASE_URL:-${FLINK_BASE_URL:-}}}"; VVP_API_NAMESPACE="${VVP_API_NAMESPACE:-${FLINK_NAMESPACE:-${VVP_NAMESPACE:-default}}}"
[ -n "$VVP_BASE_URL" ] || fail "VVP_API_BASE_URL, VVP_BASE_URL, or FLINK_BASE_URL is required"
rendered="${TMPDIR:-/tmp}/vvp-session-cluster-rendered-$name-$$.yaml"; trap 'rm -f "$rendered"' EXIT HUP INT TERM
render_manifest "$payload" "$rendered"; payload="$rendered"
vvp_request PUT "${VVP_API_PREFIX%/}/namespaces/$VVP_API_NAMESPACE/sessionclusters/$name" "$payload" >/dev/null
ok "submitted VVP session cluster payload for $name"
