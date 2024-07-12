# bundleutils

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
## Contents

- [TLDR - option 1 - docker](#tldr---option-1---docker)
- [TLDR - option 2 - docker compose](#tldr---option-2---docker-compose)
- [TLDR - option 3 - using a shared local cache](#tldr---option-3---using-a-shared-local-cache)
- [Introduction](#introduction)
  - [Bundle Util Commands](#bundle-util-commands)
  - [Test Server Commands](#test-server-commands)
- [The `transform` Command](#the-transform-command)
- [Examples](#examples)
  - [Non-Interactive Standard Workflow](#non-interactive-standard-workflow)
  - [Interactive Custom Transformation](#interactive-custom-transformation)
- [Local Development](#local-development)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## TLDR - option 1 - docker

Set the wildcard test license environment variables so that docker compose knows of them.

```sh
# e.g. using base64 to cover line breaks, etc
# cat license.key | base64 -w0
# cat license.cert | base64 -w0
export CASC_VALIDATION_LICENSE_KEY_B64=$(cat license.key | base64 -w0)
export CASC_VALIDATION_LICENSE_CERT_B64=$(cat license.cert | base64 -w0)
```

(optional) Create a cache volume to hold the war files, etc

```sh
docker volume create bundleutils-cache
```

Start a container with a cache volume

```sh
docker run -d -v bundleutils-cache:/opt/bundleutils/.cache \
-e CASC_VALIDATION_LICENSE_KEY_B64="$CASC_VALIDATION_LICENSE_KEY_B64" \
-e CASC_VALIDATION_LICENSE_CERT_B64="$CASC_VALIDATION_LICENSE_CERT_B64" \
--name bundleutils \
--entrypoint bash \
ghcr.io/tsmp-falcon-platform/ci-bundle-utils \
-c "tail -f /dev/null"
```

Exec into the container

```sh
docker exec -it bundleutils bash
```

Think about setting the licence(!) if not done so above. Then, run the example script and follow the instructions:

```sh
./examples/run-all.sh
```

Stop and clean up...

```sh
docker rm -f bundleutils
```

## TLDR - option 2 - docker compose

Set the wildcard test license environment variables so that docker compose knows of them.

```sh
# e.g. using base64 to cover line breaks, etc
# cat license.key | base64 -w0
# cat license.cert | base64 -w0
export CASC_VALIDATION_LICENSE_KEY_B64=$(cat license.key | base64 -w0)
export CASC_VALIDATION_LICENSE_CERT_B64=$(cat license.cert | base64 -w0)
```

Start a container with a cache volume using the provided

```sh
docker compose up -d
```

Exec into the container

```sh
docker exec -it ci-bundle-utils-bundleutils-1 bash
```

Think about setting the licence(!) if not done so above. Then, run the example script and follow the instructions:

```sh
./examples/run-all.sh
```

Stop and clean up...

```sh
docker compose down
```

## TLDR - option 3 - using a shared local cache

The default docker compose file creates a docker volume for the cache, but maybe you want to use your local file system.

This would allow you to run `bundleutils` locally and in docker, sharing the cache between both.

The main difference to the steps above would be to:

- create the local cache directory
- use the new directory in the docker compose configuration
- exec into the container as the local user instead of using the default
  - NOTE: this is only necessary if your own UID and GID differs from the default in the container (1000)

Create a local cache volume if not

```sh
mkdir -p ~/.bundleutils/cache
```

Use the local cache volume in the [docker compose configuration](./docker-compose.yaml):

```sh
  # option 2 - points to the default local directory on the host
  # for use both in the docker-compose.yaml and locally
  bundleutils-cache:
    driver: local
    driver_opts:
      type: none
      device: ~/.bundleutils/cache
      o: bind
```

Exec into the container as the local user

```sh
docker exec -it -u $(id -u ) -g $(id -g) ci-bundle-utils-bundleutils-1 bash
```

## Introduction

Initial project to provide some nice bundle utility features.

### Bundle Util Commands

Main commands:

- `fetch` to fetch the exported bundle from a given controller URL, zip file, or text file
  - defaults to the `core-casc-export-*.zip` in the current directory
- `transform` to transform the exported bundle
  - takes one or more transformation configurations
- `validate` to validate a bundle against a target server
  - takes a source directory, url, username, password, etc

Special transformational commands:

- `normalize` used to help compare bundles by normalizing the values
  - a transformation based on the [normalize.yaml](./bundleutilspkg/defaults/configs/normalize.yaml)
  - can be overridden file of the same name in the current directory.
- `operationalize` used to make a bundle which is consumable by a controller or operation center
  - a transformation based on the [operationalize.yaml](./bundleutilspkg/defaults/configs/operationalize.yaml)
  - can be overridden file of the same name in the current directory.

### Test Server Commands

Special `ci-*` commands to provide local testing capabilities:

Common variables for all commands:

- The server version with either `BUNDLEUTILS_CI_VERSION` or `--ci-version`
- The server type with either `BUNDLEUTILS_CI_TYPE` or `--ci-type` (defaults to `mm`)

Individual commands:

- `ci-setup` prepares a server for local testing
  - takes a bundle directory as a source for expected plugins
  - downloads the appropriate war file
  - creates a startup bundle using
    - the plugins  the [default validation template](./bundleutilspkg/defaults/configs/validation-template) (can be overridden)
- `ci-start` starts the test server
  - starting the java process
  - saves the pid file
  - tests the authentication token
- `ci-validate` validates a bundle aginst the started server
  - takes the bundle source directory
  - returns the validation result JSON
- `ci-stop` stops the test server
  - uses the pid file from the start command above

## The `transform` Command

The `transform` command can transform a fetched bundle according to a configuration based upon:

- `patches` - a set of patches as shown by https://jsonpatch.com/
- `credentials` - the ability to replace encrypted credentials with a given or autogenerated text
- `splits` - split configuration files (typically `items.yaml` or `jenkins.yaml`) into smaller chunked configuration files.
- `substitutions` - generic regex substitutions for post processing config files.

It can take multiple transformation files which it merges together before applying.

```sh
❯ bundleutils transform --help
Usage: bundleutils transform [OPTIONS]

  Transform using a custom transformation config.

Options:
  -l, --log-level TEXT   The log level (or use BUNDLEUTILS_LOG_LEVEL).
  -t, --target-dir TEXT  The target directory for the YAML documents (or use
                         BUNDLEUTILS_TARGET_DIR). Defaults to the source
                         directory suffixed with -transformed.
  -s, --source-dir TEXT  The source directory for the YAML documents (or use
                         BUNDLEUTILS_TARGET_DIR).
  -c, --config TEXT      The transformation config(s) (or use
                         BUNDLEUTILS_TRANSFORMATION).
  --help                 Show this message and exit.
```

## Examples

Create a docker image:

```sh
docker buildx build -t bundle-utils:dev .
```

### Non-Interactive Standard Workflow

This example will analyse a downloaded zip file.

Create a temporary directory and navigate into it:

```sh
cd $(mktemp -d)
```

Download CasC export zip file:

```sh
❯ ls -1
core-casc-export-admin-controller.zip
```

Run `fetch` command with mounted `pwd`:

```sh
❯ docker run -v $(pwd):/work -w /work -u $(id -u):$(id -g) --rm bundle-utils:dev fetch
INFO:root:Found core-casc-export-*.zip file: core-casc-export-admin-controller.zip
INFO:root:Wrote target/docs/bundle.yaml
INFO:root:Wrote target/docs/items.yaml
INFO:root:Wrote target/docs/jenkins.yaml
INFO:root:Wrote target/docs/plugin-catalog.yaml
INFO:root:Wrote target/docs/plugins.yaml
INFO:root:Wrote target/docs/rbac.yaml
```

Run `normalize` command with mounted `pwd`:

```sh
❯ docker run -v $(pwd):/work -w /work -u $(id -u):$(id -g) --rm bundle-utils:dev normalize
INFO:root:Processing config: /usr/local/lib/python3.12/site-packages/bundleutilspkg/configs/normalize.yaml
INFO:root:Transforming target/docs to target/docs-normalized
INFO:root:Applying patch to target/docs-normalized/jenkins.yaml
INFO:root:Applying JSON patch to target/docs-normalized/jenkins.yaml
INFO:root:Applying cred replacements to target/docs-normalized/jenkins.yaml
INFO:root:Applying JSON patch to target/docs-normalized/jenkins.yaml
INFO:root:Applying JSON patch to target/docs-normalized/jenkins.yaml
INFO:root:Applying JSON patch to target/docs-normalized/jenkins.yaml
WARNING:root:Found a non-credential string (no id found) that needs to be replaced at path: /unclassified/mailer/authentication/password
INFO:root:Applying JSON patch to target/docs-normalized/jenkins.yaml
INFO:root:Applying cred replacements to target/docs-normalized/items.yaml
INFO:root:Writing bundle to target/docs-normalized/bundle.yaml
```

Run `operationalize` command with mounted `pwd`:

```sh
❯ docker run -v $(pwd):/work -w /work -u $(id -u):$(id -g) --rm bundle-utils:dev operationalize
INFO:root:Processing config: /usr/local/lib/python3.12/site-packages/bundleutilspkg/configs/operationalize.yaml
INFO:root:Transforming target/docs-normalized to target/docs-operationalized
INFO:root:Applying patch to target/docs-operationalized/jenkins.yaml
INFO:root:Applying JSON patch to target/docs-operationalized/jenkins.yaml
INFO:root:Applying JSON patch to target/docs-operationalized/jenkins.yaml
INFO:root:Applying cred replacements to target/docs-operationalized/jenkins.yaml
INFO:root:Applying cred replacements to target/docs-operationalized/items.yaml
INFO:root:Writing bundle to target/docs-operationalized/bundle.yaml
```

Check the differences between the various target directories:

```sh
❯ ls -1 target
docs
docs-normalized
docs-operationalized
```

### Interactive Custom Transformation

Create a temporary container:

```sh
docker run -u $(id -u):$(id -g) --entrypoint bash --rm -it bundle-utils:dev
```

Fetch an exported bundle:

```sh
bundle-user@89f38e7b7f8c:/app$ bundleutils fetch --path examples/bundlecontent.yaml
INFO:root:Wrote target/docs/bundle.yaml
INFO:root:Wrote target/docs/jenkins.yaml
INFO:root:Wrote target/docs/plugins.yaml
INFO:root:Wrote target/docs/rbac.yaml
INFO:root:Wrote target/docs/items.yaml
```

Transform the bundle:

```sh
bundle-user@89f38e7b7f8c:/app$ bundleutils transform -c examples/transformations.yaml -s target/docs
INFO:root:Processing config: examples/transformations.yaml
INFO:root:Applying patch to target/docs-transformed/jenkins.yaml
INFO:root:Applying JSON patch to target/docs-transformed/jenkins.yaml
INFO:root:Applying JSON patch to target/docs-transformed/jenkins.yaml
INFO:root:Applying patch to target/docs-transformed/bundle.yaml
INFO:root:Applying JSON patch to target/docs-transformed/bundle.yaml
...
...
INFO:root:Loading existing target file target/docs-transformed/jenkins.kubernetes.yaml
INFO:root:Saving target file target/docs-transformed/jenkins.kubernetes.yaml
INFO:root:Writing bundle to target/docs-transformed/bundle.yaml
```

Check the changes:

```sh
bundle-user@89f38e7b7f8c:/app$ find target/docs-transformed
target/docs-transformed
target/docs-transformed/items.casc-test-1.yaml
target/docs-transformed/jenkins.controllerLifecycleNotifications.yaml
target/docs-transformed/items.casc-test-2.yaml
target/docs-transformed/items.yaml
target/docs-transformed/jenkins.beekeeper.yaml
target/docs-transformed/items.controllers.yaml
target/docs-transformed/jenkins.cloudBeesCasCServer.yaml
target/docs-transformed/jenkins.jenkins.clouds.yaml
target/docs-transformed/items.admin.yaml
target/docs-transformed/plugins.yaml
target/docs-transformed/bundle.yaml
target/docs-transformed/jenkins.yaml
target/docs-transformed/jenkins.credentials.yaml
target/docs-transformed/jenkins.advisor.yaml
target/docs-transformed/jenkins.support.yaml
target/docs-transformed/rbac.yaml
target/docs-transformed/jenkins.kubernetes.yaml
```

The `bundle.yaml` has been updated to reflect the new structure and the version is based on the md5sum of all files.

```sh
bundle-user@89f38e7b7f8c:/app$ cat target/docs-transformed/bundle.yaml
apiVersion: '1'
id: base
description: This is an autogenerated bundle from the base transformation
version: 84f13a8ff6e30e59639ea266456dc64e
jcasc:
- jenkins.yaml
- jenkins.advisor.yaml
- jenkins.beekeeper.yaml
- jenkins.cloudBeesCasCServer.yaml
- jenkins.controllerLifecycleNotifications.yaml
- jenkins.credentials.yaml
- jenkins.jenkins.clouds.yaml
- jenkins.kubernetes.yaml
- jenkins.support.yaml
plugins:
- plugins.yaml
rbac:
- rbac.yaml
items:
- items.yaml
- items.admin.yaml
- items.casc-test-1.yaml
- items.casc-test-2.yaml
- items.controllers.yaml
```

## Local Development

To run locally:

```sh
# create a virtual environment
python -m venv .venv

# install dependencies in edit mode
pip install -e bundleutilspkg

# activate environment
source .venv/bin/activate

# activate shell completion
bundleutils completion -s ... # e.g. bash or zsh
```
