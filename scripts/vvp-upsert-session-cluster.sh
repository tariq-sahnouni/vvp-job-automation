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
curl_insecure_arg() { if [ "${VVP_INSECURE_TLS:-${FLINK_INSECURE_TLS:-false}}" = "true" ]; then printf -- '-k'; fi; }
token_url() { if [ -n "${KEYCLOAK_TOKEN_URL:-}" ]; then printf '%s' "$KEYCLOAK_TOKEN_URL"; else printf '%s/realms/%s/protocol/openid-connect/token' "${KEYCLOAK_BASE_URL%/}" "$KEYCLOAK_REALM"; fi; }
keycloak_token() { require_command curl; require_command python3; [ -n "${AUTH_ACCESS_TOKEN:-}" ] && { printf '%s' "$AUTH_ACCESS_TOKEN"; return; }; [ -n "${KEYCLOAK_BASE_URL:-${KEYCLOAK_TOKEN_URL:-}}" ] || fail "KEYCLOAK_BASE_URL or KEYCLOAK_TOKEN_URL is required"; [ -n "${KEYCLOAK_TOKEN_URL:-}" ] || [ -n "${KEYCLOAK_REALM:-}" ] || fail "KEYCLOAK_REALM is required"; [ -n "${KEYCLOAK_CLIENT_ID:-}" ] || fail "KEYCLOAK_CLIENT_ID is required"; [ -n "${KEYCLOAK_CLIENT_SECRET:-}" ] || fail "KEYCLOAK_CLIENT_SECRET is required"; : "${KEYCLOAK_GRANT_TYPE:=client_credentials}"; insecure_arg="$(curl_insecure_arg)"; response="$(curl -sS -f $insecure_arg --connect-timeout 10 --max-time "$VVP_REQUEST_TIMEOUT" -H "Accept: application/json" -H "Content-Type: application/x-www-form-urlencoded" --data-urlencode "grant_type=$KEYCLOAK_GRANT_TYPE" --data-urlencode "client_id=$KEYCLOAK_CLIENT_ID" --data-urlencode "client_secret=$KEYCLOAK_CLIENT_SECRET" "$(token_url)")" || fail "failed to fetch Keycloak token"; TOKEN_RESPONSE="$response" python3 - <<'PY'
import json, os, sys
token=json.loads(os.environ["TOKEN_RESPONSE"]).get("access_token")
if not token:
    print("[ERROR] Keycloak response did not include access_token", file=sys.stderr)
    raise SystemExit(1)
print(token)
PY
}
auth_header() { raw="${VVP_AUTH_PROVIDER:-${FLINK_AUTH_PROVIDER:-none}}"; case "$(printf '%s' "$raw" | tr '[:upper:]_' '[:lower:]-')" in none|no-auth|disabled|false) return 0 ;; bearer|token|static-bearer) token="${VVP_API_TOKEN:-${FLINK_API_TOKEN:-${AUTH_ACCESS_TOKEN:-}}}"; [ -n "$token" ] || fail "VVP_API_TOKEN or FLINK_API_TOKEN is required"; printf 'Authorization: Bearer %s' "$token" ;; keycloak|keycloak-client-credentials|oidc-keycloak) printf 'Authorization: Bearer %s' "$(keycloak_token)" ;; custom|command) [ -n "${VVP_AUTH_HEADER_COMMAND:-${FLINK_AUTH_HEADER_COMMAND:-}}" ] || fail "VVP_AUTH_HEADER_COMMAND or FLINK_AUTH_HEADER_COMMAND is required"; sh -c "${VVP_AUTH_HEADER_COMMAND:-$FLINK_AUTH_HEADER_COMMAND}" ;; *) fail "unsupported VVP_AUTH_PROVIDER/FLINK_AUTH_PROVIDER: $raw" ;; esac; }
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
vvp_request PUT "${VVP_API_PREFIX%/}/namespaces/$VVP_API_NAMESPACE/sessionclusters/$name" "$payload" >/dev/null
ok "submitted VVP session cluster payload for $name"
