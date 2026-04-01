# postgres-db-admin-operator

A very simple Kubernetes operator that can create PostgreSQL databases + roles as native Kubernetes resources. This operator can be used to automate manual Postgres operations. This project has been built for our company's [innoweek](https://blog.promaton.com/the-power-of-a-single-week-dedicated-to-innovation-585c2721de17) to learn about writing your own operator. Wanted to make it open-source in case it helps anyone!

Create a `PostgresDatabase` custom resource and the operator will:

- Create the database on your PostgreSQL server
- Create an admin role with full privileges
- Optionally create a read-only role with `SELECT`-only access
- Write connection credentials into a Kubernetes `Secret` in the same namespace as the resource

## Getting started

Create a secret with your PostgreSQL password:

```bash
kubectl create secret generic postgres-credentials \
  --from-literal=password=<your-postgres-password>
```

Create a `values.yaml`:

```yaml
postgres:
  host: <pg-host>
  user: <pg-user>
  password:
    existingSecret: postgres-credentials
```

Install the Helm chart:

```bash
helm upgrade --install postgres-db-admin-operator \
  oci://ghcr.io/nielstenboom/charts/postgres-db-admin-operator \
  -f values.yaml
```

### Create your first database

```yaml
apiVersion: postgresdbadminoperator.github.io/v1
kind: PostgresDatabase
metadata:
  name: my-app
  namespace: default
```

```bash
kubectl apply -f database.yaml
```

Once reconciled, the operator writes a Secret named `my-app-credentials` in the same namespace:

```console
$ kubectl get secret my-app-credentials -o yaml
apiVersion: v1
data:
  admin-database-url: postgresql://xxx
  admin-password: xxx
  admin-username: xxx
  dbname: my-app
  host: <pg-host>
  port: 5432
  readonly-database-url: postgresql://xxx
  readonly-password: xxx
  readonly-username: xxx
kind: Secret
metadata:
  creationTimestamp: "2026-04-01T09:15:05Z"
  name: my-app-credentials
  namespace: default
type: Opaque
```

The `readonly-*` keys are only present when `createReadOnlyUser: true`.

### Configuration

| Value | Description | Default |
|---|---|---|
| `postgres.host` | PostgreSQL host | `""` |
| `postgres.port` | PostgreSQL port | `5432` |
| `postgres.user` | PostgreSQL superuser | `""` |
| `postgres.password.existingSecret` | Name of the secret containing the password | `""` |
| `postgres.password.secretKey` | Key within the secret | `"password"` |
| `cleanupOnDelete` | Drop database and roles when the resource is deleted | `false` |

## Development

### Prerequisites

- Docker
- kind
- kubectl + helm
- [uv](https://github.com/astral-sh/uv)

### Make commands

| Command | Description |
|---|---|
| `make init` | Create a local kind cluster and deploy PostgreSQL into it |
| `make deploy` | Build the image, load it into kind, and install/upgrade the Helm chart |
| `make port-forward` | Port-forward PostgreSQL to `localhost:5432` |
| `make test` | Run the test suite (requires Docker) |
| `make destroy` | Tear down the kind cluster |

### Running the operator locally

```bash
make init
make port-forward &
PG_HOST=localhost PG_USER=postgres PG_PASSWORD=devpassword \
  uv run kopf run src/postgres_db_admin_operator/main.py --all-namespaces
```

