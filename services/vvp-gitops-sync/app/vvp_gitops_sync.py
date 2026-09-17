#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


MANAGED_ANNOTATION_PREFIX = "vvp-gitops-sync/"


def log(level: str, message: str) -> None:
    print(f"[{level}] {message}", flush=True)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def run(command: list[str], cwd: Path | None = None) -> str:
    log("INFO", "run: " + " ".join(command))
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.stderr.strip():
        log("INFO", completed.stderr.strip())
    return completed.stdout


@dataclass(frozen=True)
class Config:
    git_repo_url: str
    git_branch: str
    git_path: str
    git_cache_dir: Path
    state_file: Path
    sync_interval_seconds: int
    run_once: bool
    dry_run: bool
    force_sync: bool
    prune_enabled: bool
    managed_label_key: str
    managed_label_value: str
    vvp_base_url: str
    vvp_api_namespace: str
    vvp_api_prefix: str
    vvp_request_timeout: int
    vvp_insecure_tls: bool
    delete_stop_first: bool
    delete_stop_state: str
    delete_retry_attempts: int
    delete_retry_seconds: int

    @classmethod
    def from_env(cls, args: argparse.Namespace) -> "Config":
        repo_url = args.repo_url or os.environ.get("GIT_REPO_URL", "")
        base_url = (
            args.vvp_base_url
            or os.environ.get("VVP_API_BASE_URL")
            or os.environ.get("VVP_BASE_URL")
            or os.environ.get("FLINK_BASE_URL")
            or ""
        )
        if not repo_url:
            raise SystemExit("[ERROR] GIT_REPO_URL is required")
        if not base_url:
            raise SystemExit("[ERROR] VVP_API_BASE_URL, VVP_BASE_URL, or FLINK_BASE_URL is required")
        cache_dir = Path(os.environ.get("GIT_CACHE_DIR", "/data/repo"))
        state_file = Path(os.environ.get("VVP_GITOPS_STATE_FILE", str(cache_dir.parent / "state.json")))
        return cls(
            git_repo_url=repo_url,
            git_branch=args.branch or os.environ.get("GIT_BRANCH", "main"),
            git_path=args.path or os.environ.get("GIT_PATH", "deployments"),
            git_cache_dir=cache_dir,
            state_file=state_file,
            sync_interval_seconds=int(os.environ.get("SYNC_INTERVAL_SECONDS", "60")),
            run_once=args.once or env_bool("VVP_GITOPS_RUN_ONCE", False),
            dry_run=args.dry_run or env_bool("VVP_GITOPS_DRY_RUN", env_bool("VVP_DRY_RUN", False)),
            force_sync=args.force or env_bool("VVP_GITOPS_FORCE_SYNC", False),
            prune_enabled=env_bool("VVP_GITOPS_PRUNE_ENABLED", True),
            managed_label_key=os.environ.get("VVP_GITOPS_MANAGED_LABEL_KEY", "managed-by"),
            managed_label_value=os.environ.get("VVP_GITOPS_MANAGED_LABEL_VALUE", "vvp-gitops-sync"),
            vvp_base_url=base_url.rstrip("/"),
            vvp_api_namespace=os.environ.get("VVP_API_NAMESPACE") or os.environ.get("FLINK_NAMESPACE") or os.environ.get("VVP_NAMESPACE", "default"),
            vvp_api_prefix=os.environ.get("VVP_API_PREFIX", "/api/v1").rstrip("/"),
            vvp_request_timeout=int(os.environ.get("VVP_REQUEST_TIMEOUT", os.environ.get("FLINK_REQUEST_TIMEOUT", "60"))),
            vvp_insecure_tls=env_bool("VVP_INSECURE_TLS", env_bool("FLINK_INSECURE_TLS", False)),
            delete_stop_first=env_bool("VVP_GITOPS_DELETE_STOP_FIRST", True),
            delete_stop_state=os.environ.get("VVP_GITOPS_DELETE_STOP_STATE", "CANCELLED"),
            delete_retry_attempts=int(os.environ.get("VVP_GITOPS_DELETE_RETRY_ATTEMPTS", "12")),
            delete_retry_seconds=int(os.environ.get("VVP_GITOPS_DELETE_RETRY_SECONDS", "5")),
        )


