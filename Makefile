CLUSTER_NAME := postgres-operator-dev
POSTGRES_NAMESPACE := postgres
POSTGRES_RELEASE := postgres
POSTGRES_PASSWORD := devpassword
POSTGRES_CHART_VERSION := 18.5.14
IMAGE := postgres-db-admin-operator:dev
SECRET_NAME := postgres-credentials

.PHONY: init destroy port-forward deploy test

init:
	kind create cluster --name $(CLUSTER_NAME)
	kubectl config use-context kind-$(CLUSTER_NAME)
	helm repo add bitnami https://charts.bitnami.com/bitnami
	helm repo update
	kubectl create namespace $(POSTGRES_NAMESPACE)
	helm install $(POSTGRES_RELEASE) bitnami/postgresql \
		--namespace $(POSTGRES_NAMESPACE) \
		--version $(POSTGRES_CHART_VERSION) \
		-f postgres-dev-values.yaml \
		--wait

deploy:
	docker build -t $(IMAGE) .
	kind load docker-image $(IMAGE) --name $(CLUSTER_NAME)
	kubectl create secret generic $(SECRET_NAME) \
		--from-literal=password=$(POSTGRES_PASSWORD) \
		--dry-run=client -o yaml | kubectl apply -f -
	helm upgrade --install postgres-db-admin-operator ./charts/postgres-db-admin-operator \
		--set image.repository=postgres-db-admin-operator \
		--set image.tag=dev \
		--set image.pullPolicy=Never \
		--set postgres.host=$(POSTGRES_RELEASE)-postgresql.$(POSTGRES_NAMESPACE).svc.cluster.local \
		--set postgres.user=postgres \
		--set postgres.password.existingSecret=$(SECRET_NAME)
	kubectl rollout restart deployment/postgres-db-admin-operator
	kubectl rollout status deployment/postgres-db-admin-operator

port-forward:
	kubectl port-forward -n $(POSTGRES_NAMESPACE) svc/$(POSTGRES_RELEASE)-postgresql 5432:5432

destroy:
	kind delete cluster --name $(CLUSTER_NAME)

test:
	uv run pytest -v
