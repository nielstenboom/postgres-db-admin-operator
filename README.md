# postgres-db-admin-operator

## Development

Start the kind cluster and deploy postgres:
```bash
make init
```

Port-forward postgres locally:
```bash
make port-forward
```

Run the operator:
```bash
PG_HOST=localhost PG_USER=postgres PG_PASSWORD=devpassword uv run kopf run src/postgres_db_admin_operator/main.py --all-namespaces
```

Apply an example resource:
```bash
kubectl apply -f deploy/example.yaml
```

Run the tests (requires Docker):
```bash
uv run pytest  -v
```

Tear down the cluster:
```bash
make destroy
```
