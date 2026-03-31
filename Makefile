CLUSTER_NAME := postgres-operator-dev
POSTGRES_NAMESPACE := postgres
POSTGRES_RELEASE := postgres
POSTGRES_PASSWORD := devpassword
IMAGE := postgres-db-admin-operator:dev

.PHONY: init destroy port-forward deploy test

init:
	kind create cluster --name $(CLUSTER_NAME)
	kubectx kind-$(CLUSTER_NAME)
	helm repo add bitnami https://charts.bitnami.com/bitnami
	helm repo update
	kubectl create namespace $(POSTGRES_NAMESPACE)
	helm install $(POSTGRES_RELEASE) bitnami/postgresql \
		--namespace $(POSTGRES_NAMESPACE) \
		--set auth.postgresPassword=$(POSTGRES_PASSWORD) \
		--wait
	kubectl apply -f deploy/crd.yaml


port-forward:
	kubectl port-forward -n $(POSTGRES_NAMESPACE) svc/$(POSTGRES_RELEASE)-postgresql 5432:5432

destroy:
	kind delete cluster --name $(CLUSTER_NAME)

deploy:
	docker build -t $(IMAGE) .
	kind load docker-image $(IMAGE) --name $(CLUSTER_NAME)
	helm upgrade --install postgres-db-admin-operator ./charts/postgres-db-admin-operator \
		--set postgres.host=$(POSTGRES_RELEASE)-postgresql.$(POSTGRES_NAMESPACE).svc.cluster.local \
		--set postgres.user=postgres \
		--set postgres.password=$(POSTGRES_PASSWORD)
	kubectl rollout restart deployment/postgres-db-admin-operator
	kubectl rollout status deployment/postgres-db-admin-operator

test:
	uv run pytest -v
