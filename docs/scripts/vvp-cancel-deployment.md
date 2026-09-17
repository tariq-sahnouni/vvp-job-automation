# vvp-cancel-deployment.sh

Cancels one VVP Deployment.

## Usage

```sh
./scripts/vvp-cancel-deployment.sh simple-java-flink-job
```

## Environment

- `VVP_API_BASE_URL`, `VVP_BASE_URL`, or `FLINK_BASE_URL`
- `VVP_API_NAMESPACE` or `FLINK_NAMESPACE`
- `VVP_AUTH_PROVIDER` or `FLINK_AUTH_PROVIDER`

## Behavior

The script sends a JSON merge patch setting `spec.state` to `CANCELLED`.
