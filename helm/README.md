# Helm integration

The existing BNP Paribas Helm installation owns the VVP release, ingress,
license, storage, API service and platform credentials. Place its chart,
values and environment overlays here when integrating this directory into the
deployment repository. Do not install a second VVP release from the job
automation scripts.

The deployment automation needs these outputs from the Helm installation:

| Output | Consumer |
| --- | --- |
| Reachable VVP AppManager API URL | `VVP_API_BASE_URL` in scripts and sync service |
| VVP API namespace | `VVP_API_NAMESPACE` in scripts and sync service |
| S3-compatible blob-storage configuration | Artifact, checkpoint and savepoint `s3://` URIs used by deployments |
| Optional generated VVP API token | `VVP_API_TOKEN` for scripts and the sync service Secret |
| Kubernetes namespace and service DNS | `services/vvp-gitops-sync/k8s/deployment.yaml` |
| Image registry and pull credentials | Git sync service image in the Kubernetes workload |

Use the actual API URL exposed by the installed release, which may differ from
the browser UI URL. The scripts call `/api/v1/namespaces/...` by default. Run
`scripts/vvp-preflight.sh` after Helm deployment to verify access.

Keep credentials in the platform's secret mechanism. The sample env files and
Kubernetes manifest contain placeholders and are not production values.

Include the resources under `platform/postgres-bootstrap/` in the VVP Helm
release when PostgreSQL must be prepared automatically. They run as
`pre-install` and `pre-upgrade` hooks, create database `vvp` when absent and
prepare the schema derived from the VVP instance name. The PostgreSQL admin
Secret must exist before Helm starts. See
`docs/platform/vvp-postgres-bootstrap.md`.

Configure the VVP universal blob-storage base URI, S3-compatible endpoint,
region and credentials in the Helm installation. Project definitions should
reference only `s3://` locations and must not repeat endpoint or credential
configuration.
