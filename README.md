# VVP Project Deployment Template

Use this repository as the starting point for a project team that deploys
Apache Flink jobs through Ververica Platform (VVP).

It gives the team three ways to work:

1. Store the desired VVP job definitions in `deployments/`.
2. Run the standalone scripts for manual operations and troubleshooting.
3. Build and run `vvp-gitops-sync` to reconcile `deployments/` with VVP.

The VVP platform itself is installed and configured by the platform Helm
repository. Each inventory repository points to one VVP installation, API
namespace and deployment target. It may use multiple VVP session clusters.
This repository owns project job definitions and their lifecycle.

Artifacts, checkpoints and savepoints use generic `s3://` URIs. The platform
Helm installation supplies the S3-compatible endpoint and credentials, so job
definitions remain independent of the storage vendor.

## Repository layout

| Path | Project team responsibility |
| --- | --- |
| `deployments/` | Desired VVP `Deployment` resources watched by the sync service |
| `platform/` | Deployment target and session cluster definitions applied with scripts |
| `config/` | Local environment and Kubernetes configuration templates |
| `scripts/` | Standalone VVP API operations |
| `services/vvp-gitops-sync/` | Source, container build and Kubernetes resources for automatic deployment |
| `docs/` | Operating documentation and one page per script |
| `examples/` | Reference definitions; these are not reconciled automatically |
| `dist/` | Optional exported service image for environments without a registry |

## Start a new project

1. Create a repository from this template.
2. Copy `config/vvp.env.example` to `.env` and set the VVP API values.
3. Run `make preflight` to verify VVP access.
4. Add deployment targets or session clusters under `platform/` if the platform
   team does not provide them.
5. Copy `deployments/job.yaml.example` to `deployments/<job-name>.yaml`, replace
   every placeholder, review it, and commit it.
6. Use `make deploy FILE=deployments/<job-name>.yaml` for a manual deployment.
7. Configure `services/vvp-gitops-sync/k8s/configmap.yaml` and the required
   Kubernetes Secrets, then run `make service-install` to enable reconciliation.

## Common commands

```sh
make help
make validate
make preflight
make list
make deploy FILE=deployments/payments-job.yaml
make wait NAME=payments-job STATE=RUNNING
make cancel NAME=payments-job
make delete NAME=payments-job

make service-test
make service-build
make service-export
make service-install
make service-logs
```

The sync service checks the configured Git branch and recursively reads YAML or
JSON files under `deployments/`. A committed deployment is created or updated
in VVP. Removing its file causes the service to cancel and delete it from VVP,
provided it carries the service ownership label.

The finite [PyFlink example](examples/apps/python/simple_pyflink_job.py) and its
[disabled deployment definition](deployments/examples/simple-python.yaml.example)
provide a small first deployment. The definition remains inactive until it is
copied or renamed with a `.yaml` extension.

Read [Getting Started](docs/getting-started.md) before enabling automatic
pruning. The complete documentation starts at [docs/README.md](docs/README.md).

The optional [PostgreSQL bootstrap Job](docs/platform/vvp-postgres-bootstrap.md)
creates database `vvp` and an isolated schema for the configured VVP instance
before the Helm installation or upgrade continues.
