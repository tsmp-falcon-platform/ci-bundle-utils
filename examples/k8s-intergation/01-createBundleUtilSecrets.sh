#!/bin/bash

set -euo pipefail

NAMESPACE="cbci"
BUNDLE_SECRETS="yaml/bu-secrets.yaml"
BUNDLE_SECRET_NAME="bundle-utils-secrets"
SSH_SECRET_DIR="k8s-git-ssh-secret"
SSH_SECRET_NAME="secret-ssh-auth"


# Ensure dependencies exist
command -v yq >/dev/null 2>&1 || { echo "❌ 'yq' is required but not installed. Aborting."; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "❌ 'kubectl' is required but not installed. Aborting."; exit 1; }

echo "🔄 Recreating Kubernetes secret '$BUNDLE_SECRET_NAME' in namespace '$NAMESPACE'..."
kubectl delete secret "$BUNDLE_SECRET_NAME" -n "$NAMESPACE" --ignore-not-found


kubectl create secret generic bundle-utils-secrets -n $NAMESPACE \
    --from-literal=BUNDLEUTILS_USERNAME="$(yq '.BUNDLEUTILS_USERNAME' ${BUNDLE_SECRETS} )" \
    --from-literal=BUNDLEUTILS_PASSWORD="$(yq '.BUNDLEUTILS_PASSWORD' ${BUNDLE_SECRETS} )" \
    --from-literal=BUNDLEUTILS_JENKINS_URL="$(yq '.BUNDLEUTILS_JENKINS_URL' ${BUNDLE_SECRETS} )" \
    --from-literal=JENKINS_URL="$(yq '.BUNDLEUTILS_JENKINS_URL' ${BUNDLE_SECRETS} )" \
    --from-literal=GIT_COMMITTER_NAME="$(yq '.GIT_COMMITTER_NAME' ${BUNDLE_SECRETS} )" \
    --from-literal=GIT_AUTHOR_NAME="$(yq '.GIT_AUTHOR_NAME' ${BUNDLE_SECRETS} )" \
    --from-literal=GIT_REPO="$(yq '.GIT_REPO' ${BUNDLE_SECRETS} )" \
    --from-literal=GIT_COMMITTER_EMAIL="$(yq '.GIT_COMMITTER_EMAIL' ${BUNDLE_SECRETS} )" \
    --from-literal=GIT_AUTHOR_EMAIL="$(yq '.GIT_AUTHOR_EMAIL' ${BUNDLE_SECRETS} )" \
    --from-literal=GIT_ACTION="$(yq '.GIT_ACTION' ${BUNDLE_SECRETS} )"
    #--from-literal=id_rsa="$(yq '.GITHUB_SSH_PRIVKEY' ${BUNDLE_SECRETS} )"

echo "✅ Secret '$BUNDLE_SECRET_NAME' created successfully."

echo "🔄 Recreating SSH secret '$SSH_SECRET_NAME'..."
kubectl delete secret "$SSH_SECRET_NAME" -n "$NAMESPACE" --ignore-not-found

if [[ ! -d "$SSH_SECRET_DIR" ]]; then
  echo "❌ Directory '$SSH_SECRET_DIR' not found. Aborting."
  exit 1
fi

cd $SSH_SECRET_DIR
# workaround: K8s secret    --type=kubernetes.io/ssh-auth expects file ssh-privatekey
#cp  id_rsa ssh-privatekey
kubectl create secret generic "$SSH_SECRET_NAME" \
  --from-file=./ \
  -n "$NAMESPACE"
cd -
echo "✅ SSH secret '$SSH_SECRET_NAME' created from directory '$SSH_SECRET_DIR'."














