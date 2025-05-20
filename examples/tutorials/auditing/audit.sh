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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
elif [[ "${1:-}" == "cjoc-and-online-controllers" ]]; then
  # List all controllers
  CONTROLLERS_JSON=$(curl --fail -u "$BUNDLEUTILS_USERNAME:$BUNDLEUTILS_PASSWORD" "${JENKINS_URL}/api/json?pretty&tree=jobs\[name,online,state,endpoint\]")
  ONLINE_CONTROLLERS=$(echo "$CONTROLLERS_JSON" | jq -r '.jobs[]|select(.online == true).endpoint')
  if [[ -z "$ONLINE_CONTROLLERS" ]]; then
    echo "AUDITING: No online controllers found."
  else
    echo
    echo
    echo "AUDITING: Auditing the following ONLINE controllers and then the OC:"
    echo "$ONLINE_CONTROLLERS"
    echo
    echo
    sleep 5
  fi
  for CONTROLLER in $ONLINE_CONTROLLERS; do
    echo "AUDITING: Found online controller: $CONTROLLER"
    # Fetch the bundle from the controller
    if BUNDLEUTILS_JENKINS_URL="$CONTROLLER" $0; then
      echo "AUDITING: Bundle fetched from $CONTROLLER"
    else
      echo "AUDITING: Failed to fetch bundle from $CONTROLLER"
    fi
  done
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
    echo "AUDITING: Performing audit..."
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
GIT_BUNDLE_PRESERVE_HISTORY="${GIT_BUNDLE_PRESERVE_HISTORY:-}"
echo "AUDITING: GIT_ACTION=${GIT_ACTION}"

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

function migrate_bundle() {
  echo "AUDITING: Migrating from previous version $LAST_KNOWN_VERSION to $BUNDLE_DIR"
  if [[ "$GIT_ACTION_COMMIT" == "true" ]]; then
    git mv "$LAST_KNOWN_VERSION"  "$BUNDLE_DIR"
    git commit -m "Renaming $LAST_KNOWN_VERSION to $BUNDLE_DIR to preserve the git history" "$LAST_KNOWN_VERSION" "$BUNDLE_DIR"
    cp -r "$BUNDLE_DIR" "$LAST_KNOWN_VERSION"
    git add "$LAST_KNOWN_VERSION"
    git commit -m "Last known state of $LAST_KNOWN_VERSION before moving to $BUNDLE_DIR"
  fi
}

###############################
#### BUNDLEUTILS COMMANDS  ####
###############################

# This will ensure all plugins are left in the bundle.
# If you want to remove dependencies, etc, comment the following lines:
export BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY='ALL'
export BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY='ALL'

# Determine env vars simply by the URL alone
export BUNDLEUTILS_AUTO_ENV_USE_URL_ONLY='true'

# Get bundle name from the URL
echo "AUDITING: Running bundleutils config..."
bundleutils config

# Get the CI version
echo "AUDITING: Export the instance version to avoid fetching it every time..."
BUNDLEUTILS_CI_VERSION=$(bundleutils  config --key BUNDLEUTILS_CI_VERSION)
export BUNDLEUTILS_CI_VERSION

# If we are appending the version to the bundle name, are we migrating from a previous version?
# Get the current final bundle directory
BUNDLE_DIR="$(bundleutils config --key BUNDLEUTILS_AUDIT_TARGET_DIR)"
APPEND_VERSION="$(bundleutils config --key BUNDLEUTILS_AUTO_ENV_APPEND_VERSION)"
if [[ "$APPEND_VERSION" == "true" ]] && [[ ! -d "$BUNDLE_DIR" ]]; then
  echo "AUDITING: Bundle $BUNDLE_DIR not found. Looking for a previous version..."
  LAST_KNOWN_VERSION="$(bundleutils config --key BUNDLEUTILS_AUTO_ENV_LAST_KNOWN_VERSION 2> /dev/null || true)"
  if [[ -n "$LAST_KNOWN_VERSION" ]]; then
    if [[ "$GIT_BUNDLE_PRESERVE_HISTORY" == "true" ]]; then
      migrate_bundle
    elif [[ "$GIT_BUNDLE_PRESERVE_HISTORY" == "false" ]]; then
      echo "AUDITING: Bundle $BUNDLE_DIR will be created. Original bundle $LAST_KNOWN_VERSION will be left as is."
    else
      echo "AUDITING: Decision time!!! The $BUNDLE_DIR is not found. The last known version is $LAST_KNOWN_VERSION."
      echo "AUDITING: The GIT_BUNDLE_PRESERVE_HISTORY is not set. Please set it to true or false."
      echo "AUDITING: - true:  If you want to preserve the history of $LAST_KNOWN_VERSION by renaming it to $BUNDLE_DIR, and re-adding the old bundle."
      echo "AUDITING: - false: If you want to keep the history of $LAST_KNOWN_VERSION and start a new history for $BUNDLE_DIR"
      exit 1
    fi
  fi
