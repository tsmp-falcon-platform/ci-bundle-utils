# Validating existing bundles

## Assumptions

- You have a directory to keep your bundles
- You have access to a CloudBees Controller or Operations Center you wish to validate.
- You have a user and token able to fetch the exported config.
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

Start a shell in the container. e.g.

```sh
# with docker
docker exec -it bundleutils bash

# with docker-compose
docker compose exec bundleutils bash

# with kubectl
kubectl exec -it bundleutils -- bash
```

Run the commands to fetch your bundle, for example:

**PRO TIP:** THIS IS A VERY VERBOSE EXPLANATION OF COMMANDS. Check out the [predefined-configs](./working-with-predefined-configs.md) to remove the need for specifying arguments on the command line.

Let's first fetch the bundle.

```sh
# where are we fetching the bundle from?
export JENKINS_URL='https://cjoc.acme.org/controller'

# where do we want to put the fetch bundle in it's raw/unusable state?
export FETCH_DIR='target/fetched-bundle'

# authentication parameters
export USERNAME='admin' # in production you would likely have a dedicated user
export PASSWORD='11...' # API token

# fetch the bundle from the target
bundleutils fetch --url "$JENKINS_URL" --target-dir "$FETCH_DIR" --username "$USERNAME" --password "$PASSWORD"
```

Now let's apply transformations the bundle, making it consumable for our server again.

In this use case, we will use the examples [remove-dynamic-stuff.yaml](../examples/example-bundles-repo/bundles/transformations/remove-dynamic-stuff.yaml) and [controllers-common.yaml](../examples/example-bundles-repo/bundles/transformations/controllers-common.yaml).

```sh
# we want to transform the bundle we just fetched, so...
TRANSFORM_SRC="$FETCH_DIR"

# and we'll place the result in target/transformed-bundle
TRANSFORM_DST='target/transformed-bundle'

# which transformations should we apply?
TRANSFORM_1=/path/to/remove-dynamic-stuff.yaml
TRANSFORM_2=/path/to/controllers-common.yaml

bundleutils transform --source-dir "$TRANSFORM_SRC" --target-dir  "$TRANSFORM_DST" --config  "$TRANSFORM_1" --config "$TRANSFORM_2"
```

Run the commands to validate your newly transformed bundle, for example:

```sh
# what do we want to validate?
export BUNDLEUTILS_CI_TYPE=mm
export BUNDLEUTILS_CI_VERSION=2.452.2.3

# point to the bundle in question
MY_BUNDLE=target/transformed-bundle

# setup the test server using the plugins of the bundle you
bundleutils ci-setup -s "$MY_BUNDLE"

# start the test server
bundleutils ci-start

# validate the bundle
bundleutils ci-validate -s "$MY_BUNDLE"

# stop the test server
bundleutils ci-stop
```
