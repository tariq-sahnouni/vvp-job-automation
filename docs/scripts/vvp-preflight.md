# vvp-preflight.sh

Checks Ververica Platform API reachability and authorization.

## Usage

```sh
FLINK_ENV_FILE=examples/env/base.env.example:examples/env/auth-none.env.example:examples/env/vvp-application.env.example \
  ./scripts/vvp-preflight.sh
```

## Environment

- `VVP_API_BASE_URL`, `VVP_BASE_URL`, or `FLINK_BASE_URL`
- `VVP_API_NAMESPACE` or `FLINK_NAMESPACE`
- `VVP_AUTH_PROVIDER` or `FLINK_AUTH_PROVIDER`: `none`, `bearer`, `keycloak`, or `custom`
- `VVP_PREFLIGHT_STRICT=true` makes optional checks fatal

## Behavior

The script calls VVP deployment, session cluster, and deployment target list endpoints.
