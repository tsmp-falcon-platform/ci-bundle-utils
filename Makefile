.DEFAULT_GOAL      := help
SHELL              := /usr/bin/env bash
MAKEFLAGS          += --no-print-directory
MKFILE_DIR         := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
DOCKER_IMAGE       ?= ghcr.io/tsmp-falcon-platform/ci-bundle-utils
DOCKER_NAME        ?= bundleutils
BUNDLES_WORKSPACE  ?= $(MKFILE_DIR)
PYTHON_CMD         ?= python3

.PHONY: setup
setup: ## Setup virtualenv (optional PYTHON_CMD=python3.xx)
	$(PYTHON_CMD) -m venv .venv
	@echo -e "\n**NOW RUN** >>>>> source .venv/bin/activate"

.PHONY: install
install: ## Install the bundleutils package
	cd bundleutilspkg && \
	pip install --upgrade pip pip-tools && \
	pip install -r requirements-dev.lock.txt && \
	pip install -e "."

.PHONY: test
test: ## Run the pytest suite
	cd bundleutilspkg && \
	pytest -v

.PHONY: test/%
test/%: ## Run the pytest suite tests containing 'test/<string>'
	cd bundleutilspkg && \
	pytest -v -k $*

.PHONY: lock-files
lock-files: ## Install the bundleutils package
	cd bundleutilspkg && \
	pip-compile --strip-extras --output-file=requirements.lock.txt pyproject.toml && \
	pip-compile --extra dev pyproject.toml --strip-extras --output-file=requirements-dev.lock.txt

.PHONY: pyinstaller
pyinstaller: ## Build the bundleutils package
	cd bundleutilspkg && \
	pyinstaller --noconfirm --clean --onedir \
	--add-data "src/bundleutilspkg/data/configs:data/configs" \
	--copy-metadata bundleutilspkg \
	src/bundleutilspkg/bundleutils.py

.PHONY: marp
marp: ## Build the Marp presentation
	@docker run \
		-v $$(pwd):/home/marp/app \
		-e MARP_USER="$$(id -u):$$(id -g)" \
		-e LANG=$$LANG \
		marpteam/marp-cli docs/presentations/intro.md
	@browse docs/presentations/intro.html

.PHONY: compose/start-dev
compose/start-dev: ## Start the bundleutils container
compose/start-dev: compose/stop
	@docker compose run --rm --build builder
	@BUNDLEUTILS_IMAGE=bundleutils:dev docker compose up -d

.PHONY: compose/start
compose/start: ## Start the bundleutils container
	@docker compose pull
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

.PHONY: docker/build-dev
docker/build-dev: ## Build the bundleutils:dev image
docker/build-dev:
	@docker buildx build -t bundleutils:dev .

.PHONY: docker/start-dev
docker/start-dev: ## Start the bundleutils:dev container
docker/start-dev: docker/remove docker/build-dev
	DOCKER_IMAGE=bundleutils:dev $(MAKE) docker/start

.PHONY: docker/start
docker/start: ## Start the bundleutils container
docker/start: docker/create-volume
	@docker run \
		-d \
		-v bundleutils-cache:/opt/bundleutils/.cache \
		--name $(DOCKER_NAME) \
		--entrypoint bash \
		-e BUNDLEUTILS_USERNAME="$(BUNDLEUTILS_USERNAME)" \
		-e BUNDLEUTILS_PASSWORD="$(BUNDLEUTILS_PASSWORD)" \
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
