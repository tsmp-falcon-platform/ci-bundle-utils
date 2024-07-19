.DEFAULT_GOAL	:=  help
SHELL			:=  /bin/bash
MAKEFLAGS		+= --no-print-directory
MKFILE_DIR		:=  $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
.ONESHELL:

.PHONY: %/fetch
%/fetch: ## Run bundleutils fetch in the directory '%'
	cd $*
	bundleutils fetch

.PHONY: %/transform
%/transform: ## Run bundleutils fetch in the directory '%'
	cd $*
	bundleutils transform

.PHONY: %/validate
%/validate: ## Run all validation steps in the directory '%'
	cd $*
	bundleutils ci-setup
	bundleutils ci-start || bundleutils ci-stop
	bundleutils ci-validate || bundleutils ci-stop
	bundleutils ci-stop

.PHONY: %/process
%/process: ## Run all validation steps in the directory '%'
	cd $*
	bundleutils fetch
	bundleutils transform
	bundleutils ci-setup
	bundleutils ci-start || bundleutils ci-stop
	bundleutils ci-validate || bundleutils ci-stop
	bundleutils ci-stop

.PHONY: help
help: ## Makefile Help Page
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[\/\%a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-21s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) 2>/dev/null

.PHONY: guard-%
guard-%:
	@if [[ "${${*}}" == "" ]]; then echo "Environment variable $* not set"; exit 1; fi
