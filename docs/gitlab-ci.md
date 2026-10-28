# GitLab CI Usage

The root `.gitlab-ci.yml` demonstrates practical use of the inventory, scripts
and sync service.

## Pipeline jobs

| Job | Purpose |
| --- | --- |
| `validate-inventory` | Parse active definitions, expand variables and reject duplicates |
| `validate-postgres-bootstrap` | Parse the PostgreSQL bootstrap manifests and check the embedded shell script |
| `test-sync-service` | Run the sync service unit tests |
| `build-sync-service` | Build and push the service image on the default branch |
| `vvp-preflight` | Manually verify API access from a GitLab runner |
| `deploy-inventory` | Manually submit every active deployment definition |
| `cancel-deployment` | Manually cancel `DEPLOYMENT_NAME` |
| `delete-deployment` | Manually cancel and delete `DEPLOYMENT_NAME` |

## Required CI variables

Configure these at project or group level:

```text
VVP_API_BASE_URL
VVP_API_NAMESPACE
VVP_DEPLOYMENT_TARGET_NAME
S3_ARTIFACT_URI_PREFIX
S3_CHECKPOINT_URI_PREFIX
S3_SAVEPOINT_URI_PREFIX
```

If the VVP API requires authentication, also define `VVP_API_TOKEN` as a masked
and protected CI/CD variable containing a generated VVP token. Leave it absent
for VVP API access without authentication.

The S3 variables contain URIs only. Supply the S3-compatible endpoint and
credentials through the VVP installation's approved platform configuration and
secret management mechanism.

The GitLab container registry variables are supplied by GitLab when its
registry is enabled. The image build job requires a runner that supports Docker
in Docker or an equivalent approved container builder.

Use protected variables and protected environments for VVP production access.
Keep `deploy-inventory`, cancel and delete as manual jobs unless the project has
an approved automated promotion process.
