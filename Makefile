SHELL := /bin/sh

ENV_FILE ?= ./.env
IMAGE ?= vvp-gitops-sync:0.1.0
PLATFORM ?= linux/amd64
NAMESPACE ?= vvp
FILE ?=
NAME ?=
STATE ?= RUNNING

.PHONY: help validate preflight list deploy deploy-session wait cancel delete service-test service-build service-export service-install service-delete service-logs postgres-bootstrap postgres-bootstrap-logs postgres-bootstrap-delete

help:
	@printf '%s\n' 'VVP project deployment template' '' \
	  '  make validate' \
	  '  make preflight' \
	  '  make list' \
	  '  make deploy FILE=deployments/job.yaml' \
	  '  make deploy-session FILE=deployments/session-job.yaml' \
	  '  make wait NAME=job-name STATE=RUNNING' \
	  '  make cancel NAME=job-name' \
	  '  make delete NAME=job-name' \
	  '  make service-test' \
	  '  make service-build [IMAGE=registry/project/vvp-gitops-sync:tag]' \
	  '  make service-export' \
	  '  make service-install [NAMESPACE=vvp]' \
	  '  make service-logs [NAMESPACE=vvp]' \
	  '  make service-delete [NAMESPACE=vvp]' \
	  '  make postgres-bootstrap [NAMESPACE=vvp]' \
	  '  make postgres-bootstrap-logs [NAMESPACE=vvp]' \
	  '  make postgres-bootstrap-delete [NAMESPACE=vvp]'

validate:
	@set -a; test ! -r "$(ENV_FILE)" || . "$(ENV_FILE)"; set +a; ./scripts/vvp-validate-inventory.sh deployments

preflight:
	FLINK_ENV_FILE="$(ENV_FILE)" ./scripts/vvp-preflight.sh

list:
	FLINK_ENV_FILE="$(ENV_FILE)" ./scripts/vvp-list-deployments.sh

deploy:
	@test -n "$(FILE)" || { echo 'FILE is required'; exit 2; }
	FLINK_ENV_FILE="$(ENV_FILE)" ./scripts/vvp-deploy-application.sh "$(FILE)"

deploy-session:
	@test -n "$(FILE)" || { echo 'FILE is required'; exit 2; }
	FLINK_ENV_FILE="$(ENV_FILE)" ./scripts/vvp-deploy-session-job.sh "$(FILE)"

wait:
	@test -n "$(NAME)" || { echo 'NAME is required'; exit 2; }
	FLINK_ENV_FILE="$(ENV_FILE)" ./scripts/vvp-wait-deployment.sh "$(NAME)" "$(STATE)"

cancel:
	@test -n "$(NAME)" || { echo 'NAME is required'; exit 2; }
	FLINK_ENV_FILE="$(ENV_FILE)" ./scripts/vvp-cancel-deployment.sh "$(NAME)"

delete:
	@test -n "$(NAME)" || { echo 'NAME is required'; exit 2; }
	FLINK_ENV_FILE="$(ENV_FILE)" VVP_CONFIRM_DELETE=true ./scripts/vvp-delete-deployment.sh "$(NAME)"

service-test:
	docker build --target test -t vvp-gitops-sync:test services/vvp-gitops-sync

service-build:
	docker build --platform "$(PLATFORM)" -t "$(IMAGE)" services/vvp-gitops-sync

service-export: service-build
	@mkdir -p dist
	docker save "$(IMAGE)" | gzip -9 > dist/vvp-gitops-sync-image.tar.gz
	shasum -a 256 dist/vvp-gitops-sync-image.tar.gz

service-install:
	kubectl -n "$(NAMESPACE)" apply -f services/vvp-gitops-sync/k8s/configmap.yaml
	kubectl -n "$(NAMESPACE)" apply -f services/vvp-gitops-sync/k8s/deployment.yaml
	kubectl -n "$(NAMESPACE)" rollout restart deployment/vvp-gitops-sync
	kubectl -n "$(NAMESPACE)" rollout status deployment/vvp-gitops-sync

service-delete:
	kubectl -n "$(NAMESPACE)" delete -f services/vvp-gitops-sync/k8s/deployment.yaml --ignore-not-found=true

service-logs:
	kubectl -n "$(NAMESPACE)" logs deployment/vvp-gitops-sync --follow

postgres-bootstrap:
	kubectl -n "$(NAMESPACE)" apply -f platform/postgres-bootstrap/configmap.yaml
	kubectl -n "$(NAMESPACE)" apply -f platform/postgres-bootstrap/script-configmap.yaml
	kubectl -n "$(NAMESPACE)" delete job/vvp-postgres-bootstrap --ignore-not-found=true
	kubectl -n "$(NAMESPACE)" apply -f platform/postgres-bootstrap/job.yaml
	@kubectl -n "$(NAMESPACE)" wait --for=condition=complete job/vvp-postgres-bootstrap --timeout=10m || { kubectl -n "$(NAMESPACE)" logs job/vvp-postgres-bootstrap; exit 1; }
	kubectl -n "$(NAMESPACE)" logs job/vvp-postgres-bootstrap

postgres-bootstrap-logs:
	kubectl -n "$(NAMESPACE)" logs job/vvp-postgres-bootstrap

postgres-bootstrap-delete:
	kubectl -n "$(NAMESPACE)" delete job/vvp-postgres-bootstrap --ignore-not-found=true
	kubectl -n "$(NAMESPACE)" delete configmap/vvp-postgres-bootstrap configmap/vvp-postgres-bootstrap-script --ignore-not-found=true
