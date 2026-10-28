import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import yaml

import vvp_gitops_sync as sync


class VvpGitopsSyncTest(unittest.TestCase):
    def config(self, root: Path) -> sync.Config:
        return sync.Config(
            git_repo_url="file:///tmp/repo.git",
            git_branch="main",
            git_path="deployments",
            git_cache_dir=root / "cache",
            state_file=root / "state.json",
            sync_interval_seconds=60,
            run_once=True,
            dry_run=True,
            force_sync=False,
            prune_enabled=True,
            managed_label_key="managed-by",
            managed_label_value="vvp-gitops-sync",
            vvp_base_url="http://vvp.example.com",
            vvp_api_namespace="default",
            vvp_api_prefix="/api/v1",
            vvp_request_timeout=60,
            vvp_insecure_tls=False,
            vvp_api_token=None,
            delete_stop_first=True,
            delete_stop_state="CANCELLED",
            delete_retry_attempts=1,
            delete_retry_seconds=0,
            inventory_variables={},
        )

    def test_load_desired_deployments_filters_and_annotates_vvp_deployments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deployments = root / "deployments"
            deployments.mkdir()
            (deployments / "app.yaml").write_text(
                """
apiVersion: v1
kind: Deployment
metadata:
  name: payments-job
spec:
  state: RUNNING
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: ignored
""",
                encoding="utf-8",
            )
            desired = sync.load_desired_deployments(root, self.config(root), "abc123")
            self.assertEqual(["payments-job"], sorted(desired))
            metadata = desired["payments-job"]["metadata"]
            self.assertEqual("vvp-gitops-sync", metadata["labels"]["managed-by"])
            self.assertEqual("abc123", metadata["annotations"]["vvp-gitops-sync/commit"])
            self.assertEqual("deployments/app.yaml", metadata["annotations"]["vvp-gitops-sync/path"])

    def test_duplicate_deployment_names_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deployments = root / "deployments"
            deployments.mkdir()
            for name in ("one.yaml", "two.yaml"):
                (deployments / name).write_text(
                    "apiVersion: v1\nkind: Deployment\nmetadata:\n  name: duplicate\n",
                    encoding="utf-8",
                )
            with self.assertRaises(ValueError):
                sync.load_desired_deployments(root, self.config(root), "abc123")

    def test_inventory_variables_are_expanded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deployments = root / "deployments"
            deployments.mkdir()
            (deployments / "app.yaml").write_text(
                "apiVersion: v1\nkind: Deployment\nmetadata:\n  name: app\n"
                "spec:\n  deploymentTargetName: ${VVP_DEPLOYMENT_TARGET_NAME}\n",
                encoding="utf-8",
            )
            old_value = os.environ.get("VVP_DEPLOYMENT_TARGET_NAME")
            try:
                os.environ["VVP_DEPLOYMENT_TARGET_NAME"] = "project-target"
                desired = sync.load_desired_deployments(root, self.config(root), "abc123")
            finally:
                if old_value is None:
                    os.environ.pop("VVP_DEPLOYMENT_TARGET_NAME", None)
                else:
                    os.environ["VVP_DEPLOYMENT_TARGET_NAME"] = old_value
            self.assertEqual("project-target", desired["app"]["spec"]["deploymentTargetName"])

    def test_unset_inventory_variable_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deployments = root / "deployments"
            deployments.mkdir()
            (deployments / "app.yaml").write_text(
                "apiVersion: v1\nkind: Deployment\nmetadata:\n  name: app\n"
                "spec:\n  deploymentTargetName: ${MISSING_TEST_TARGET}\n",
                encoding="utf-8",
            )
            os.environ.pop("MISSING_TEST_TARGET", None)
            with self.assertRaisesRegex(ValueError, "MISSING_TEST_TARGET"):
                sync.load_desired_deployments(root, self.config(root), "abc123")

    def test_git_repo_detects_latest_sha_from_local_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "source"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, stdout=subprocess.PIPE)
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(
                ["git", "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-m", "initial"],
                cwd=repo,
                check=True,
                stdout=subprocess.PIPE,
            )
            cfg = self.config(root)
            cfg = sync.Config(
                **{
                    **cfg.__dict__,
                    "git_repo_url": str(repo),
                    "git_cache_dir": root / "cache",
                }
            )
            git_repo = sync.GitRepo(cfg)
            sha = git_repo.latest_sha()
            checkout = git_repo.checkout(sha)
            self.assertTrue((checkout / "README.md").exists())

    def test_state_file_defaults_next_to_git_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_env = os.environ.copy()
            try:
                os.environ.clear()
                os.environ.update(
                    {
                        "GIT_REPO_URL": "file:///tmp/repo.git",
                        "GIT_CACHE_DIR": str(root / "cache"),
                        "VVP_API_BASE_URL": "http://vvp.example.com",
                    }
                )
                args = type(
                    "Args",
                    (),
                    {
                        "repo_url": None,
                        "vvp_base_url": None,
                        "branch": None,
                        "path": None,
                        "once": False,
                        "dry_run": False,
                        "force": False,
                        "config": None,
                    },
                )()
                cfg = sync.Config.from_env(args)
                self.assertEqual(root / "state.json", cfg.state_file)
            finally:
                os.environ.clear()
                os.environ.update(old_env)

    def test_config_map_file_supplies_all_service_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "config.yaml"
            config_path.write_text(
                """
git:
  repoUrl: https://git.example.internal/team/inventory.git
  branch: release
  path: desired
  cacheDir: /data/git
vvp:
  apiBaseUrl: https://vvp.example.internal
  apiNamespace: payments
  apiPrefix: /api/v1
  requestTimeoutSeconds: 45
  insecureTls: false
reconciliation:
  intervalSeconds: 30
  stateFile: /data/sync-state.json
  runOnce: false
  dryRun: true
  forceSync: false
  pruneEnabled: false
  managedLabel:
    key: managed-by
    value: project-sync
  delete:
    stopFirst: true
    stopState: CANCELLED
    retryAttempts: 4
    retrySeconds: 2
inventory:
  VVP_DEPLOYMENT_TARGET_NAME: payments-target
""",
                encoding="utf-8",
            )
            old_env = os.environ.copy()
            try:
                os.environ.clear()
                args = sync.parse_args(["--config", str(config_path)])
                cfg = sync.Config.from_env(args)
            finally:
                os.environ.clear()
                os.environ.update(old_env)
            self.assertEqual("release", cfg.git_branch)
            self.assertEqual(Path("/data/git"), cfg.git_cache_dir)
            self.assertEqual("payments", cfg.vvp_api_namespace)
            self.assertEqual(30, cfg.sync_interval_seconds)
            self.assertFalse(cfg.prune_enabled)
            self.assertEqual("payments-target", cfg.inventory_variables["VVP_DEPLOYMENT_TARGET_NAME"])

    def test_vvp_token_is_optional_and_used_as_bearer_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self.config(Path(tmp))
            self.assertNotIn("Authorization", sync.VvpClient(cfg)._headers())

            token_cfg = sync.Config(**{**cfg.__dict__, "vvp_api_token": "generated-vvp-token"})
            self.assertEqual(
                "Bearer generated-vvp-token",
                sync.VvpClient(token_cfg)._headers()["Authorization"],
            )

    def test_inventory_variables_can_come_from_config_map_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deployments = root / "deployments"
            deployments.mkdir()
            (deployments / "app.yaml").write_text(
                "apiVersion: v1\nkind: Deployment\nmetadata:\n  name: app\n"
                "spec:\n  deploymentTargetName: ${VVP_DEPLOYMENT_TARGET_NAME}\n",
                encoding="utf-8",
            )
            cfg = self.config(root)
            cfg = sync.Config(
                **{
                    **cfg.__dict__,
                    "inventory_variables": {"VVP_DEPLOYMENT_TARGET_NAME": "config-map-target"},
                }
            )
            desired = sync.load_desired_deployments(root, cfg, "abc123")
            self.assertEqual("config-map-target", desired["app"]["spec"]["deploymentTargetName"])


if __name__ == "__main__":
    unittest.main()
