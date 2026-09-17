# VVP GitOps Sync

Small Python service that watches one Git repository path and reconciles VVP
`Deployment` definitions with the VVP API.

The service is intentionally simple:

- checks the remote Git branch SHA with `git ls-remote`
- fetches only when the SHA changes
- reads YAML or JSON files under one repository path
- creates or updates VVP `Deployment` resources
- prunes VVP deployments removed from Git, but only when they carry the managed label

See `docs/services/vvp-gitops-sync.md` for the full operating guide.

