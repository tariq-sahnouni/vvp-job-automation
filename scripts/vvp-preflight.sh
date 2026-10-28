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
auth_header() { if [ -n "${VVP_API_TOKEN:-}" ]; then printf "Authorization: Bearer %s" "$VVP_API_TOKEN"; fi; }
auth_mode_label() { if [ -n "${VVP_API_TOKEN:-}" ]; then printf 'VVP token'; else printf 'none'; fi; }
vvp_request() { method="$1"; path="$2"; require_command curl; url="${VVP_BASE_URL%/}$path"; if [ "$VVP_DRY_RUN" = "true" ]; then log "DRY RUN $method $url"; return 0; fi; insecure_arg="$(curl_insecure_arg)"; header="$(auth_header)"; if [ -n "$header" ]; then curl -sS -f $insecure_arg --connect-timeout 10 --max-time "$VVP_REQUEST_TIMEOUT" -X "$method" -H "$header" -H "Accept: application/json" "$url"; else curl -sS -f $insecure_arg --connect-timeout 10 --max-time "$VVP_REQUEST_TIMEOUT" -X "$method" -H "Accept: application/json" "$url"; fi; }
usage() { printf 'Usage:\n  vvp-preflight.sh\n'; }
load_env_files
[ "${1:-}" = "--help" ] && { usage; exit 0; }
[ "$#" -eq 0 ] || { usage >&2; exit 2; }
: "${VVP_REQUEST_TIMEOUT:=${FLINK_REQUEST_TIMEOUT:-60}}"; : "${VVP_DRY_RUN:=${FLINK_DRY_RUN:-false}}"; : "${VVP_API_PREFIX:=/api/v1}"
VVP_BASE_URL="${VVP_API_BASE_URL:-${VVP_BASE_URL:-${FLINK_BASE_URL:-}}}"; VVP_API_NAMESPACE="${VVP_API_NAMESPACE:-${FLINK_NAMESPACE:-${VVP_NAMESPACE:-default}}}"
[ -n "$VVP_BASE_URL" ] || fail "VVP_API_BASE_URL, VVP_BASE_URL, or FLINK_BASE_URL is required"
log "checking VVP API at ${VVP_BASE_URL%/}"
log "VVP API namespace: $VVP_API_NAMESPACE"
log "authentication: $(auth_mode_label)"
vvp_request GET "${VVP_API_PREFIX%/}/namespaces/$VVP_API_NAMESPACE/deployments" >/dev/null
ok "API access can list VVP deployments in namespace $VVP_API_NAMESPACE"
if vvp_request GET "${VVP_API_PREFIX%/}/namespaces/$VVP_API_NAMESPACE/sessionclusters" >/dev/null 2>&1; then ok "API access can list VVP session clusters"; elif [ "${VVP_PREFLIGHT_STRICT:-${FLINK_PREFLIGHT_STRICT:-false}}" = "true" ]; then fail "API access cannot list VVP session clusters"; else warn "API access cannot list VVP session clusters"; fi
if vvp_request GET "${VVP_API_PREFIX%/}/namespaces/$VVP_API_NAMESPACE/deployment-targets" >/dev/null 2>&1; then ok "API access can list VVP deployment targets"; elif [ "${VVP_PREFLIGHT_STRICT:-${FLINK_PREFLIGHT_STRICT:-false}}" = "true" ]; then fail "API access cannot list VVP deployment targets"; else warn "API access cannot list VVP deployment targets; teams often consume pre-created targets"; fi
ok "VVP preflight passed"
