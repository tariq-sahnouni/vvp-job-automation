# VVP platform resources

Each inventory uses one deployment target, configured once as
`VVP_DEPLOYMENT_TARGET_NAME`. The platform team normally creates that target.
Keep `deployment-targets/` empty unless the project is explicitly responsible
for it.

An inventory may use multiple session clusters. Keep their definitions under
`session-clusters/` and apply them explicitly with the corresponding scripts.
The Git sync service only reconciles VVP `Deployment` resources under
`deployments/`.

```sh
FLINK_ENV_FILE=.env ./scripts/vvp-upsert-deployment-target.sh \
  platform/deployment-targets/project-target.yaml

FLINK_ENV_FILE=.env ./scripts/vvp-upsert-session-cluster.sh \
  platform/session-clusters/project-session.yaml
```

The platform team may provide these resources centrally. In that case, leave
the directories empty and reference the provided names from job definitions.

`postgres-bootstrap/` contains an optional Kubernetes startup Job that creates
database `vvp` when absent and prepares one schema per VVP instance. Read the
[PostgreSQL bootstrap guide](../docs/platform/vvp-postgres-bootstrap.md) before
adding it to the VVP Helm lifecycle.
