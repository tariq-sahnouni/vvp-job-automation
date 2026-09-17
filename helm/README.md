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
| Authentication mode and credentials | `VVP_AUTH_PROVIDER` and provider-specific variables |
| Kubernetes namespace and service DNS | `services/vvp-gitops-sync/k8s/deployment.yaml` |
| Image registry and pull credentials | Git sync service image in the Kubernetes workload |

Use the actual API URL exposed by the installed release, which may differ from
the browser UI URL. The scripts call `/api/v1/namespaces/...` by default. Run
`scripts/vvp-preflight.sh` after Helm deployment to verify access.

Keep credentials in the platform's secret mechanism. The sample env files and
Kubernetes manifest contain placeholders and are not production values.
