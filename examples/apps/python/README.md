# Simple PyFlink application

`simple_pyflink_job.py` emits one numbered message per second for five minutes.
It is long enough to exercise deploy, wait, list, cancel and delete operations,
then finishes naturally.

Publish the file at:

```text
${S3_ARTIFACT_URI_PREFIX}/simple_pyflink_job.py
```

Then activate its definition:

```sh
cp deployments/examples/simple-python.yaml.example \
  deployments/simple-python.yaml
make validate
make deploy FILE=deployments/simple-python.yaml
make wait NAME=simple-python-example STATE=RUNNING
```

The selected VVP Flink image must include PyFlink. The standard VVP Python
artifact image used by the local Colima environment satisfies this requirement.
