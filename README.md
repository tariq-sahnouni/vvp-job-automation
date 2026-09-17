# VVP Marketplace

VVP deployment operations and Git reconciliation components for integration with
the BNP Paribas VVP Helm installation. This directory does not install VVP;
the existing platform Helm release remains the owner of VVP configuration.

## Layout

| Path | Purpose |
| --- | --- |
| `helm/` | Integration contract with the platform Helm release |
| `scripts/` | Self-contained VVP API commands, one action per script |
| `services/vvp-gitops-sync/` | Git-to-VVP deployment reconciliation service |
| `docs/` | [Documentation home](docs/README.md) and one usage page per VVP script |
| `docs/services/` | Git sync setup and behavior |
| `examples/` | Sample env files and VVP resource definitions; replace demo values before use |

## Integration order

1. Configure and install VVP using the platform Helm release. See [Helm integration](helm/README.md).
2. Set the VVP API URL, namespace and authentication in an environment file.
3. Run `scripts/vvp-preflight.sh` and then the needed deployment scripts. See [script index](docs/scripts/README.md).
4. For continuous reconciliation, build and deploy `services/vvp-gitops-sync/` and point it at a Git path containing VVP `Deployment` definitions. See [service guide](docs/services/vvp-gitops-sync.md).

The scripts and service both call the VVP API. They do not share a library or
require the Apache Flink scripts. Some copied scripts still accept legacy
`FLINK_*` environment aliases; prefer the `VVP_*` variables here.
