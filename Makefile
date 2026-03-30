CLUSTER_NAME := postgres-operator-dev
POSTGRES_NAMESPACE := postgres
POSTGRES_RELEASE := postgres
POSTGRES_PASSWORD := devpassword

.PHONY: init destroy apply-crd port-forward

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
