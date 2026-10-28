# VVP GitOps Sync Image

`vvp-gitops-sync-0.1.0-linux-amd64.tar.gz` is a Docker image export for
`linux/amd64`. It contains the `vvp-gitops-sync:0.1.0` image and can be stored
in Git (about 27 MB compressed).

From the `vvp-marketplace` directory, verify and import it with:

```sh
shasum -a 256 dist/vvp-gitops-sync-0.1.0-linux-amd64.tar.gz
gzip -dc dist/vvp-gitops-sync-0.1.0-linux-amd64.tar.gz | docker load
docker run --rm --platform linux/amd64 vvp-gitops-sync:0.1.0 --help
```

Expected SHA-256:

```text
18e4e9e410105b2272d04a6f3676cfa3e72f91c598891639b6577d56ba2be221
```

To share it through the repository:

```sh
git add services/vvp-gitops-sync/Dockerfile dist/
git commit -m "Add exportable VVP GitOps sync image"
git push
```

To deploy it to a Kubernetes cluster, load the archive into a container
registry accessible by the cluster, push it with the desired registry tag, and
set that tag in `services/vvp-gitops-sync/k8s/deployment.yaml`. Loading the
archive into a laptop's Docker daemon alone does not make it available to
remote Kubernetes nodes.
