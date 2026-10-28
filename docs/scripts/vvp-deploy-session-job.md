# vvp-deploy-session-job.sh

Creates or updates one VVP Deployment manifest that targets a VVP session cluster.

## Usage

```sh
./scripts/vvp-deploy-session-job.sh examples/manifests/vvp/simple-java-session-deployment.yaml
```

## Environment

- `VVP_API_BASE_URL`, `VVP_BASE_URL`, or `FLINK_BASE_URL`
- `VVP_API_NAMESPACE` or `FLINK_NAMESPACE`
- `VVP_API_TOKEN`: optional generated VVP bearer token; leave unset for unauthenticated access
- `${NAME}` values in the manifest are expanded from exported environment variables
- `VVP_WAIT=true` or `FLINK_WAIT=true` waits for `RUNNING`

## Behavior

The script sends the Deployment manifest to `PUT /deployments/<name>`. The manifest content decides which session cluster is used.