fi

bundleutils fetch

# Sanitize the fetched bundle
echo "AUDITING: Running bundleutils audit..."
bundleutils audit

# list the bundle files
echo "AUDITING: Listing bundle files..."
BUNDLE_DIR="$(bundleutils config --key BUNDLEUTILS_AUDIT_TARGET_DIR)"
find "$BUNDLE_DIR"

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

# gitleaks check
gitleaks_check() {
  GITLEAKS_CHECK="${GITLEAKS_CHECK:-staged}"
  if [[ "${GITLEAKS_CHECK}" == "none" ]]; then
    echo "AUDITING: Skipping gitleaks check due to GITLEAKS_CHECK=none."
  else
    echo "AUDITING: Running gitleaks check with gitleaks version $(gitleaks version)"
    # Get config
    if [[ -n "${GITLEAKS_CONFIG:-}" ]]; then
      echo "AUDITING: Using GITLEAKS_CONFIG=$GITLEAKS_CONFIG"
    else
      echo "AUDITING: No GITLEAKS_CONFIG found in env."
      if [[ "${GITLEAKS_USE_EMBEDDED_CONFIG:-true}" == "true" ]]; then
        export GITLEAKS_CONFIG="${SCRIPT_DIR}/.gitleaks.toml"
        echo "AUDITING: GITLEAKS_USE_EMBEDDED_CONFIG=true. Using embedded config: $GITLEAKS_CONFIG"
      fi
    fi
    # Check runs
    case "${GITLEAKS_CHECK}" in
      none)
        echo "AUDITING: Skipping gitleaks check..."
        ;;
      all)
        echo "AUDITING: Running gitleaks check on all files..."
        if ! gitleaks git --no-color --verbose --redact --log-opts "$BUNDLE_DIR"; then
          echo "AUDITING: Gitleaks found leaks. Please check the output."
          exit 1
        fi
        ;&
      *)
        if [[ "${GITLEAKS_CHECK}" != "staged" ]]; then
          echo "AUDITING: GITLEAKS_CHECK is set to '$GITLEAKS_CHECK', not [all|staged]. Defaulting to staged."
        fi
        echo "AUDITING: Running gitleaks check on staged files..."
        if ! gitleaks git --no-color --staged --verbose --redact --log-opts "$BUNDLE_DIR"; then
          echo "AUDITING: Gitleaks found leaks. Please check the output."
          exit 1
        fi
        ;;
    esac
  fi
}

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

if [ -d "$BUNDLE_DIR" ]; then
  if [[ "$GIT_ACTION_ADD" == "true" ]]; then
    git add "$BUNDLE_DIR"
    gitleaks_check
    if git diff --cached --stat --exit-code "$BUNDLE_DIR"; then
      echo "AUDITING: No changes to commit for $BUNDLE_DIR."
    else
      if [[ "$GIT_ACTION_COMMIT" == "true" ]]; then
        echo "AUDITING: Committing changes to $BUNDLE_DIR"
        git commit -m "Audit bundle $BUNDLE_DIR (version: $BUNDLEUTILS_CI_VERSION)" "$BUNDLE_DIR"
        echo "AUDITING: Commit: $(git --no-pager log -n1 --pretty=format:"YOUR_GIT_REPO/commit/%h %s")"

        if [[ "$GIT_ACTION_PUSH" == "true" ]]; then
          git push "${GIT_ORIGIN}" "${GIT_CURRENT_BRANCH}"
          echo "AUDITING: Pushed to YOUR_GIT_REPO/tree/$GIT_CURRENT_BRANCH"
        fi
      fi
    fi
  fi
else
  echo "AUDITING: Bundle $BUNDLE_DIR not found. No changes to commit or push."
fi
echo "AUDITING: Bundle audit complete."