#!/usr/bin/env sh
###############################################################################
#  bundleutils‑git‑audit.sh
#
#  • prepares GitHub SSH authentication
#  • derives a deterministic branch name from $JENKINS_URL
#  • clones or checks‑out the repository and branch
#  • runs bundleutils audit + optional gitleaks
#  • commits / pushes depending on $GIT_ACTION
#
#  Dependencies: git, ssh-agent, bundleutils, (optional) gitleaks
###############################################################################

#set -euo pipefail
set -euo

###############################################################################
# 0.  CONSTANTS & HELPER FUNCTIONS
###############################################################################
export LC_ALL=C      # predictable sort/grep behaviour

die()   { printf >&2 'ERROR: %s\n' "$*"; exit 1; }
note()  { printf 'INFO : %s\n'  "$*"; }
debug() { [ "${DEBUG_SCRIPT:-false}" = "true" ] && set -x; }

indent() { sed "s/^/    /"; }   # simple indent helper for multi‑line logs

###############################################################################
# 1.  INPUT VALIDATION
###############################################################################
req_env="GIT_REPO JENKINS_URL GIT_COMMITTER_EMAIL GIT_COMMITTER_NAME \
         BUNDLEUTILS_USERNAME BUNDLEUTILS_PASSWORD"
for v in $req_env; do
  [ -n "${!v:-}" ] || die "$v is not set"
done

GIT_ACTION=${GIT_ACTION:-commit-only}
case $GIT_ACTION in do-nothing|add-only|commit-only|push) ;; *) die "Invalid GIT_ACTION";; esac

SSH_PATH=/root/.ssh
SSH_KEY=$SSH_PATH/privateKey
SSH_KNOWN_HOSTS=$SSH_PATH/known_hosts

[ -r "$SSH_KEY" ] || die "SSH key $SSH_KEY missing"

###############################################################################
# 2.  SSH PREPARATION
###############################################################################
mkdir -p  /root/.ssh
chmod 700 /root/.ssh
ssh -o UserKnownHostsFile=$SSH_KNOWN_HOSTS -i "$SSH_KEY" -T git@github.com || true
eval "$(ssh-agent -s)"
ssh-add "$SSH_KEY" >/dev/null

###############################################################################
# 3.  DERIVE & VALIDATE BRANCH NAME
###############################################################################
BRANCH_CANDIDATE=$(printf '%s' "$JENKINS_URL" | sed 's|^https://||; s|/$||; s/\./-/g')
git check-ref-format --branch "$BRANCH_CANDIDATE" \
  || die "Derived branch '$BRANCH_CANDIDATE' is not a valid Git ref"

note "Using branch: $BRANCH_CANDIDATE"

###############################################################################
# 4.  GLOBAL GIT CONFIG
###############################################################################
git config --global user.email "$GIT_COMMITTER_EMAIL"
git config --global user.name  "$GIT_COMMITTER_NAME"

###############################################################################
# 5.  CLONE OR CHECK OUT REPOSITORY
###############################################################################
REPO_DIR=$(basename -s .git "$GIT_REPO")
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone --quiet "$GIT_REPO" "$REPO_DIR"
fi
cd "$REPO_DIR"

git fetch origin --quiet
if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH_CANDIDATE"; then
  git checkout --quiet -B "$BRANCH_CANDIDATE" "origin/$BRANCH_CANDIDATE"
else
  git checkout --quiet -B "$BRANCH_CANDIDATE"
fi

###############################################################################
# 6.  BUNDLEUTILS AUDIT
###############################################################################
export BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY=ALL
export BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY=ALL

note "Running bundleutils fetch + audit …"
bundleutils fetch
bundleutils audit

BUNDLE_DIR=$(bundleutils audit --config-key BUNDLEUTILS_AUDIT_TARGET_DIR)

###############################################################################
# 7.  OPTIONAL GITLEAKS
###############################################################################
gitleaks_run() {
  [ "${GITLEAKS_CHECK:-staged}" = "none" ] && return 0
  note "Running gitleaks (${GITLEAKS_CHECK:-staged}) …"
  local args="git --no-color --verbose --redact"
  [ "${GITLEAKS_CHECK:-staged}" = "all" ] && args="$args --log-opts $BUNDLE_DIR"
  gitleaks $args || die "gitleaks detected secrets"
}

###############################################################################
# 8.  GIT ACTIONS
###############################################################################
if [ -d "$BUNDLE_DIR" ] && [ "$GIT_ACTION" != "do-nothing" ]; then
  git add "$BUNDLE_DIR"
  gitleaks_run

  if git diff --cached --quiet; then
    note "No bundle changes detected."
  else
    [ "$GIT_ACTION" = "add-only" ] && note "Changes staged but not committed." && exit 0
    git commit -m "Audit bundle $BUNDLE_DIR (CI version: $(bundleutils extract-version-from-url))"
    note "Changes committed."

    if [ "$GIT_ACTION" = "push" ]; then
      git push --quiet origin "$BRANCH_CANDIDATE"
      note "Changes pushed to origin/$BRANCH_CANDIDATE"
    fi
  fi
else
  note "Bundle dir missing or GIT_ACTION=do-nothing; nothing to commit."
fi
