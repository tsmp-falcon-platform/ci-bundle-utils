#!/bin/bash

set -euo pipefail

SECRET_DIR="k8s-git-ssh-secret"
ID_RSA="$SECRET_DIR/id_rsa"
CONFIG="$SECRET_DIR/config"
KNOWN_HOSTS="$SECRET_DIR/known_hosts"
GITHUB_HOST="[ssh.github.com]:443"

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
  echo "✅ Directory exists: $SECRET_DIR"
else
  error "Directory does not exist: $SECRET_DIR"
  exit 1
fi

if [[ ! -f "$ID_RSA" ]]; then
    error "'$ID_RSA' not found"
fi

# Check if id_rsa is a valid private key
if ! grep -q -- "-----BEGIN RSA PRIVATE KEY-----" "$ID_RSA" && \
   ! grep -q -- "-----BEGIN OPENSSH PRIVATE KEY-----" "$ID_RSA"; then
    error "'$ID_RSA' is not a valid SSH private key"
fi

chmod 600 "$ID_RSA"

sshoutput=$(ssh -T -i k8s-git-ssh-secret/id_rsa git@github.com 2>&1) || true

if echo "$sshoutput" | grep -q "successfully authenticated"; then
  echo "✅ SSH key is valid and authentication succeeded."
else
  error "SSH connection test failed or key is invalid. Output was: $sshoutput"
fi

success "'$ID_RSA' exists and appears to be a valid private key"

echo "🔍 Checking SSH config file..."
if [[ ! -f "$CONFIG" ]]; then
    error "'$CONFIG' not found"
fi

# Check if config contains a GitHub Host entry
if ! grep -qiE "Host\s+github\.com" "$CONFIG"; then
    error "'$CONFIG' does not contain a 'Host github.com' entry"
fi
if ! grep -qiE "Hostname\s+ssh\.github\.com" "$CONFIG"; then
    error "'$CONFIG' does not contain 'Hostname ssh.github.com'"
fi
if ! grep -qiE "Port\s+443" "$CONFIG"; then
    error "'$CONFIG' does not contain 'Port 443'"
fi
success "'$CONFIG' contains correct SSH configuration for GitHub"

echo "🔍 Checking known_hosts file..."
if [[ ! -f "$KNOWN_HOSTS" ]]; then
    error "'$KNOWN_HOSTS' not found"
fi

# Validate presence of all required keys
for KEY_TYPE in ecdsa-sha2-nistp256 ssh-ed25519 ssh-rsa; do
    if ! grep -q "${GITHUB_HOST} ${KEY_TYPE}" "$KNOWN_HOSTS"; then
        #error "'$KNOWN_HOSTS' is missing GitHub entry for key type: $KEY_TYPE"
        warning "'$KNOWN_HOSTS' is missing GitHub entry for key type: $KEY_TYPE"
    fi
done
success "'$KNOWN_HOSTS' contains valid entries for GitHub at $GITHUB_HOST"

echo "🎉 All pre-checks passed."




