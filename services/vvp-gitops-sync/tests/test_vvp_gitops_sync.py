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
            delete_stop_first=True,
            delete_stop_state="CANCELLED",
            delete_retry_attempts=1,
            delete_retry_seconds=0,
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
                    },
                )()
                cfg = sync.Config.from_env(args)
                self.assertEqual(root / "state.json", cfg.state_file)
            finally:
                os.environ.clear()
                os.environ.update(old_env)


if __name__ == "__main__":
    unittest.main()
