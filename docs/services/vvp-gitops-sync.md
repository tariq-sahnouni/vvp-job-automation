# VVP GitOps Sync Service

`vvp-gitops-sync` is a small Python service that runs beside VVP and reconciles
VVP `Deployment` definitions from Git.

It is intentionally not a full Argo CD replacement. It only handles one job:
keep VVP deployments in sync with the YAML files found in one Git repository
path.

## What It Does

The service loop is:

```text
1. Check the latest remote Git branch SHA with git ls-remote.
2. If the SHA is unchanged, do nothing.
3. If the SHA changed, fetch and checkout that commit in a local cache.
4. Read YAML and JSON files under GIT_PATH.
5. Keep only documents with kind: Deployment.
6. Add the managed label and source annotations.
7. PUT each desired deployment to the VVP API.
8. List current VVP deployments.
9. Delete VVP deployments removed from Git, but only if they carry the managed label.
10. Save the last synced commit SHA.
```

The lightweight `git ls-remote` check avoids running a full `git pull` on every
interval.

## Directory

```text
services/vvp-gitops-sync/
  app/vvp_gitops_sync.py       Python service
  Dockerfile                   Container image
  requirements.txt             Python dependency list
  k8s/deployment.yaml          Kubernetes Deployment example
  tests/                       Unit tests
```

## Git Repository Format

Create a repository path such as:

```text
deployments/
  payments-job.yaml
  risk-job.yaml
```

Each file can contain one or more YAML documents. The service only reconciles
documents where:

```yaml
kind: Deployment
```

Example:

```yaml
apiVersion: v1
kind: Deployment
metadata:
  name: simple-java-flink-job
spec:
  state: RUNNING
  deploymentTargetName: local-vvp-target
  template:
    spec:
      artifact:
        kind: JAR
        jarUri: http://minio.minio.svc.cluster.local:9000/flink-artifacts/simple-java-flink-job/simple-java-flink-job.jar
        entryClass: com.example.flinkautomation.SimpleFlinkJob
```

## Managed Label

The service adds this label by default:

```yaml
metadata:
  labels:
    managed-by: vvp-gitops-sync
```

Pruning only deletes VVP deployments that already have this label. This prevents
the service from deleting manually managed VVP deployments.

The service also adds annotations:

```yaml
metadata:
  annotations:
    vvp-gitops-sync/repo: <repo-url>
    vvp-gitops-sync/branch: <branch>
    vvp-gitops-sync/path: <source-file>
    vvp-gitops-sync/commit: <commit-sha>
```

## Required Environment

```sh
export GIT_REPO_URL=https://git.example.com/team/flink-deployments.git
export GIT_BRANCH=main
export GIT_PATH=deployments

export VVP_API_BASE_URL=http://vvp-ververica-platform.vvp.svc.cluster.local
export VVP_API_NAMESPACE=default
export VVP_AUTH_PROVIDER=none
```

## Important Environment Variables

- `GIT_REPO_URL`: Git repository URL. Required.
- `GIT_BRANCH`: branch to watch. Default: `main`.
- `GIT_PATH`: path inside the repository. Default: `deployments`.
- `GIT_CACHE_DIR`: local clone/cache directory. Default: `/data/repo`.
- `SYNC_INTERVAL_SECONDS`: polling interval. Default: `60`.
- `VVP_GITOPS_RUN_ONCE=true`: run one reconciliation and exit.
- `VVP_GITOPS_DRY_RUN=true`: print VVP API actions without modifying VVP.
- `VVP_GITOPS_FORCE_SYNC=true`: reconcile even when the commit SHA did not change.
- `VVP_GITOPS_PRUNE_ENABLED=false`: do not delete removed deployments.
- `VVP_GITOPS_STATE_FILE`: state file path. Default: sibling of
  `GIT_CACHE_DIR`, for example `/data/state.json` when `GIT_CACHE_DIR` is
  `/data/repo`.
- `VVP_GITOPS_MANAGED_LABEL_KEY`: default `managed-by`.
- `VVP_GITOPS_MANAGED_LABEL_VALUE`: default `vvp-gitops-sync`.

## AuthN

No-auth:

```sh
export VVP_AUTH_PROVIDER=none
```

Bearer token:

```sh
export VVP_AUTH_PROVIDER=bearer
export VVP_API_TOKEN=<token>
```

Keycloak client credentials:

```sh
export VVP_AUTH_PROVIDER=keycloak
export KEYCLOAK_BASE_URL=http://keycloak.keycloak.svc.cluster.local:8080
export KEYCLOAK_REALM=vvp
export KEYCLOAK_CLIENT_ID=vvp-gitops-sync
export KEYCLOAK_CLIENT_SECRET=<secret>
```

## Run Locally

Install dependencies in a virtual environment:

```sh
python3 -m venv /tmp/vvp-gitops-sync-venv
. /tmp/vvp-gitops-sync-venv/bin/activate
pip install -r services/vvp-gitops-sync/requirements.txt
```

Run one dry-run sync:

```sh
GIT_REPO_URL=file:///tmp/vvp-gitops-demo-repo \
GIT_BRANCH=main \
GIT_PATH=deployments \
VVP_API_BASE_URL=https://vvp-api.example.internal \
VVP_API_NAMESPACE=default \
VVP_AUTH_PROVIDER=none \
VVP_GITOPS_RUN_ONCE=true \
VVP_GITOPS_DRY_RUN=true \
python services/vvp-gitops-sync/app/vvp_gitops_sync.py
```

Run continuously:

```sh
GIT_REPO_URL=https://git.example.com/team/flink-deployments.git \
GIT_BRANCH=main \
GIT_PATH=deployments \
VVP_API_BASE_URL=https://vvp-api.example.internal \
VVP_API_NAMESPACE=default \
VVP_AUTH_PROVIDER=none \
python services/vvp-gitops-sync/app/vvp_gitops_sync.py
```

## Run In Kubernetes

Build and push an image:

```sh
docker build -t registry.example.com/platform/vvp-gitops-sync:0.1.0 \
  services/vvp-gitops-sync
docker push registry.example.com/platform/vvp-gitops-sync:0.1.0
```

Edit:

```text
services/vvp-gitops-sync/k8s/deployment.yaml
```

Set the image, Git repository URL, branch, path, and VVP API URL, then deploy:

```sh
kubectl apply -f services/vvp-gitops-sync/k8s/deployment.yaml
kubectl -n vvp logs deploy/vvp-gitops-sync -f
```

## Delete Behavior

If a deployment YAML is removed from Git and pruning is enabled, the service:

```text
1. lists current VVP deployments
2. keeps only deployments with managed-by=vvp-gitops-sync
3. patches removed deployments to CANCELLED
4. deletes them from VVP
```

This means a deployment is deleted only when both conditions are true:

```text
the YAML file is gone from Git
the live VVP deployment is owned by vvp-gitops-sync
```

## Testing

Run unit tests:

```sh
python -m unittest discover -s services/vvp-gitops-sync/tests
```

Run a dry-run against the VVP installation after replacing the URL and Git
repository with reachable values:

```sh
GIT_REPO_URL=file:///tmp/vvp-gitops-demo-repo \
GIT_BRANCH=main \
GIT_PATH=deployments \
VVP_API_BASE_URL=https://vvp-api.example.internal \
VVP_API_NAMESPACE=default \
VVP_AUTH_PROVIDER=none \
VVP_GITOPS_RUN_ONCE=true \
VVP_GITOPS_DRY_RUN=true \
python services/vvp-gitops-sync/app/vvp_gitops_sync.py
```
