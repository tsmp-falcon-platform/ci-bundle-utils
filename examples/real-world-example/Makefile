.DEFAULT_GOAL	:=  help
SHELL			:=  /bin/bash
MAKEFLAGS		+= --no-print-directory
MKFILE_DIR		:=  $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
GIT_ORIGIN		:=  origin
GIT_MAIN		:=  main
.ONESHELL:

.PHONY: run/%/update-bundle
run/%/update-bundle: ## Run bundleutils update-bundle in the directory '%'
run/%/update-bundle: run/%/check
	bundleutils update-bundle -t $*

.PHONY: run/%/fetch
run/%/fetch: ## Run bundleutils fetch in the directory '%'
	cd $*
	bundleutils fetch

.PHONY: run/%/transform
run/%/transform: ## Run bundleutils fetch in the directory '%'
	cd $*
	bundleutils transform

.PHONY: run/%/refresh
run/%/refresh: ## Run bundleutils fetch and transform in the directory '%'
run/%/refresh: run/%/fetch run/%/transform
	cd $*

.PHONY: run/%/validate
run/%/validate: ## Run validation steps in the directory '%'
run/%/validate: run/%/check run/%/update-bundle
	cd $*
	bundleutils ci-setup
	bundleutils ci-start || { bundleutils ci-stop; exit 1; }
	bundleutils ci-validate || { bundleutils ci-stop; exit 1; }
	bundleutils ci-stop

.PHONY: run/%/all
run/%/all: ## Run all steps in the directory '%'
run/%/all: run/%/refresh run/%/validate
	cd $*

.PHONY: run/%/git-diff
run/%/git-diff: ## Run git diff in the directory '%'
run/%/git-diff: run/%/check
	cd $*
	git --no-pager diff --exit-code .

.PHONY: run/%/git-commit
run/%/git-commit: ## Run git commit in the directory '%'
run/%/git-commit: run/%/check
	git add $*
	git commit -m "Update $$(basename $*) (version: $$(grep -oP 'version: \K.*' $*/bundle.yaml))" $*

run/%/git-handle-drift: ## Creates or rebases drift branch for the directory '%'
	if git show-ref --quiet refs/remotes/$(GIT_ORIGIN)/$$(basename $*)-drift; then \
		$(MAKE) run/$*/git-rebase-drift; \
	else \
		$(MAKE) run/$*/git-create-drift; \
	fi

.PHONY: run/%/git-checkout-drift
run/%/git-checkout-drift: ## Checks out a drift branch for the directory '%'
run/%/git-checkout-drift: run/%/check
	git checkout $$(basename $*)-drift

.PHONY: run/%/git-create-drift
run/%/git-create-drift: ## Creates a drift branch for the directory '%'
run/%/git-create-drift: run/%/check
	set -e
	git checkout -b $$(basename $*)-drift
	git push --set-upstream $(GIT_ORIGIN) $$(basename $*)-drift
	git checkout -

.PHONY: run/%/git-rebase-drift
run/%/git-rebase-drift: ## Rebases a drift branch for the directory '%'
run/%/git-rebase-drift: run/%/git-checkout-drift
	set -e
	git reset --hard $(GIT_ORIGIN)/$$(basename $*)-drift
	git fetch $(GIT_ORIGIN)
	git merge $(GIT_ORIGIN)/$(GIT_MAIN) --no-ff -m "Merging updates from $(GIT_ORIGIN)/$(GIT_MAIN) into $$(basename $*)-drift"
	git push $(GIT_ORIGIN) $$(basename $*)-drift
	git checkout -

.PHONY: run/%/deploy-cm
run/%/deploy-cm: ## Deploy configmap from directory '%'
run/%/deploy-cm: run/%/check
	kubectl create cm $$(basename $*) --from-file $* -oyaml --dry-run=client | kubectl apply -f -

.PHONY: run/%/check
run/%/check: ## Ensure a bunde exists in the directory '%'
	@if [ ! -f $*/bundle.yaml ]; then echo "Bundle does not exist in $*"; exit 1; fi

.PHONY: auto/%
auto/%: ## Expect MY_BUNDLE and then run 'make $MYBUNDLE/%'
auto/%: guard-MY_BUNDLE
	$(MAKE) run/$(MY_BUNDLE)/$*

.PHONY: git-diff
git-diff: ## Run git diff for the whole repository
	git --no-pager diff --exit-code

.PHONY: git-reset
git-reset: ## Run git reset --hard for the whole repository
	git reset $(GIT_ORIGIN)/$$(git branch --show-current) --hard

.PHONY: git-reset-main
git-reset-main: ## Checkout latest main and run git reset --hard
	git fetch $(GIT_ORIGIN)
	git checkout $(GIT_MAIN)
	git reset $(GIT_ORIGIN)/$$(git branch --show-current) --hard

.PHONY: git-push
git-push: ## Pushes the current branch to $(GIT_ORIGIN)
	git push $(GIT_ORIGIN) $$(git branch --show-current)

.PHONY: find
find: ## List all bundle dirs according to bundle pattern var 'BP'
find: guard-BP
	@git ls-files -- "**/bundle.yaml" | grep -E "$(BP)/bundle.yaml" | xargs -r dirname

.PHONY: help
help: ## Makefile Help Page
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[\/\%a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) 2>/dev/null

.PHONY: guard-%
guard-%:
	@if [[ "${${*}}" == "" ]]; then echo "Environment variable $* not set"; exit 1; fi
