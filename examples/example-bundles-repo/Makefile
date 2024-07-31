.DEFAULT_GOAL	:=  help
SHELL			:=  /bin/bash
MAKEFLAGS		+= --no-print-directory
MKFILE_DIR		:=  $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
.ONESHELL:

.PHONY: %/update-bundle
%/update-bundle: ## Run bundleutils update-bundle in the directory '%'
%/update-bundle: %/check
	bundleutils update-bundle -t $*

.PHONY: %/fetch
%/fetch: ## Run bundleutils fetch in the directory '%'
	cd $*
	bundleutils fetch

.PHONY: %/transform
%/transform: ## Run bundleutils fetch in the directory '%'
	cd $*
	bundleutils transform

.PHONY: %/refresh
%/refresh: ## Run bundleutils fetch and transform in the directory '%'
%/refresh: %/fetch %/transform
	cd $*

.PHONY: %/validate
%/validate: ## Run validation steps in the directory '%'
%/validate: %/check %/update-bundle
	cd $*
	bundleutils ci-setup
	bundleutils ci-start || { bundleutils ci-stop; exit 1; }
	bundleutils ci-validate || { bundleutils ci-stop; exit 1; }
	bundleutils ci-stop

.PHONY: %/all
%/all: ## Run all steps in the directory '%'
%/all: %/refresh %/validate
	cd $*

.PHONY: %/git-diff
%/git-diff: ## Run git diff in the directory '%'
%/git-diff: %/check
	cd $*
	git --no-pager diff --exit-code .

.PHONY: %/git-commit
%/git-commit: ## Run git commit in the directory '%'
%/git-commit: %/check
	git add $*
	git commit -m "Update $$(basename $*) (version: $$(grep -oP 'version: \K.*' $*/bundle.yaml))" $*

.PHONY: %/git-create-branch
%/git-create-branch: ## Creates a drift branch for the directory '%'
%/git-create-branch: %/check
	git checkout -b $$(basename $*)-drift
	git push --set-upstream origin $$(basename $*)-drift
	git checkout -

.PHONY: %/deploy-cm
%/deploy-cm: ## Deploy configmap from directory '%'
%/deploy-cm: %/check
	kubectl create cm $$(basename $*) --from-file $* -oyaml --dry-run=client | kubectl apply -f -

.PHONY: %/check
%/check: ## Ensure a bunde exists in the directory '%'
	@if [ ! -f $*/bundle.yaml ]; then echo "Bundle does not exist in $*"; exit 1; fi

.PHONY: git-diff
git-diff: ## Run git diff for the whole repository
	git --no-pager diff --exit-code

.PHONY: git-reset
git-reset: ## Run git reset --hard for the whole repository
	git reset origin/$$(git branch --show-current) --hard

.PHONY: find
find: ## List all bundle dirs according to bundle pattern var 'BP'
find: guard-BP
	@git ls-files -- "**/bundle.yaml" | grep -E "$(BP)/" | xargs -r dirname

.PHONY: help
help: ## Makefile Help Page
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[\/\%a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-21s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) 2>/dev/null

.PHONY: guard-%
guard-%:
	@if [[ "${${*}}" == "" ]]; then echo "Environment variable $* not set"; exit 1; fi
