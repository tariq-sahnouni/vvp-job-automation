# Configuration

`vvp.env.example` configures scripts run from a workstation or CI runner. Copy
it to the repository root as `.env`; `.env` is ignored by Git.

The three `S3_*_URI_PREFIX` values identify artifact, checkpoint and savepoint
locations using portable `s3://` URIs. The VVP installation owns the
S3-compatible endpoint, region, credentials and Flink filesystem plugin.

The automatic deployment service uses Kubernetes configuration under
`services/vvp-gitops-sync/k8s/`. Edit its ConfigMap for non-secret settings and
create the referenced Secrets through the approved secret management process.

Do not place bearer tokens, client secrets, Git passwords, object-storage
credentials or private keys in tracked files.
