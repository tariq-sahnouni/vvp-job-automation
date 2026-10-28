#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

ok() { printf '[OK] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }
require_command() { command -v "$1" >/dev/null 2>&1 || fail "$1 is required"; }
load_env_files() { [ "${FLINK_LOAD_ENV_FILE:-true}" = "false" ] && return; explicit=false; if [ -n "${FLINK_ENV_FILE:-}" ]; then env_files="$FLINK_ENV_FILE"; explicit=true; else env_files=".env"; fi; old_ifs="$IFS"; IFS=:; for env_file in $env_files; do IFS="$old_ifs"; [ -n "$env_file" ] || continue; case "$env_file" in /*) env_path="$env_file" ;; *) env_path="$REPO_DIR/$env_file" ;; esac; if [ -r "$env_path" ]; then . "$env_path"; elif [ "$explicit" = "true" ]; then fail "FLINK_ENV_FILE is not readable: $env_file"; fi; IFS=:; done; IFS="$old_ifs"; }
curl_insecure_arg() { if [ "${VVP_INSECURE_TLS:-${FLINK_INSECURE_TLS:-false}}" = "true" ]; then printf -- '-k'; fi; }
auth_header() { if [ -n "${VVP_API_TOKEN:-}" ]; then printf "Authorization: Bearer %s" "$VVP_API_TOKEN"; fi; }
vvp_request() { method="$1"; path="$2"; payload="${3:-}"; content_type="${4:-application/json}"; require_command curl; url="${VVP_BASE_URL%/}$path"; if [ "$VVP_DRY_RUN" = "true" ]; then printf '[INFO] DRY RUN %s %s\n' "$method" "$url"; return 0; fi; insecure_arg="$(curl_insecure_arg)"; header="$(auth_header)"; if [ -n "$payload" ]; then if [ -n "$header" ]; then curl -sS -f $insecure_arg --connect-timeout 10 --max-time "$VVP_REQUEST_TIMEOUT" -X "$method" -H "$header" -H "Accept: application/json" -H "Content-Type: $content_type" --data-binary "@$payload" "$url"; else curl -sS -f $insecure_arg --connect-timeout 10 --max-time "$VVP_REQUEST_TIMEOUT" -X "$method" -H "Accept: application/json" -H "Content-Type: $content_type" --data-binary "@$payload" "$url"; fi; else if [ -n "$header" ]; then curl -sS -f $insecure_arg --connect-timeout 10 --max-time "$VVP_REQUEST_TIMEOUT" -X "$method" -H "$header" -H "Accept: application/json" "$url"; else curl -sS -f $insecure_arg --connect-timeout 10 --max-time "$VVP_REQUEST_TIMEOUT" -X "$method" -H "Accept: application/json" "$url"; fi; fi; }
usage() { printf 'Usage:\n  vvp-delete-deployment.sh <deployment-name>\n\nSet VVP_CONFIRM_DELETE=true.\n'; }
load_env_files
[ "${1:-}" = "--help" ] && { usage; exit 0; }
[ "$#" -eq 1 ] || { usage >&2; exit 2; }
[ "${VVP_CONFIRM_DELETE:-${FLINK_CONFIRM_DELETE:-false}}" = "true" ] || fail "set VVP_CONFIRM_DELETE=true or FLINK_CONFIRM_DELETE=true to delete"
: "${VVP_REQUEST_TIMEOUT:=${FLINK_REQUEST_TIMEOUT:-60}}"; : "${VVP_DRY_RUN:=${FLINK_DRY_RUN:-false}}"; : "${VVP_API_PREFIX:=/api/v1}"
VVP_BASE_URL="${VVP_API_BASE_URL:-${VVP_BASE_URL:-${FLINK_BASE_URL:-}}}"; VVP_API_NAMESPACE="${VVP_API_NAMESPACE:-${FLINK_NAMESPACE:-${VVP_NAMESPACE:-default}}}"
[ -n "$VVP_BASE_URL" ] || fail "VVP_API_BASE_URL, VVP_BASE_URL, or FLINK_BASE_URL is required"
name="$1"; base="${VVP_API_PREFIX%/}/namespaces/$VVP_API_NAMESPACE/deployments/$name"
if [ "${VVP_DELETE_STOP_FIRST:-true}" = "true" ]; then
  tmp="${TMPDIR:-/tmp}/vvp-delete-$name-$$.json"; trap 'rm -f "$tmp"' EXIT HUP INT TERM
  printf '{"spec":{"state":"%s"}}\n' "${VVP_DELETE_STOP_STATE:-CANCELLED}" > "$tmp"
  vvp_request PATCH "$base" "$tmp" "application/merge-patch+json" >/dev/null
  ok "patched VVP deployment $name to ${VVP_DELETE_STOP_STATE:-CANCELLED} before delete"
fi
attempt=1; attempts="${VVP_DELETE_RETRY_ATTEMPTS:-12}"; sleep_seconds="${VVP_DELETE_RETRY_SECONDS:-5}"
while :; do
  if vvp_request DELETE "$base" >/dev/null; then break; fi
  [ "$attempt" -lt "$attempts" ] || fail "failed to delete VVP deployment $name after $attempts attempts"
  warn "VVP deployment $name is not deletable yet; retrying in ${sleep_seconds}s"
  attempt="$((attempt + 1))"; sleep "$sleep_seconds"
done
ok "deleted VVP deployment $name"
