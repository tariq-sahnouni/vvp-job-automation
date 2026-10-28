# vvp-delete-deployment.sh

Stops and deletes one VVP Deployment.

## Usage

```sh
VVP_CONFIRM_DELETE=true ./scripts/vvp-delete-deployment.sh simple-java-flink-job
```

## Environment

- `VVP_CONFIRM_DELETE=true` or `FLINK_CONFIRM_DELETE=true`
- `VVP_DELETE_STOP_FIRST=true`, default
- `VVP_DELETE_STOP_STATE=CANCELLED`, default
- `VVP_DELETE_RETRY_ATTEMPTS`, default `12`
- `VVP_DELETE_RETRY_SECONDS`, default `5`
- `VVP_API_BASE_URL`, `VVP_BASE_URL`, or `FLINK_BASE_URL`
- `VVP_API_NAMESPACE` or `FLINK_NAMESPACE`
- `VVP_API_TOKEN`: optional generated VVP bearer token; leave unset for unauthenticated access

## Behavior

The script optionally patches the deployment to `CANCELLED`, then retries `DELETE /deployments/<name>` until it succeeds or attempts are exhausted.
