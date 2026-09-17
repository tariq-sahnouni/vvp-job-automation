# VVP script index

Set `FLINK_ENV_FILE` to a colon-separated list of env files (the variable name
is retained for compatibility), or put the VVP values in `.env` at the root of
this directory. Run all commands from this directory.

| Script | Documentation |
| --- | --- |
| `vvp-preflight.sh` | [Preflight](vvp-preflight.md) |
| `vvp-upsert-deployment-target.sh` | [Upsert deployment target](vvp-upsert-deployment-target.md) |
| `vvp-upsert-session-cluster.sh` | [Upsert session cluster](vvp-upsert-session-cluster.md) |
| `vvp-patch-session-cluster-state.sh` | [Patch session cluster state](vvp-patch-session-cluster-state.md) |
| `vvp-wait-session-cluster.sh` | [Wait for session cluster](vvp-wait-session-cluster.md) |
| `vvp-delete-session-cluster.sh` | [Delete session cluster](vvp-delete-session-cluster.md) |
| `vvp-deploy-application.sh` | [Deploy application](vvp-deploy-application.md) |
| `vvp-deploy-session-job.sh` | [Deploy session job](vvp-deploy-session-job.md) |
| `vvp-list-deployments.sh` | [List deployments](vvp-list-deployments.md) |
| `vvp-wait-deployment.sh` | [Wait for deployment](vvp-wait-deployment.md) |
| `vvp-patch-deployment-state.sh` | [Patch deployment state](vvp-patch-deployment-state.md) |
| `vvp-cancel-deployment.sh` | [Cancel deployment](vvp-cancel-deployment.md) |
| `vvp-delete-deployment.sh` | [Delete deployment](vvp-delete-deployment.md) |

Start with `examples/env/vvp-application.env.example` and one of the
`examples/env/auth-*.env.example` files. The example manifests reference demo
targets and artifacts, so update them for the installed environment.
