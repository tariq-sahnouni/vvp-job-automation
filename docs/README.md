# VVP Marketplace Documentation

- [Getting started](getting-started.md): use this repository as a project team template.
- [Helm integration](../helm/README.md): connect the existing VVP installation to automation.
- [VVP scripts](scripts/README.md): deploy, inspect, change state and delete VVP resources.
- [Script usage patterns](script-patterns.md): application mode, session mode, lifecycle and reconciliation workflows.
- [GitLab CI usage](gitlab-ci.md): validation, image publishing and controlled VVP operations.
- [Git sync service](services/vvp-gitops-sync.md): reconcile VVP deployments from Git.
- [Configuration](../config/README.md): local and Kubernetes settings.
- [PostgreSQL bootstrap](platform/vvp-postgres-bootstrap.md): create database `vvp` and an isolated schema before VVP starts.
- [Examples](../examples/): reference definitions that are not reconciled.

Start with the getting started page, then run the preflight script before
deploying jobs or enabling automatic reconciliation.
