#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
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


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def load_config_file(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.is_file():
        raise SystemExit(f"[ERROR] configuration file is not readable: {config_path}")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"[ERROR] configuration file must contain a YAML object: {config_path}")
    return data


def nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


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
    vvp_api_token: str | None
    delete_stop_first: bool
    delete_stop_state: str
    delete_retry_attempts: int
    delete_retry_seconds: int
    inventory_variables: dict[str, str]

    @classmethod
    def from_env(cls, args: argparse.Namespace) -> "Config":
        config_path = args.config or os.environ.get("VVP_GITOPS_CONFIG")
        file_config = load_config_file(config_path)

        def value(env_name: str, *path: str, default: Any = None) -> Any:
            return os.environ.get(env_name, nested(file_config, *path, default=default))

        repo_url = args.repo_url or value("GIT_REPO_URL", "git", "repoUrl", default="")
        base_url = (
            args.vvp_base_url
            or os.environ.get("VVP_API_BASE_URL")
            or os.environ.get("VVP_BASE_URL")
            or os.environ.get("FLINK_BASE_URL")
            or nested(file_config, "vvp", "apiBaseUrl", default="")
            or ""
        )
        if not repo_url:
            raise SystemExit("[ERROR] git.repoUrl is required in the configuration file")
        if not base_url:
            raise SystemExit("[ERROR] vvp.apiBaseUrl is required in the configuration file")
        cache_dir = Path(value("GIT_CACHE_DIR", "git", "cacheDir", default="/data/repo"))
        configured_state_file = value("VVP_GITOPS_STATE_FILE", "reconciliation", "stateFile")
        state_file = Path(configured_state_file or cache_dir.parent / "state.json")
        inventory = nested(file_config, "inventory", default={})
        if not isinstance(inventory, dict):
            raise SystemExit("[ERROR] inventory configuration must be a YAML object")
        return cls(
            git_repo_url=repo_url,
            git_branch=args.branch or value("GIT_BRANCH", "git", "branch", default="main"),
            git_path=args.path or value("GIT_PATH", "git", "path", default="deployments"),
            git_cache_dir=cache_dir,
            state_file=state_file,
            sync_interval_seconds=int(value("SYNC_INTERVAL_SECONDS", "reconciliation", "intervalSeconds", default=60)),
            run_once=args.once or as_bool(value("VVP_GITOPS_RUN_ONCE", "reconciliation", "runOnce", default=False)),
            dry_run=args.dry_run or as_bool(value("VVP_GITOPS_DRY_RUN", "reconciliation", "dryRun", default=env_bool("VVP_DRY_RUN", False))),
            force_sync=args.force or as_bool(value("VVP_GITOPS_FORCE_SYNC", "reconciliation", "forceSync", default=False)),
            prune_enabled=as_bool(value("VVP_GITOPS_PRUNE_ENABLED", "reconciliation", "pruneEnabled", default=True)),
            managed_label_key=value("VVP_GITOPS_MANAGED_LABEL_KEY", "reconciliation", "managedLabel", "key", default="managed-by"),
            managed_label_value=value("VVP_GITOPS_MANAGED_LABEL_VALUE", "reconciliation", "managedLabel", "value", default="vvp-gitops-sync"),
            vvp_base_url=base_url.rstrip("/"),
            vvp_api_namespace=os.environ.get("VVP_API_NAMESPACE") or os.environ.get("FLINK_NAMESPACE") or os.environ.get("VVP_NAMESPACE") or nested(file_config, "vvp", "apiNamespace", default="default"),
            vvp_api_prefix=value("VVP_API_PREFIX", "vvp", "apiPrefix", default="/api/v1").rstrip("/"),
            vvp_request_timeout=int(value("VVP_REQUEST_TIMEOUT", "vvp", "requestTimeoutSeconds", default=os.environ.get("FLINK_REQUEST_TIMEOUT", "60"))),
            vvp_insecure_tls=as_bool(value("VVP_INSECURE_TLS", "vvp", "insecureTls", default=env_bool("FLINK_INSECURE_TLS", False))),
            vvp_api_token=os.environ.get("VVP_API_TOKEN", "").strip() or None,
            delete_stop_first=as_bool(value("VVP_GITOPS_DELETE_STOP_FIRST", "reconciliation", "delete", "stopFirst", default=True)),
            delete_stop_state=value("VVP_GITOPS_DELETE_STOP_STATE", "reconciliation", "delete", "stopState", default="CANCELLED"),
            delete_retry_attempts=int(value("VVP_GITOPS_DELETE_RETRY_ATTEMPTS", "reconciliation", "delete", "retryAttempts", default=12)),
            delete_retry_seconds=int(value("VVP_GITOPS_DELETE_RETRY_SECONDS", "reconciliation", "delete", "retrySeconds", default=5)),
            inventory_variables={str(key): str(item) for key, item in inventory.items()},
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


def expand_inventory_variables(text: str, source: Path, config: Config) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in os.environ:
            return os.environ[name]
        if name in config.inventory_variables:
            return config.inventory_variables[name]
        raise ValueError(f"{source} references unset inventory variable {name}")

    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", replace, text)


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
        rendered_text = expand_inventory_variables(path.read_text(encoding="utf-8"), path, config)
        documents = list(yaml.safe_load_all(rendered_text))
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

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.config.vvp_api_token:
            headers["Authorization"] = f"Bearer {self.config.vvp_api_token}"
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def request(self, method: str, path: str, body: str | None = None, content_type: str = "application/json") -> Any:
        url = f"{self.config.vvp_base_url}{path}"
        if self.config.dry_run:
            log("INFO", f"DRY RUN {method} {url}")
            if body:
                log("INFO", f"DRY RUN payload bytes: {len(body.encode('utf-8'))}")
            return {"items": []} if method == "GET" else {}
        data = None
        if body is not None:
            data = body.encode("utf-8")
        headers = self._headers(content_type if body is not None else None)
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
    parser.add_argument("--config", help="YAML configuration file mounted from a ConfigMap")
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
