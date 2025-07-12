#!/bin/bash

set -euo pipefail

SECRET_DIR="$(pwd)/k8s-git-ssh-secret"
PRIVATEKEY="$SECRET_DIR/privateKey"
CONFIG="$SECRET_DIR/config"
KNOWN_HOSTS="$SECRET_DIR/known_hosts"
#GITHUB_HOST="ssh.github.com"
GITHUB_HOST="github.com"

error() {
    echo "❌ $1"
    exit 1
}
success() {
    echo "✅ $1"
}
warning() {
    echo "WARNING :-| $1"
}



echo "🔍 Checking SSH private key..."
if [[ -d "$SECRET_DIR" ]]; then
  success "Directory exists: $SECRET_DIR"
else
  error "Directory does not exist: $SECRET_DIR"
  exit 1
fi

echo "🔍 Checking SSH privatekey file..."
if [[ ! -f "$PRIVATEKEY" ]]; then
    error "'$PRIVATEKEY' not found"
fi
echo "🔍 Checking SSH config file..."
if [[ ! -f "$CONFIG" ]]; then
    error "'$CONFIG' not found"
fi
echo "🔍 Checking known_hosts file..."
if [[ ! -f "$KNOWN_HOSTS" ]]; then
    error "'$KNOWN_HOSTS' not found"
fi

chmod 600 "$PRIVATEKEY"

sshKnownHostsoutput=$(ssh -F "$CONFIG" -o UserKnownHostsFile="$KNOWN_HOSTS" -i "$PRIVATEKEY" git@github.com 2>&1) || true

if echo "$sshKnownHostsoutput" | grep -q "successfully authenticated"; then
  success "$KNOWN_HOSTS exists and appears to be a valid known_hosts file"
  success "$PRIVATEKEY exists and appears to be a valid private key"
  success "$CONFIG exists and appears to be a valid config"
else
  error "SSH known_hosts test failed or key is invalid. Output was: $sshKnownHostsoutput"
fi


success "End: All pre-checks passed."




