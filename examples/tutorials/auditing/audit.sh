#!/usr/bin/env bash
# This script is used to audit a bundle and push changes to the remote repository.

set -euo pipefail

GIT_ACTION="${GIT_ACTION:-commit-only}"
mandatory_envs="BUNDLEUTILS_USERNAME BUNDLEUTILS_PASSWORD JENKINS_URL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL GIT_ACTION"
usage_message="Usage: ./audit.sh [setup|help|<jenkins-url>]
  ./audit.sh setup         - Setup the bundleutils environment variables.
  ./audit.sh help          - Show this help message.
  ./audit.sh <jenkins-url> - Fetch from this URL regardless (keeping the other variables).

  Mandatory environment variables (configured manually or using setup):
    BUNDLEUTILS_USERNAME   - Your bundleutils username.
    BUNDLEUTILS_PASSWORD   - Your bundleutils password.
    JENKINS_URL            - The Jenkins URL to fetch the bundle from.
    GIT_COMMITTER_NAME     - The name to use for git commits.
    GIT_COMMITTER_EMAIL    - The email to use for git commits.
    GIT_ACTION             - The git action to perform (do-nothing, add-only, commit-only, push).
"

###############################
#### ENVIRONMENT VARIABLES ####
###############################

function source_env() {
  # shellcheck disable=SC1091
  [ ! -f ".bundleutils.env" ] || source .bundleutils.env
}
source_env

if [[ "${1:-}" == "help" ]]; then
  echo -e "$usage_message"
  exit 0
elif [[ "${1:-}" == http* ]]; then
  export JENKINS_URL="${1:-}"
elif [[ "${1:-}" == "setup" ]]; then
  if [[ ! -t 0 ]]; then
    echo "AUDITING: Error: Setup requires a terminal to run."
    exit 1
  fi
  # Setup script for the bundleutils
  echo "AUDITING: Setting up bundleutils..."
  GIT_ACTION="${GIT_ACTION:-commit-only}"
  mandatory_envs="BUNDLEUTILS_USERNAME BUNDLEUTILS_PASSWORD JENKINS_URL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL GIT_ACTION"
  output=""
  # check if mandatory envs are set, if not, prompt for them
  for env in $mandatory_envs; do
    current_value="${!env:-}"
    # if the env name contains PASSWORD, do not show the current value and hide the input on read
    if [[ "$env" == *PASSWORD* ]]; then
      # if current_value is empty, show -EMPTY- instead of -HIDDEN-
      if [[ -z "$current_value" ]]; then
        current_value_display="-EMPTY-"
      else
        current_value_display="-HIDDEN-"
      fi
      read -rsp "AUDITING: Please enter your ${env} (current: $current_value_display): " input
      echo
    else
      # show the current value for all other envs
      read -rp "AUDITING: Please enter your ${env} (current: $current_value): " input
    fi
    # if input is empty, use the current value
    if [[ -z "$input" ]]; then
      input="$current_value"
    fi
    output+="export $env=$input\n"
    [[ "$env" != "GIT_COMMITTER_NAME" ]] || output+="export GIT_AUTHOR_NAME=$input\n"
    [[ "$env" != "GIT_COMMITTER_EMAIL" ]] || output+="export GIT_AUTHOR_EMAIL=$input\n"
  done
  echo -e "$output" > .bundleutils.env
  source_env
  echo "AUDITING: Bundleutils setup complete. Saved to .bundleutils.env - do not share this file or check into git."
  # do you wish to run the audit now? (y/n)
  read -rp "AUDITING: Do you wish to run the audit now? (Y/n): " input
  if [[ "$input" =~ ^[Nn]$ ]]; then
    echo "AUDITING: Audit skipped. You can run it later with: ./audit.sh"
    exit 0
  else
    echo "AUDITING: Running audit..."
  fi
fi

# Git actions environment variable: do-nothing, add-only, commit-only, push
if [[ -z "${GIT_ACTION:-}" ]]; then
  GIT_ACTION="do-nothing"
elif [[ ! "${GIT_ACTION:-}" =~ ^(do-nothing|add-only|commit-only|push)$ ]]; then
  echo "AUDITING: Error: Invalid GIT_ACTION value. Must be one of: do-nothing, add-only, commit-only, push."
  exit 1
fi

GIT_ACTION_ADD=$([[ "${GIT_ACTION}" =~ ^(add-only|commit-only|push)$ ]] && echo 'true' || echo 'false')
GIT_ACTION_COMMIT=$([[ "${GIT_ACTION}" =~ ^(commit-only|push)$ ]] && echo 'true' || echo 'false')
GIT_ACTION_PUSH=$([[ "${GIT_ACTION}" == "push" ]] && echo 'true' || echo 'false')
echo "AUDITING: GIT_ACTION=${GIT_ACTION}"

