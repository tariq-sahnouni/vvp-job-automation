# Getting Started

## 1. Create the project repository

Create a repository from this template and keep `deployments/` as the path for
job definitions. The sync service uses that path by default.

## 2. Configure command-line access

```sh
cp config/vvp.env.example .env
```

Set the API URL, API namespace, single deployment target and the S3 artifact,
checkpoint and savepoint URI prefixes in `.env`. Do not store a VVP token in
this file. Pass `VVP_API_TOKEN` to a command only when the API requires it.

The VVP platform configuration must provide the S3-compatible endpoint, region,
credentials and Flink S3 filesystem plugin. Job definitions contain only
portable `s3://` URIs; do not store object-storage credentials in this
repository.

Verify access:

```sh
make validate
make preflight
make list
```

With a generated VVP token, run the API commands like this:

```sh
VVP_API_TOKEN="$GENERATED_VVP_TOKEN" make preflight
VVP_API_TOKEN="$GENERATED_VVP_TOKEN" make list
```

## 3. Add a job definition

```sh
cp deployments/job.yaml.example deployments/payments-job.yaml
```

Replace all placeholder values. The artifact S3 URI must be readable by the
Flink pods created by VVP. The deployment target must already exist.

For the included Python example, publish
`examples/apps/python/simple_pyflink_job.py` at the configured S3 artifact URI
and copy `deployments/examples/simple-python.yaml.example` to a `.yaml` file.

Test the definition manually before enabling reconciliation:

```sh
make deploy FILE=deployments/payments-job.yaml
make wait NAME=payments-job STATE=RUNNING
make cancel NAME=payments-job
make delete NAME=payments-job
```

## 4. Build and publish the service

Run the tests and build the target platform image:

```sh
make service-test
make service-build IMAGE=registry.example.internal/project/vvp-gitops-sync:0.1.0
docker push registry.example.internal/project/vvp-gitops-sync:0.1.0
```

Set the same image in `services/vvp-gitops-sync/k8s/deployment.yaml`.

For an environment where an image archive must be transferred through Git:

```sh
make service-export
```

## 5. Configure automatic deployment

Edit `services/vvp-gitops-sync/k8s/configmap.yaml` with this repository URL,
branch, VVP API URL, namespace and reconciliation settings. The ConfigMap is
mounted as `config.yaml`; the pod does not receive these settings through
`envFrom`. Create the `vvp-gitops-sync-git` Secret using `secret.example.yaml`
as a field reference when the Git repository is private.

Review `reconciliation.pruneEnabled`. When it is `true`, deleting a definition
from Git cancels and deletes the corresponding service-managed VVP deployment.

Install and observe the service:

```sh
make service-install NAMESPACE=vvp
make service-logs NAMESPACE=vvp
```

## 6. Daily workflow

Add or edit a YAML file under `deployments/`, review it in a pull request, and
merge it to the configured branch. The service detects the new commit and
applies all desired deployments. Remove a deployment file through the same
review process when the job should be removed from VVP.
