# vvp-validate-inventory.sh

Validates all active YAML and JSON deployment definitions before they are sent
to VVP. It checks YAML syntax, required names, duplicate names, resource kinds,
and `${VARIABLE}` references.

## Usage

```sh
. ./.env
./scripts/vvp-validate-inventory.sh
./scripts/vvp-validate-inventory.sh path/to/deployments
```

## Requirements

- Python 3
- PyYAML from `services/vvp-gitops-sync/requirements.txt`

Files ending in `.example` are intentionally ignored.
