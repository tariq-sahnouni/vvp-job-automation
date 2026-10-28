# vvp-patch-session-cluster-state.sh

Patches the desired state of one VVP SessionCluster.

## Usage

```sh
./scripts/vvp-patch-session-cluster-state.sh local-session RUNNING
./scripts/vvp-patch-session-cluster-state.sh local-session SUSPENDED
```

## Environment

- `VVP_API_BASE_URL`, `VVP_BASE_URL`, or `FLINK_BASE_URL`
- `VVP_API_NAMESPACE` or `FLINK_NAMESPACE`
- `VVP_API_TOKEN`: optional generated VVP bearer token; leave unset for unauthenticated access

## Behavior

The script sends a JSON merge patch to `spec.state` on `/sessionclusters/<name>`.
