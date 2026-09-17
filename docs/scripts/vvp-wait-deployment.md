# vvp-wait-deployment.sh

Waits until one VVP Deployment reaches an expected state.

## Usage

```sh
./scripts/vvp-wait-deployment.sh simple-java-flink-job RUNNING 600
```

## Environment

- `VVP_API_BASE_URL`, `VVP_BASE_URL`, or `FLINK_BASE_URL`
- `VVP_API_NAMESPACE` or `FLINK_NAMESPACE`
- `VVP_AUTH_PROVIDER` or `FLINK_AUTH_PROVIDER`
- `VVP_POLL_SECONDS` or `FLINK_POLL_SECONDS`, default `10`

## Behavior

The script polls `/deployments/<name>` until a common state field matches the expected value.
