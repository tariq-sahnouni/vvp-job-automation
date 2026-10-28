# VVP PostgreSQL Bootstrap Job

## Purpose

The PostgreSQL bootstrap Job prepares one shared database for a VVP instance
before VVP starts. It is safe to run repeatedly.

The resulting structure is:

```text
Database: vvp
Schema:   <normalized VVP instance name>
Owner:    <VVP runtime PostgreSQL role>
```

For example, `VVP-PROD-France` becomes schema `vvp_prod_france`.

## Resources

| File | Purpose |
| --- | --- |
| `platform/postgres-bootstrap/configmap.yaml` | PostgreSQL endpoint and VVP instance configuration |
| `platform/postgres-bootstrap/script-configmap.yaml` | Idempotent bootstrap implementation |
| `platform/postgres-bootstrap/secret.example.yaml` | Required admin-password Secret format |
| `platform/postgres-bootstrap/job.yaml` | Kubernetes Job using the PostgreSQL client image |

## Behavior

The Job:

1. waits for PostgreSQL connectivity;
2. normalizes `VVP_NAME` into a PostgreSQL-safe schema name;
3. verifies that `VVP_POSTGRES_ROLE` already exists;
4. creates database `vvp` if it does not exist;
5. creates the instance schema if it does not exist;
6. makes the VVP runtime role the schema owner;
7. grants database and schema privileges;
8. configures that role's search path for database `vvp`;
9. attempts a create, insert, update, delete and drop smoke test as the runtime role.

The Job never creates PostgreSQL users, roles or passwords.

## Configure

Edit the non-secret values in `configmap.yaml`:

| Key | Meaning |
| --- | --- |
| `POSTGRES_HOST` | PostgreSQL DNS name or address reachable from Kubernetes |
| `POSTGRES_PORT` | PostgreSQL port, normally `5432` |
| `POSTGRES_MAINTENANCE_DATABASE` | Existing database used to create `vvp`, normally `postgres` |
| `POSTGRES_ADMIN_USER` | Administrative PostgreSQL username |
| `POSTGRES_SSLMODE` | libpq SSL mode, such as `require` or `verify-full` |
| `VVP_NAME` | VVP marketplace instance name; used to derive the schema |
| `VVP_POSTGRES_ROLE` | Existing role used by this VVP instance at runtime |

Replace `postgres:16-alpine` in `job.yaml` with the approved internal image
registry path when public image pulls are not allowed.

## Secret

Create Secret `vvp-postgres-bootstrap` through the approved secret-management
process with this key:

```text
POSTGRES_ADMIN_PASSWORD
```

Do not commit a real password or put it in the ConfigMap. The Secret must exist
before a Helm installation starts because this is a pre-install Job.

## Required Permissions

The admin account needs:

| Operation | Required permission |
| --- | --- |
| Connect to the maintenance database | `CONNECT` |
| Create database `vvp` | `CREATEDB` or managed-service equivalent |
| Inspect the runtime role | access to `pg_roles` |
| Create and own schemas | database administration or ownership rights |
| Grant privileges and alter role settings | suitable admin rights |
| Run the full smoke test | permission to `SET ROLE` to the VVP runtime role |

The VVP runtime role must be provisioned before the Job runs. If the database
already exists, the Job does not change its owner. Each VVP instance can use a
different runtime role and schema inside the same `vvp` database.

## Helm Startup

The ConfigMaps use hook weight `-20`; the Job uses weight `-10`. With the files
included in the VVP Helm release, Helm creates the configuration first and then
waits for the Job to complete before continuing the VVP install or upgrade.

The parent Helm chart should template `VVP_NAME`, connection settings, resource
names and the approved PostgreSQL image from its values. Keep the Secret under
the platform's external secret mechanism.

## Manual Test

After creating the Secret, run:

```sh
make postgres-bootstrap NAMESPACE=vvp
```

Observe a previous or current execution with:

```sh
make postgres-bootstrap-logs NAMESPACE=vvp
```

Remove only the Job and non-secret bootstrap ConfigMaps with:

```sh
make postgres-bootstrap-delete NAMESPACE=vvp
```

The deletion command does not remove database objects or the password Secret.

## Verify

The successful Job log ends with:

```text
[OK] PostgreSQL bootstrap complete: database=vvp schema=<schema> role=<role>
```

The corresponding VVP database configuration must use:

```text
Database: vvp
User:     value of VVP_POSTGRES_ROLE
Schema:   normalized VVP_NAME, when VVP requests a schema explicitly
```

When VVP does not expose a schema field, the database-specific role search path
selects the instance schema automatically.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Job cannot connect | DNS, network policy, firewall, TLS mode and admin Secret |
| Runtime role missing | Provision the role through the approved identity process |
| Database creation denied | Admin account needs `CREATEDB` or equivalent |
| Schema preparation denied | Database ownership and admin grant permissions |
| Smoke test warning | Admin account may not be allowed to `SET ROLE`; test with runtime credentials |
| Two names select one schema | Choose VVP names that remain unique after normalization |
