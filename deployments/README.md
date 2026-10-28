# Desired VVP deployments

This directory is the desired state watched by `vvp-gitops-sync`.

- Store one VVP `Deployment` per YAML file.
- Use a unique `metadata.name` in the configured VVP namespace.
- Keep artifacts in a repository reachable by the Flink pods.
- Keep credentials in VVP or Kubernetes Secrets, outside these files.
- Use subdirectories when useful; the service scans recursively.
- A merged change creates or updates the deployment.
- Removing a file cancels and deletes the managed deployment when pruning is enabled.

`job.yaml.example` is ignored by the reconciler because its extension is
`.example`. Copy it to a `.yaml` file only after all placeholders are replaced.
