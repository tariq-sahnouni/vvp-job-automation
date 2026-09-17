# vvp-list-deployments.sh

Lists VVP Deployments in one VVP API namespace.

## Usage

```sh
./scripts/vvp-list-deployments.sh
```

## Environment

- `VVP_API_BASE_URL`, `VVP_BASE_URL`, or `FLINK_BASE_URL`
- `VVP_API_NAMESPACE` or `FLINK_NAMESPACE`
- `VVP_AUTH_PROVIDER` or `FLINK_AUTH_PROVIDER`

## Behavior

The script calls `GET /api/v1/namespaces/<namespace>/deployments`.
