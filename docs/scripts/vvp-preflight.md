# vvp-preflight.sh

Checks Ververica Platform API reachability and authorization.

## Usage

```sh
FLINK_ENV_FILE=examples/env/bnpp-vvp.env.example ./scripts/vvp-preflight.sh
```

With a generated VVP token:

```sh
VVP_API_TOKEN="$GENERATED_VVP_TOKEN" \
  FLINK_ENV_FILE=examples/env/bnpp-vvp.env.example \
  ./scripts/vvp-preflight.sh
```

## Environment

- `VVP_API_BASE_URL`, `VVP_BASE_URL`, or `FLINK_BASE_URL`
- `VVP_API_NAMESPACE` or `FLINK_NAMESPACE`
- `VVP_API_TOKEN`: optional generated VVP bearer token; leave unset for unauthenticated access
- `VVP_PREFLIGHT_STRICT=true` makes optional checks fatal

## Behavior

The script calls VVP deployment, session cluster, and deployment target list endpoints.