# Load positional parameters
export JENKINS_URL="${JENKINS_URL:-${1:-}}"
export BUNDLEUTILS_USERNAME="${BUNDLEUTILS_USERNAME:-${2:-}}"
export BUNDLEUTILS_PASSWORD="${BUNDLEUTILS_PASSWORD:-${3:-}}"

# This will ensure all plugins are left in the bundle.
# If you want to remove dependencies, etc, comment the following lines:
export BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY='ALL'
export BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY='ALL'

# Check mandatory environment variables function
check_envs() {
  local vars="${1:-}"
  local reason="${2:-"No reason provided"}"
  for var in $vars; do
    if [[ -z "${!var:-}" ]]; then
      echo "AUDITING: Error: Environment variable $var is not set. ${reason}."
      exit 1
    fi
  done
}
check_envs "BUNDLEUTILS_PASSWORD BUNDLEUTILS_USERNAME" "Jenkins API token needed to fetch the bundle"
check_envs "JENKINS_URL" "Jenkins URL needed to fetch the bundle"

###############################
#### BUNDLEUTILS COMMANDS  ####
###############################

# Get bundle name from the URL
echo "AUDITING: Running bundleutils extract-name-from-url..."
BUNDLE_NAME=$(bundleutils extract-name-from-url)
FETCH_TARGET="target/fetched/${BUNDLE_NAME}"

# Fetch the bundle
echo "AUDITING: Running bundleutils fetch -t ${FETCH_TARGET}"
bundleutils fetch -t "${FETCH_TARGET}"

# Sanitize the fetched bundle
echo "AUDITING: Running bundleutils audit -s $FETCH_TARGET -t $BUNDLE_NAME"
bundleutils audit -s "${FETCH_TARGET}" -t "$BUNDLE_NAME"

# list the bundle files
find "$BUNDLE_NAME"

# Check if git command exists and directory is a git repository
if ! command -v git &> /dev/null; then
  echo "AUDITING: Git command not found. Skipping git actions."
  exit 0
fi
if ! git rev-parse --is-inside-work-tree &> /dev/null; then
  echo "AUDITING: Not a git repository. Skipping git actions."
  exit 0
fi

###############################
####       GIT LOGIC       ####
###############################

# Git actions
GIT_ORIGIN="${GIT_ORIGIN:-"origin"}"
GIT_MAIN="${GIT_MAIN:-"main"}"
GIT_CURRENT_BRANCH="$(git branch --show-current)"
echo "AUDITING: GIT_ORIGIN=$GIT_ORIGIN"
echo "AUDITING: GIT_MAIN=$GIT_MAIN"
echo "AUDITING: GIT_CURRENT_BRANCH=$GIT_CURRENT_BRANCH"
echo "AUDITING: GIT_COMMITTER_NAME=$GIT_COMMITTER_NAME"
echo "AUDITING: GIT_COMMITTER_EMAIL=$GIT_COMMITTER_EMAIL"
echo "AUDITING: GIT_AUTHOR_NAME=$GIT_AUTHOR_NAME"
echo "AUDITING: GIT_AUTHOR_EMAIL=$GIT_AUTHOR_EMAIL"

if [ -d "$BUNDLE_NAME" ]; then
  if [[ "$GIT_ACTION_ADD" == "true" ]]; then
    git add "$BUNDLE_NAME"
    if git diff --cached --exit-code "$BUNDLE_NAME"; then
      echo "AUDITING: No changes to commit for $BUNDLE_NAME."
    else
      if [[ "$GIT_ACTION_COMMIT" == "true" ]]; then
        echo "AUDITING: Committing changes to $BUNDLE_NAME"
        git commit -m "Audit bundle $BUNDLE_NAME" "$BUNDLE_NAME"
        echo "AUDITING: Commit: $(git --no-pager log -n1 --pretty=format:"YOUR_GIT_REPO/commit/%h %s")"

        if [[ "$GIT_ACTION_PUSH" == "true" ]]; then
          git push "${GIT_ORIGIN}" "${GIT_CURRENT_BRANCH}"
          echo "AUDITING: Pushed to YOUR_GIT_REPO/tree/$GIT_CURRENT_BRANCH"
        fi
      fi
    fi
  fi
else
  echo "AUDITING: Bundle $BUNDLE_NAME not found. No changes to commit or push."
fi
echo "AUDITING: Bundle audit complete."