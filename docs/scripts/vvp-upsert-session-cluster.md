# vvp-upsert-session-cluster.sh

Creates or updates one VVP SessionCluster.

## Usage

```sh
./scripts/vvp-upsert-session-cluster.sh examples/manifests/vvp/simple-session-cluster.yaml
./scripts/vvp-upsert-session-cluster.sh local-session examples/manifests/vvp/simple-session-cluster.yaml
```

## Environment

- `VVP_API_BASE_URL`, `VVP_BASE_URL`, or `FLINK_BASE_URL`
- `VVP_API_NAMESPACE` or `FLINK_NAMESPACE`
- `VVP_API_TOKEN`: optional generated VVP bearer token; leave unset for unauthenticated access
- `${NAME}` values in the manifest are expanded from exported environment variables

## Behavior

The script reads `metadata.name` unless a name is passed explicitly, then sends `PUT /api/v1/namespaces/<namespace>/sessionclusters/<name>`.
