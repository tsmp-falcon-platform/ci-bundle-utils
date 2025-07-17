#!/bin/bash
###!/usr/bin/env bash
#
# bundleutils‑prepare.sh
# * Verifies SSH connectivity
# * Creates or checks out a deterministic Git branch
# * Clones the target repo and configures author info
#
# Required env vars:
#   - GIT_REPO            ssh:// or git@… URL
#   - JENKINS_URL         full CI/OC URL (used to derive branch)
#   - GIT_COMMITTER_NAME  git config user.name
#   - GIT_COMMITTER_EMAIL git config user.email
#
###############################################################################
#set -euo pipefail
set -eu

[ "${DEBUG_SCRIPT:-false}" = "true" ] && set -x
SSH_DIR=/root/.ssh
KEY_FILE="$SSH_DIR/privateKey"
KNOWN="$SSH_DIR/known_hosts"
CONFIG="$SSH_DIR/config"          # optional but harmless if missing

###############################################################################
# 1.  Sanity‑check inputs
###############################################################################
for v in GIT_REPO JENKINS_URL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL; do
  eval val=\${$v}
  [ -n "$val" ] || { echo "❌  $v is not set" >&2; exit 1; }
done

###############################################################################
# 2.  Verify SSH access to GitHub once (fingerprints must already be in $KNOWN)
###############################################################################
ssh -F "$CONFIG" -o UserKnownHostsFile="$KNOWN" -i "$KEY_FILE" -T git@github.com || true
echo "🔒 Known hosts in use:" && cat "$KNOWN"

###############################################################################
# 3.  Derive & validate branch name from JENKINS_URL
###############################################################################
BRANCH_CANDIDATE=$(printf '%s' "$JENKINS_URL" | sed 's|^https://||; s|/$||; s/\./-/g')
git check-ref-format --branch "$BRANCH_CANDIDATE" \
  || { echo "❌  Invalid branch: $BRANCH_CANDIDATE" >&2; exit 1; }
GIT_BRANCH="$BRANCH_CANDIDATE"
echo "✔  Using branch: $GIT_BRANCH"

###############################################################################
# 4.  Start ssh‑agent & configure Git
###############################################################################
eval "$(ssh-agent -s)"
ssh-add "$KEY_FILE" >/dev/null

git config --global user.email "$GIT_COMMITTER_EMAIL"
git config --global user.name  "$GIT_COMMITTER_NAME"

###############################################################################
# 5.  Clone repo (skip if directory already exists)
###############################################################################
REPO_DIR=$(basename "${GIT_REPO%.git}")
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone "$GIT_REPO" "$REPO_DIR"
fi
cd "$REPO_DIR"

###############################################################################
# 6.  Ensure branch exists locally, create if missing
###############################################################################
git fetch origin --quiet
if git show-ref --verify --quiet "refs/remotes/origin/$GIT_BRANCH"; then
  git checkout --quiet -B "$GIT_BRANCH" "origin/$GIT_BRANCH"
else
  git checkout --quiet -B "$GIT_BRANCH"
fi

echo "✅  Repository ready on branch '$GIT_BRANCH'."
echo "✅  Start Audit now...."
/opt/bundleutils/work/examples/tutorials/bundle-management/bundle-management.sh
