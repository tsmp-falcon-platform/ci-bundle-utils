#!/usr/bin/env bash

# Run all examples
set -euo pipefail

# script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exit_trap() {
    if [ -z "${BUNDLEUTILS_NO_STOP_ON_FAIL:-}" ]; then
        bundleutils ci-stop
    fi
    exit 1
}

export BUNDLEUTILS_PATH BUNDLEUTILS_PASSWORD BUNDLEUTILS_USERNAME BUNDLEUTILS_JENKINS_URL BUNDLEUTILS_CI_VERSION

# example
# export BUNDLEUTILS_PASSWORD=11d41c03f331b654a9be07618365aee016; export BUNDLEUTILS_USERNAME=admin; export BUNDLEUTILS_JENKINS_URL=http://ci.127.0.0.1.beesdns.com/dev-1
# export BUNDLEUTILS_CI_VERSION=2.452.2.3

DEFAULT_BUNDLEUTILS_PATH="${SCRIPT_DIR}/bundlecontent.yaml"
# if BUNDLEUTILS_PATH not set, offer to set it with default value
if [ -z "${BUNDLEUTILS_PATH:-}" ]; then
    read -ep "Enter the BUNDLEUTILS_PATH (remove to fetch from url): " -i "$DEFAULT_BUNDLEUTILS_PATH" BUNDLEUTILS_PATH
fi

if [ -z "${BUNDLEUTILS_PATH:-}" ]; then
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
    echo "NOTE: We will now fetch the bundle using the following parameters:"
    echo "NOTE:  - BUNDLEUTILS_USERNAME=$BUNDLEUTILS_USERNAME"
    echo "NOTE:  - BUNDLEUTILS_PASSWORD=${BUNDLEUTILS_PASSWORD:0:3}..."
    echo "NOTE:  - BUNDLEUTILS_JENKINS_URL=$BUNDLEUTILS_JENKINS_URL"
    echo "NOTE:  - BUNDLEUTILS_CI_VERSION=$BUNDLEUTILS_CI_VERSION"
    # wait for user to press enter
    read -rp "Press enter to continue"

else
    echo "NOTE: Slightly more advanced setup with BUNDLEUTILS_PATH=$BUNDLEUTILS_PATH"
    echo "NOTE:  - This bundle is from an OC instance, so we need to set the BUNDLEUTILS_CI_TYPE to 'oc' and add some Java options"
    echo "NOTE:  - This bundle is also using the SystemReadPermission and ManagePermission Java options, so we need to set those as well"
    export BUNDLEUTILS_CI_VERSION="${BUNDLEUTILS_CI_VERSION:-2.452.2.3}"
    export BUNDLEUTILS_CI_TYPE=oc
    export BUNDLEUTILS_JAVA_OPTS='-Djenkins.security.SystemReadPermission=true -Djenkins.security.ManagePermission=true'
    echo "NOTE: We will now fetch the bundle using the following parameters:"
    echo "NOTE:  - BUNDLEUTILS_PATH=$BUNDLEUTILS_PATH"
    echo "NOTE:  - BUNDLEUTILS_CI_TYPE=$BUNDLEUTILS_CI_TYPE"
    echo "NOTE:  - BUNDLEUTILS_JAVA_OPTS=$BUNDLEUTILS_JAVA_OPTS"
    echo "NOTE:  - BUNDLEUTILS_CI_VERSION=$BUNDLEUTILS_CI_VERSION"
    # wait for user to press enter
    read -rp "Press enter to continue"
fi

set -x
bundleutils fetch
bundleutils normalize
bundleutils operationalize
bundleutils ci-setup -s target/docs-operationalized
bundleutils ci-start || exit_trap
bundleutils ci-validate -s target/docs-operationalized || exit_trap
bundleutils ci-stop
set +x



