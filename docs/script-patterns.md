# Script Usage Patterns

## Inventory configuration

One inventory repository connects to one VVP installation and one VVP API
namespace. Configure these once in `.env`:

```sh
export VVP_API_BASE_URL=https://vvp-api.example.internal
export VVP_API_NAMESPACE=project-namespace
export VVP_DEPLOYMENT_TARGET_NAME=project-target
export S3_ARTIFACT_URI_PREFIX=s3://project-flink-artifacts
export S3_CHECKPOINT_URI_PREFIX=s3://project-flink-checkpoints
export S3_SAVEPOINT_URI_PREFIX=s3://project-flink-savepoints
```

Definitions can use `${VVP_DEPLOYMENT_TARGET_NAME}` and
the three `${S3_*_URI_PREFIX}` variables. The deployment scripts and sync
service expand only the `${NAME}` form and fail when a referenced variable is
missing.

The URIs use the standard `s3://bucket/prefix` form and are independent of the
S3-compatible storage implementation. Configure the endpoint, region,
credentials and Flink S3 filesystem plugin centrally in the VVP deployment
target or platform-managed Flink configuration. Do not put storage credentials
in deployment definitions or this inventory repository.

## Validate before changing VVP

```sh
. ./.env
./scripts/vvp-validate-inventory.sh
make preflight
```

Use this pattern locally and in merge request pipelines.

## Application mode

Use application mode for job isolation. VVP creates a dedicated Flink cluster
for the deployment.

```sh
make deploy FILE=deployments/payments-job.yaml
make wait NAME=payments-job STATE=RUNNING
make list
```

The job definition contains `deploymentTargetName` and has no
`sessionClusterName`.

## Session mode

An inventory may reference several session clusters. Keep each session cluster
definition under `platform/session-clusters/` and each job's chosen
`sessionClusterName` in its deployment definition.

```sh
FLINK_ENV_FILE=.env ./scripts/vvp-upsert-session-cluster.sh \
  platform/session-clusters/analytics.yaml
FLINK_ENV_FILE=.env ./scripts/vvp-patch-session-cluster-state.sh analytics RUNNING
FLINK_ENV_FILE=.env ./scripts/vvp-wait-session-cluster.sh analytics RUNNING
make deploy-session FILE=deployments/analytics-job.yaml
```

## Pause and resume

Use state patches when a definition should remain in VVP:

```sh
FLINK_ENV_FILE=.env ./scripts/vvp-patch-deployment-state.sh payments-job SUSPENDED
FLINK_ENV_FILE=.env ./scripts/vvp-wait-deployment.sh payments-job SUSPENDED
FLINK_ENV_FILE=.env ./scripts/vvp-patch-deployment-state.sh payments-job RUNNING
```

## Remove a deployment

For a manual deployment, cancel it and then delete it:

```sh
make cancel NAME=payments-job
make wait NAME=payments-job STATE=CANCELLED
make delete NAME=payments-job
```

For a service-managed deployment, remove its YAML through a reviewed Git
change. With pruning enabled, the service performs the cancel and delete.

## Automatic reconciliation

Use scripts for preflight, diagnosis, controlled manual operations and recovery.
Use the sync service for the normal desired-state workflow:

```text
merge YAML -> service detects commit -> service applies VVP deployment
remove YAML -> service detects commit -> service cancels and deletes deployment
```

Do not manually maintain a service-managed deployment for long periods because
the next reconciliation reapplies the Git definition.

## VVP token authentication

All API scripts support the same two modes. Leave `VVP_API_TOKEN` unset to call
an API endpoint without authentication, or pass a generated VVP token through
the environment:

```sh
VVP_API_TOKEN="$GENERATED_VVP_TOKEN" ./scripts/vvp-preflight.sh
```

The scripts add `Authorization: Bearer <token>` when the variable is non-empty.
They never generate, print or persist the token.
