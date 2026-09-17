# vvp-deploy-application.sh

Creates or updates one VVP Deployment manifest for application-style deployment.

## Usage

```sh
./scripts/vvp-deploy-application.sh examples/manifests/vvp/simple-java-deployment.yaml
./scripts/vvp-deploy-application.sh simple-java-flink-job examples/manifests/vvp/simple-java-deployment.yaml
```

## Environment

- `VVP_API_BASE_URL`, `VVP_BASE_URL`, or `FLINK_BASE_URL`
- `VVP_API_NAMESPACE` or `FLINK_NAMESPACE`
- `VVP_AUTH_PROVIDER` or `FLINK_AUTH_PROVIDER`
- `VVP_WAIT=true` or `FLINK_WAIT=true` waits for `RUNNING`

## Behavior

The script reads `metadata.name` unless a name is passed explicitly, sends `PUT /deployments/<name>`, and can wait for the deployment state.
