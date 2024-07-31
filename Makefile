.DEFAULT_GOAL	:= help
SHELL			:= /bin/bash
MAKEFLAGS		+= --no-print-directory
MKFILE_DIR		:= $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
DOCKER_IMAGE	:= ghcr.io/tsmp-falcon-platform/ci-bundle-utils
DOCKER_NAME		:= bundleutils
BUNDLES_WORKSPACE ?= $(CWD)

.PHONY: compose/start-dev
compose/start-dev: ## Start the bundleutils container
compose/start-dev: compose/stop
	@docker compose run --rm builder
	@BUNDLEUTLS_IMAGE=bundleutils:dev docker compose up -d

.PHONY: compose/start
compose/start: ## Start the bundleutils container
	@docker compose up -d

.PHONY: compose/stop
compose/stop: ## Stop the bundleutils container
	@docker compose down --remove-orphans

.PHONY: compose/enter
compose/enter: ## Enter the bundleutils container
	@docker compose exec bundleutils bash

.PHONY: docker/create-volume
docker/create-volume: ## Create the bundleutils-cache volume
	@docker volume inspect bundleutils-cache > /dev/null 2>&1 || docker volume create bundleutils-cache

.PHONY: docker/start
docker/start: ## Start the bundleutils container
docker/start: docker/create-volume
	@docker pull $(DOCKER_IMAGE)
	@docker run \
		-d \
		-v bundleutils-cache:/opt/bundleutils/.cache \
		--name $(DOCKER_NAME) \
		--entrypoint bash \
		-e CASC_VALIDATION_LICENSE_KEY_B64=$(CASC_VALIDATION_LICENSE_KEY_B64) \
		-e CASC_VALIDATION_LICENSE_CERT_B64=$(CASC_VALIDATION_LICENSE_CERT_B64) \
		-v $(BUNDLES_WORKSPACE):/workspace \
		-w /workspace \
		-u $(id -u):$(id -g) \
		$(DOCKER_IMAGE) \
		-c "tail -f /dev/null"

.PHONY: docker/stop
docker/stop: ## Stop the bundleutils container
	@docker stop $(DOCKER_NAME)

.PHONY: docker/enter
docker/enter: ## Enter the bundleutils container
	@docker exec -it $(DOCKER_NAME) bash

.PHONY: docker/remove
docker/remove: ## Remove the bundleutils container
	@docker rm -f $(DOCKER_NAME)

.PHONY: help
help: ## Makefile Help Page
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[\/\%a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-21s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) 2>/dev/null

.PHONY: guard-%
guard-%:
	@if [[ "${${*}}" == "" ]]; then echo "Environment variable $* not set"; exit 1; fi
