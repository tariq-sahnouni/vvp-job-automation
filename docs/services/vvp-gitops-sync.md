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

The template already provides the watched path:

```text
deployments/
  job.yaml.example
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
  deploymentTargetName: ${VVP_DEPLOYMENT_TARGET_NAME}
  template:
    spec:
      artifact:
        kind: JAR
        jarUri: ${S3_ARTIFACT_URI_PREFIX}/simple-java-flink-job.jar
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

## Configuration

In Kubernetes, all non-secret service configuration is stored in
`k8s/configmap.yaml` under one `config.yaml` key. The pod mounts it read-only at
`/etc/vvp-gitops-sync/config.yaml` and starts the service with:

```sh
python /app/vvp_gitops_sync.py --config /etc/vvp-gitops-sync/config.yaml
```

The file has four sections:

| Section | Purpose |
| --- | --- |
| `git` | Repository URL, branch, watched path and local cache path |
| `vvp` | VVP API URL, namespace, prefix, timeout and TLS behavior |
| `reconciliation` | Polling, state, dry-run, pruning, ownership label and deletion behavior |
| `inventory` | Values used to expand `${NAME}` placeholders in deployment definitions |

The default ConfigMap defines only `VVP_DEPLOYMENT_TARGET_NAME`. Add
`S3_ARTIFACT_URI_PREFIX`, `S3_CHECKPOINT_URI_PREFIX` and
`S3_SAVEPOINT_URI_PREFIX` under `inventory` only when S3-compatible storage is
available and an active definition references them.

Environment variables remain supported for local compatibility and override
file values, but the Kubernetes workload does not use `envFrom`. Command-line
arguments override both. An unset inventory variable stops reconciliation and
leaves the previous desired state untouched.

The service reads the file at startup. `make service-install` restarts the
Deployment after applying the ConfigMap so changes take effect immediately.

Use standard `s3://bucket/prefix` values. Configure the S3-compatible endpoint,
region and credentials through VVP platform configuration and approved secrets;
the sync service does not need object-storage credentials.

## VVP token authentication

The service supports authenticated and unauthenticated VVP API access. When
`VVP_API_TOKEN` is non-empty, it sends `Authorization: Bearer <token>`. When the
variable is absent or empty, it sends no authentication header.

For Kubernetes, create `vvp-gitops-sync-vvp-token` from
`services/vvp-gitops-sync/k8s/vvp-token-secret.example.yaml` only when a token
is required. The Deployment references this Secret as optional, so the same
manifest works without it. Do not put the token in the ConfigMap.

Inject or rotate a generated token without writing it to a tracked file:

```sh
kubectl -n vvp create secret generic vvp-gitops-sync-vvp-token \
  --from-literal=token="$GENERATED_VVP_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n vvp rollout restart deployment/vvp-gitops-sync
```

For access without authentication, omit the Secret or delete it and restart
the Deployment.

For local execution, pass the token only to the process that needs it:

```sh
VVP_API_TOKEN="$GENERATED_VVP_TOKEN" \
  python services/vvp-gitops-sync/app/vvp_gitops_sync.py \
  --config /tmp/vvp-gitops-sync.yaml --once
```

## Run Locally

Install dependencies in a virtual environment:

```sh
python3 -m venv /tmp/vvp-gitops-sync-venv
. /tmp/vvp-gitops-sync-venv/bin/activate
pip install -r services/vvp-gitops-sync/requirements.txt
```

Extract the embedded configuration for local use, then edit its URLs and paths:

```sh
kubectl create --dry-run=client -f services/vvp-gitops-sync/k8s/configmap.yaml \
  -o jsonpath='{.data.config\.yaml}' > /tmp/vvp-gitops-sync.yaml
```

Run one dry-run reconciliation:

```sh
python services/vvp-gitops-sync/app/vvp_gitops_sync.py \
  --config /tmp/vvp-gitops-sync.yaml --once --dry-run --force
```

Run continuously:

```sh
python services/vvp-gitops-sync/app/vvp_gitops_sync.py \
  --config /tmp/vvp-gitops-sync.yaml
```

## Run In Kubernetes

Build and push an image:

```sh
docker build -t registry.example.com/platform/vvp-gitops-sync:0.1.0 \
  services/vvp-gitops-sync
docker push registry.example.com/platform/vvp-gitops-sync:0.1.0
```

Edit the non-secret configuration and image:

```text
services/vvp-gitops-sync/k8s/configmap.yaml
services/vvp-gitops-sync/k8s/deployment.yaml
```

For a private HTTPS Git repository, create the `vvp-gitops-sync-git` Secret
through the approved secret management process. It provides a read-only
`.netrc`; credentials never belong in the ConfigMap or repository URL.
`services/vvp-gitops-sync/k8s/secret.example.yaml` documents the expected
format. Then deploy:

```sh
make service-install NAMESPACE=vvp
make service-logs NAMESPACE=vvp
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
python services/vvp-gitops-sync/app/vvp_gitops_sync.py \
  --config /tmp/vvp-gitops-sync.yaml --once --dry-run --force
```