class GitRepo:
    def __init__(self, config: Config):
        self.config = config

    def latest_sha(self) -> str:
        refs = [f"refs/heads/{self.config.git_branch}", self.config.git_branch]
        for ref in refs:
            output = subprocess.run(
                ["git", "ls-remote", self.config.git_repo_url, ref],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if output.returncode == 0 and output.stdout.strip():
                return output.stdout.split()[0]
        raise RuntimeError(f"could not resolve Git branch {self.config.git_branch}: {output.stderr.strip()}")

    def checkout(self, sha: str) -> Path:
        cache_dir = self.config.git_cache_dir
        cache_dir.parent.mkdir(parents=True, exist_ok=True)
        if not (cache_dir / ".git").exists():
            if cache_dir.exists() and any(cache_dir.iterdir()):
                raise RuntimeError(f"GIT_CACHE_DIR exists but is not a Git checkout: {cache_dir}")
            run(["git", "clone", "--no-checkout", self.config.git_repo_url, str(cache_dir)])
        run(["git", "remote", "set-url", "origin", self.config.git_repo_url], cwd=cache_dir)
        run(["git", "fetch", "--depth", "1", "origin", self.config.git_branch], cwd=cache_dir)
        run(["git", "checkout", "--detach", sha], cwd=cache_dir)
        run(["git", "reset", "--hard", sha], cwd=cache_dir)
        run(["git", "clean", "-fdx"], cwd=cache_dir)
        return cache_dir


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def deployment_name(document: dict[str, Any], source: Path) -> str:
    name = ((document.get("metadata") or {}).get("name") or "").strip()
    if not name:
        raise ValueError(f"{source} is missing metadata.name")
    return name


def annotate_deployment(
    document: dict[str, Any],
    *,
    source_file: str,
    commit_sha: str,
    config: Config,
) -> dict[str, Any]:
    rendered = json.loads(json.dumps(document))
    metadata = rendered.setdefault("metadata", {})
    labels = metadata.setdefault("labels", {})
    labels[config.managed_label_key] = config.managed_label_value
    annotations = metadata.setdefault("annotations", {})
    annotations[f"{MANAGED_ANNOTATION_PREFIX}repo"] = config.git_repo_url
    annotations[f"{MANAGED_ANNOTATION_PREFIX}branch"] = config.git_branch
    annotations[f"{MANAGED_ANNOTATION_PREFIX}path"] = source_file
    annotations[f"{MANAGED_ANNOTATION_PREFIX}commit"] = commit_sha
    return rendered


def load_desired_deployments(repo_root: Path, config: Config, commit_sha: str) -> dict[str, dict[str, Any]]:
    desired_root = (repo_root / config.git_path).resolve()
    repo_root_resolved = repo_root.resolve()
    if not desired_root.exists():
        log("WARN", f"Git path does not exist: {config.git_path}")
        return {}
    if repo_root_resolved not in desired_root.parents and desired_root != repo_root_resolved:
        raise ValueError(f"GIT_PATH escapes repository root: {config.git_path}")

    desired: dict[str, dict[str, Any]] = {}
    for path in sorted(desired_root.rglob("*")):
        if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        with path.open("r", encoding="utf-8") as handle:
            documents = list(yaml.safe_load_all(handle))
        for document in documents:
            if not document:
                continue
            if not isinstance(document, dict):
                raise ValueError(f"{path} contains a non-object YAML document")
            if document.get("kind") != "Deployment":
                continue
            name = deployment_name(document, path)
            if name in desired:
                raise ValueError(f"duplicate VVP Deployment name in Git: {name}")
            rel_path = str(path.resolve().relative_to(repo_root_resolved))
            desired[name] = annotate_deployment(document, source_file=rel_path, commit_sha=commit_sha, config=config)
    return desired


class VvpClient:
    def __init__(self, config: Config):
        self.config = config

    def _ssl_context(self) -> ssl.SSLContext | None:
        if not self.config.vvp_insecure_tls:
            return None
        return ssl._create_unverified_context()

    def _auth_header(self) -> dict[str, str]:
        provider = os.environ.get("VVP_AUTH_PROVIDER", os.environ.get("FLINK_AUTH_PROVIDER", "none")).strip().lower().replace("_", "-")
        if provider in {"none", "no-auth", "disabled", "false"}:
            return {}
        if provider in {"bearer", "token", "static-bearer"}:
            token = os.environ.get("VVP_API_TOKEN") or os.environ.get("FLINK_API_TOKEN") or os.environ.get("AUTH_ACCESS_TOKEN")
            if not token:
                raise RuntimeError("VVP_API_TOKEN, FLINK_API_TOKEN, or AUTH_ACCESS_TOKEN is required")
            return {"Authorization": f"Bearer {token}"}
        if provider in {"keycloak", "keycloak-client-credentials", "oidc-keycloak"}:
            return {"Authorization": f"Bearer {self._keycloak_token()}"}
        literal_header = os.environ.get("VVP_AUTH_HEADER")
        if provider in {"custom", "header"} and literal_header:
            key, _, value = literal_header.partition(":")
            if not key or not value:
                raise RuntimeError("VVP_AUTH_HEADER must look like 'Header-Name: value'")
            return {key.strip(): value.strip()}
        raise RuntimeError(f"unsupported VVP_AUTH_PROVIDER: {provider}")

    def _keycloak_token(self) -> str:
        token_url = os.environ.get("KEYCLOAK_TOKEN_URL")
        if not token_url:
            base_url = os.environ.get("KEYCLOAK_BASE_URL", "").rstrip("/")
            realm = os.environ.get("KEYCLOAK_REALM", "")
            if not base_url or not realm:
                raise RuntimeError("KEYCLOAK_TOKEN_URL or KEYCLOAK_BASE_URL plus KEYCLOAK_REALM is required")
            token_url = f"{base_url}/realms/{realm}/protocol/openid-connect/token"
        client_id = os.environ.get("KEYCLOAK_CLIENT_ID")
        client_secret = os.environ.get("KEYCLOAK_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError("KEYCLOAK_CLIENT_ID and KEYCLOAK_CLIENT_SECRET are required")
        payload = {
            "grant_type": os.environ.get("KEYCLOAK_GRANT_TYPE", "client_credentials"),
            "client_id": client_id,
            "client_secret": client_secret,
        }
        if os.environ.get("KEYCLOAK_SCOPE"):
            payload["scope"] = os.environ["KEYCLOAK_SCOPE"]
        request = urllib.request.Request(
            token_url,
            data=urllib.parse.urlencode(payload).encode("utf-8"),
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.config.vvp_request_timeout, context=self._ssl_context()) as response:
            body = json.loads(response.read().decode("utf-8"))
        token = body.get("access_token")
        if not token:
            raise RuntimeError("Keycloak response did not include access_token")
        return token

    def request(self, method: str, path: str, body: str | None = None, content_type: str = "application/json") -> Any:
        url = f"{self.config.vvp_base_url}{path}"
        if self.config.dry_run:
            log("INFO", f"DRY RUN {method} {url}")
            if body:
                log("INFO", f"DRY RUN payload bytes: {len(body.encode('utf-8'))}")
            return {"items": []} if method == "GET" else {}
        headers = {"Accept": "application/json"}
        headers.update(self._auth_header())
        data = None
        if body is not None:
            data = body.encode("utf-8")
            headers["Content-Type"] = content_type
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.config.vvp_request_timeout, context=self._ssl_context()) as response:
                payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"VVP {method} {url} failed with HTTP {exc.code}: {detail}") from exc
        if not payload.strip():
            return {}
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return payload

    def deployments_path(self) -> str:
        return f"{self.config.vvp_api_prefix}/namespaces/{self.config.vvp_api_namespace}/deployments"

    def deployment_path(self, name: str) -> str:
        return f"{self.deployments_path()}/{urllib.parse.quote(name, safe='')}"

    def list_managed_deployments(self) -> dict[str, dict[str, Any]]:
        response = self.request("GET", self.deployments_path())
        items = response.get("items", []) if isinstance(response, dict) else []
        managed: dict[str, dict[str, Any]] = {}
        for item in items:
            metadata = item.get("metadata") or {}
            labels = metadata.get("labels") or {}
            if labels.get(self.config.managed_label_key) != self.config.managed_label_value:
                continue
            name = metadata.get("name")
            if name:
                managed[name] = item
        return managed

    def apply_deployment(self, name: str, manifest: dict[str, Any]) -> None:
        payload = yaml.safe_dump(manifest, sort_keys=False)
        self.request("PUT", self.deployment_path(name), body=payload, content_type="application/yaml")
        log("OK", f"applied VVP deployment {name}")

    def stop_then_delete_deployment(self, name: str) -> None:
        path = self.deployment_path(name)
        if self.config.delete_stop_first:
            patch = json.dumps({"spec": {"state": self.config.delete_stop_state}})
            self.request("PATCH", path, body=patch, content_type="application/merge-patch+json")
            log("OK", f"patched VVP deployment {name} to {self.config.delete_stop_state}")
        for attempt in range(1, self.config.delete_retry_attempts + 1):
            try:
                self.request("DELETE", path)
                log("OK", f"deleted VVP deployment {name}")
                return
            except RuntimeError as exc:
                if attempt == self.config.delete_retry_attempts:
                    raise
                log("WARN", f"delete attempt {attempt} failed for {name}: {exc}")
                time.sleep(self.config.delete_retry_seconds)


