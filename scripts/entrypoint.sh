#!/usr/bin/env bash

set -euo pipefail

: "${BUNDLE_UID:=1000}"
: "${BUNDLE_GID:=1000}"

# Get current UID/GID of bundle-user
CURRENT_UID=$(id -u bundle-user)
CURRENT_GID=$(id -g bundle-user)

# If custom UID or GID is different, update the user/group
if [ "$BUNDLE_UID" -ne "$CURRENT_UID" ] || [ "$BUNDLE_GID" -ne "$CURRENT_GID" ]; then
    groupmod -g "$BUNDLE_GID" bundle-user
    usermod -u "$BUNDLE_UID" -g "$BUNDLE_GID" bundle-user
    chown -R "$BUNDLE_UID:$BUNDLE_GID" /home/bundle-user /opt/bundleutils/work /opt/bundleutils/.cache || true
fi

exec gosu bundle-user "$@"
