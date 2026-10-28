# vvp-patch-deployment-state.sh

Patches the desired state of one VVP Deployment.

## Usage

```sh
./scripts/vvp-patch-deployment-state.sh simple-java-flink-job SUSPENDED
./scripts/vvp-patch-deployment-state.sh simple-java-flink-job RUNNING
```

## Environment

- `VVP_API_BASE_URL`, `VVP_BASE_URL`, or `FLINK_BASE_URL`
- `VVP_API_NAMESPACE` or `FLINK_NAMESPACE`
- `VVP_API_TOKEN`: optional generated VVP bearer token; leave unset for unauthenticated access

## Behavior

The script sends a JSON merge patch to `spec.state` on `/deployments/<name>`.
