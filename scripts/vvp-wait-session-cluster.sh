#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

log() { printf '[INFO] %s\n' "$*"; }
ok() { printf '[OK] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }
require_command() { command -v "$1" >/dev/null 2>&1 || fail "$1 is required"; }
load_env_files() { [ "${FLINK_LOAD_ENV_FILE:-true}" = "false" ] && return; explicit=false; if [ -n "${FLINK_ENV_FILE:-}" ]; then env_files="$FLINK_ENV_FILE"; explicit=true; else env_files=".env"; fi; old_ifs="$IFS"; IFS=:; for env_file in $env_files; do IFS="$old_ifs"; [ -n "$env_file" ] || continue; case "$env_file" in /*) env_path="$env_file" ;; *) env_path="$REPO_DIR/$env_file" ;; esac; if [ -r "$env_path" ]; then . "$env_path"; elif [ "$explicit" = "true" ]; then fail "FLINK_ENV_FILE is not readable: $env_file"; fi; IFS=:; done; IFS="$old_ifs"; }
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
vvp_get() { path="$1"; require_command curl; url="${VVP_BASE_URL%/}$path"; insecure_arg="$(curl_insecure_arg)"; header="$(auth_header)"; if [ -n "$header" ]; then curl -sS -f $insecure_arg --connect-timeout 10 --max-time "$VVP_REQUEST_TIMEOUT" -H "$header" -H "Accept: application/json" "$url"; else curl -sS -f $insecure_arg --connect-timeout 10 --max-time "$VVP_REQUEST_TIMEOUT" -H "Accept: application/json" "$url"; fi; }
usage() { printf 'Usage:\n  vvp-wait-session-cluster.sh <session-cluster-name> <expected-state> [timeout-seconds]\n'; }
load_env_files
[ "${1:-}" = "--help" ] && { usage; exit 0; }
[ "$#" -ge 2 ] && [ "$#" -le 3 ] || { usage >&2; exit 2; }
: "${VVP_REQUEST_TIMEOUT:=${FLINK_REQUEST_TIMEOUT:-60}}"; : "${VVP_API_PREFIX:=/api/v1}"; : "${VVP_POLL_SECONDS:=${FLINK_POLL_SECONDS:-10}}"
VVP_BASE_URL="${VVP_API_BASE_URL:-${VVP_BASE_URL:-${FLINK_BASE_URL:-}}}"; VVP_API_NAMESPACE="${VVP_API_NAMESPACE:-${FLINK_NAMESPACE:-${VVP_NAMESPACE:-default}}}"
[ -n "$VVP_BASE_URL" ] || fail "VVP_API_BASE_URL, VVP_BASE_URL, or FLINK_BASE_URL is required"
require_command python3
name="$1"; expected="$2"; timeout_seconds="${3:-600}"; start="$(date +%s)"; tmp="${TMPDIR:-/tmp}/vvp-session-cluster-status-$name-$$.json"; trap 'rm -f "$tmp"' EXIT HUP INT TERM
while :; do
  if vvp_get "${VVP_API_PREFIX%/}/namespaces/$VVP_API_NAMESPACE/sessionclusters/$name" > "$tmp"; then
    actual="$(python3 - "$tmp" <<'PY'
import json, sys
from pathlib import Path
data=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for path in ("state","status.state","status.phase","status.sessionClusterState","spec.state"):
    cur=data
    for part in path.split("."):
        cur=cur.get(part) if isinstance(cur, dict) else None
    if isinstance(cur,(str,int,float,bool)):
        print(cur); raise SystemExit(0)
print("UNKNOWN")
PY
)"
    log "sessionclusters/$name state: $actual"
    [ "$(printf '%s' "$actual" | tr '[:lower:]' '[:upper:]')" = "$(printf '%s' "$expected" | tr '[:lower:]' '[:upper:]')" ] && { ok "sessionclusters/$name reached $expected"; exit 0; }
  else
    warn "could not read sessionclusters/$name yet"
  fi
  now="$(date +%s)"; [ "$((now - start))" -lt "$timeout_seconds" ] || fail "timed out waiting for sessionclusters/$name to reach $expected"; sleep "$VVP_POLL_SECONDS"
done
