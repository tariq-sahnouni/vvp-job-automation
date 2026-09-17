# vvp-wait-session-cluster.sh

Waits until one VVP SessionCluster reaches an expected state.

## Usage

```sh
./scripts/vvp-wait-session-cluster.sh local-session RUNNING 600
```

## Environment

- `VVP_API_BASE_URL`, `VVP_BASE_URL`, or `FLINK_BASE_URL`
- `VVP_API_NAMESPACE` or `FLINK_NAMESPACE`
- `VVP_AUTH_PROVIDER` or `FLINK_AUTH_PROVIDER`
- `VVP_POLL_SECONDS` or `FLINK_POLL_SECONDS`, default `10`

## Behavior

The script polls `/sessionclusters/<name>` until a common state field matches the expected value.
