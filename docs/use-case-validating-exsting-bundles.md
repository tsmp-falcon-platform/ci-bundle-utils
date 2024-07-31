# Validating existing bundles

## Assumptions

- You have a CasC bundle available which you wish to validate.
- You have a single user wildcard license to start the test server.

## Setup

Start a container using the method of your choice.

If starting locally with [docker](./setup-docker.md) or [docker-compose](./setup-docker-compose.md)

- export the bundle workspace to mount your bundles directory.
- export the wildcard test license environment variables.

```sh
# bundle workspace
export BUNDLES_WORKSPACE=/path/to/my/bundles

# e.g. using base64 to cover line breaks, etc
# cat license.key | base64 -w0
# cat license.cert | base64 -w0
export CASC_VALIDATION_LICENSE_KEY_B64=$(cat license.key | base64 -w0)
export CASC_VALIDATION_LICENSE_CERT_B64=$(cat license.cert | base64 -w0)
```

If starting in [kubernetes](./setup-kubernetes.md), no local mount possible and you will have to copy or checkout your bundles directory.

## Commands

**PRO TIP:** THIS IS A VERY VERBOSE EXPLANATION OF COMMANDS. Check out the [predefined-configs](./working-with-predefined-configs.md) to remove the need for specifying arguments on the command line.

Start a shell in the container. e.g.

```sh
# with docker
docker exec -it bundleutils bash

# with docker-compose
docker compose exec bundleutils bash

# with kubectl
kubectl exec -it bundleutils -- bash
```

Run the commands to validate your bundle, for example:

```sh
# what do we want to validate?
export BUNDLEUTILS_CI_TYPE=mm
export BUNDLEUTILS_CI_VERSION=2.452.2.3

# point to the bundle in question
MY_BUNDLE=/workspace/my-bundle

# setup the test server using the plugins of the bundle you
bundleutils ci-setup -s "$MY_BUNDLE"

# start the test server
bundleutils ci-start

# validate the bundle
bundleutils ci-validate -s "$MY_BUNDLE"

# stop the test server
bundleutils ci-stop
```
