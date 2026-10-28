# VVP GitOps Sync

Small Python service that watches one Git repository path and reconciles VVP
`Deployment` definitions with the VVP API.

The service is intentionally simple:

- checks the remote Git branch SHA with `git ls-remote`
- fetches only when the SHA changes
- reads YAML or JSON files under one repository path
- creates or updates VVP `Deployment` resources
- prunes VVP deployments removed from Git, but only when they carry the managed label

## Build and test

From the repository root:

```sh
make service-test
make service-build IMAGE=registry.example.internal/project/vvp-gitops-sync:0.1.0
```

## Deploy

Set the project Git, VVP, reconciliation and inventory values in the embedded
`config.yaml` inside `k8s/configmap.yaml`. The pod mounts that file read-only.
For a private repository, create the `vvp-gitops-sync-git` Kubernetes Secret
using `k8s/secret.example.yaml` as a field reference, then set the published
image in `k8s/deployment.yaml`. If the VVP API requires authentication, also
create `vvp-gitops-sync-vvp-token` from `k8s/vvp-token-secret.example.yaml`.
The Secret is optional; omit it for API access without authentication.

```sh
kubectl -n vvp create secret generic vvp-gitops-sync-vvp-token \
  --from-literal=token="$GENERATED_VVP_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
```

```sh
make service-install NAMESPACE=vvp
make service-logs NAMESPACE=vvp
```

See `../../docs/services/vvp-gitops-sync.md` for the full operating guide.
