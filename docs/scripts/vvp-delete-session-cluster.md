# vvp-delete-session-cluster.sh

Deletes one VVP SessionCluster.

## Usage

```sh
VVP_CONFIRM_DELETE=true ./scripts/vvp-delete-session-cluster.sh local-session
```

## Environment

- `VVP_CONFIRM_DELETE=true` or `FLINK_CONFIRM_DELETE=true`
- `VVP_API_BASE_URL`, `VVP_BASE_URL`, or `FLINK_BASE_URL`
- `VVP_API_NAMESPACE` or `FLINK_NAMESPACE`
- `VVP_API_TOKEN`: optional generated VVP bearer token; leave unset for unauthenticated access

## Behavior

The script sends `DELETE /api/v1/namespaces/<namespace>/sessionclusters/<name>`.
