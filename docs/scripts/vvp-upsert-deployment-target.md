# vvp-upsert-deployment-target.sh

Creates or updates one VVP DeploymentTarget.

## Usage

```sh
./scripts/vvp-upsert-deployment-target.sh examples/manifests/vvp/simple-deployment-target.yaml
./scripts/vvp-upsert-deployment-target.sh local-vvp-target examples/manifests/vvp/simple-deployment-target.yaml
```

## Environment

- `VVP_API_BASE_URL`, `VVP_BASE_URL`, or `FLINK_BASE_URL`
- `VVP_API_NAMESPACE` or `FLINK_NAMESPACE`
- `VVP_AUTH_PROVIDER` or `FLINK_AUTH_PROVIDER`

## Behavior

The script reads `metadata.name` unless a name is passed explicitly, then sends `PUT /api/v1/namespaces/<namespace>/deployment-targets/<name>`.
