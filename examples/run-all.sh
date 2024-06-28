#!/usr/bin/env bash

# Run all examples
set -euo pipefail

export BUNDLEUTILS_PASSWORD BUNDLEUTILS_USERNAME BUNDLEUTILS_JENKINS_URL BUNDLEUTILS_CI_VERSION

# example
# export BUNDLEUTILS_PASSWORD=11d41c03f331b654a9be07618365aee016; export BUNDLEUTILS_USERNAME=admin; export BUNDLEUTILS_JENKINS_URL=http://ci.127.0.0.1.beesdns.com/dev-1
# export BUNDLEUTILS_CI_VERSION=2.452.2.3

# ask for input if BUNDLEUTILS_USERNAME not set exported value
if [ -z "${BUNDLEUTILS_USERNAME:-}" ]; then
    read -rp "Enter the BUNDLEUTILS_USERNAME: " BUNDLEUTILS_USERNAME
fi
if [ -z "${BUNDLEUTILS_PASSWORD:-}" ]; then
    read -rsp "Enter the BUNDLEUTILS_PASSWORD: " BUNDLEUTILS_PASSWORD
    echo
fi
if [ -z "${BUNDLEUTILS_JENKINS_URL:-}" ]; then
    read -rp "Enter the BUNDLEUTILS_JENKINS_URL: " BUNDLEUTILS_JENKINS_URL
fi
if [ -z "${BUNDLEUTILS_CI_VERSION:-}" ]; then
    read -rp "Enter the BUNDLEUTILS_CI_VERSION: " BUNDLEUTILS_CI_VERSION
fi

eval "$(_BUNDLEUTILS_COMPLETE=bash_source bundleutils)"
bundleutils fetch
bundleutils normalize
bundleutils operationalize
bundleutils ci-setup -s target/docs-operationalized
bundleutils ci-start
bundleutils ci-validate -s target/docs-operationalized
bundleutils ci-stop