def reconcile(config: Config, commit_sha: str, repo_root: Path) -> dict[str, Any]:
    desired = load_desired_deployments(repo_root, config, commit_sha)
    client = VvpClient(config)
    current = client.list_managed_deployments()
    desired_names = set(desired)
    current_names = set(current)
    log("INFO", f"desired deployments: {sorted(desired_names)}")
    log("INFO", f"managed VVP deployments: {sorted(current_names)}")

    for name in sorted(desired_names):
        client.apply_deployment(name, desired[name])

    pruned: list[str] = []
    if config.prune_enabled:
        for name in sorted(current_names - desired_names):
            client.stop_then_delete_deployment(name)
            pruned.append(name)
    else:
        log("INFO", "prune disabled; removed Git deployments will not be deleted from VVP")

    return {
        "commit": commit_sha,
        "applied": sorted(desired_names),
        "pruned": pruned,
    }


def sync_once(config: Config) -> bool:
    repo = GitRepo(config)
    latest_sha = repo.latest_sha()
    state = load_state(config.state_file)
    last_synced = state.get("last_synced_sha")
    if latest_sha == last_synced and not config.force_sync:
        log("INFO", f"no Git change detected at {latest_sha}")
        return False
    repo_root = repo.checkout(latest_sha)
    result = reconcile(config, latest_sha, repo_root)
    if not config.dry_run:
        save_state(
            config.state_file,
            {
                "last_synced_sha": latest_sha,
                "last_sync_epoch_seconds": int(time.time()),
                "last_result": result,
            },
        )
    else:
        log("INFO", "dry run enabled; state file not updated")
    return True


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synchronize VVP deployments from a Git repository.")
    parser.add_argument("--once", action="store_true", help="run one sync check and exit")
    parser.add_argument("--dry-run", action="store_true", help="print VVP API actions without changing VVP")
    parser.add_argument("--force", action="store_true", help="sync even when the Git SHA did not change")
    parser.add_argument("--repo-url", help="Git repository URL")
    parser.add_argument("--branch", help="Git branch")
    parser.add_argument("--path", help="Path inside the repository containing VVP deployment YAML")
    parser.add_argument("--vvp-base-url", help="VVP API base URL")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config = Config.from_env(args)
    log("INFO", f"watching {config.git_repo_url} branch {config.git_branch} path {config.git_path}")
    while True:
        try:
            changed = sync_once(config)
            if changed:
                log("OK", "sync completed")
        except Exception as exc:
            log("ERROR", str(exc))
            if config.run_once:
                return 1
        if config.run_once:
            return 0
        time.sleep(config.sync_interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
