# Running in docker

If you wish to run this in docker directly, folow the steps below.

Checkout this repository and use the provided Makefile targets.

Alternatively,

## Create Cache Volume

Create and manage the Docker volume named `bundleutils-cache`:

```sh
docker volume create bundleutils-cache
```

## Pulling the Image

Ensure you have the latest version of the image:

```sh
docker pull ghcr.io/tsmp-falcon-platform/ci-bundle-utils
```

## Running the Main Service: `bundleutils`

Start the bundleutils service using the following Docker command.

The command:

- starts the bundleutils container
- contains optional variables for the Jenkins user and token
- contains optional variables for the test server wildcard license
- adds a workspace volume using the current directory
- ensures workspace is owned by your UID and GID

```sh
docker run \
  -d \
  -v bundleutils-cache:/opt/bundleutils/.cache \
  --name bundleutils \
  -p 8080:8080 \
  -p 8081:8081 \
  -e BUNDLEUTILS_USERNAME="${BUNDLEUTILS_USERNAME:-}" \
  -e BUNDLEUTILS_PASSWORD="${BUNDLEUTILS_PASSWORD:-}" \
  -e CASC_VALIDATION_LICENSE_KEY_B64="${CASC_VALIDATION_LICENSE_KEY_B64:-}" \
  -e CASC_VALIDATION_LICENSE_CERT_B64="${CASC_VALIDATION_LICENSE_CERT_B64:-}" \
  -e BUNDLE_UID=$(id -u) \
  -e BUNDLE_GID=$(id -u) \
  -v $(pwd):/workspace \
  -w /workspace \
  ghcr.io/tsmp-falcon-platform/ci-bundle-utils \
  -c "tail -f /dev/null"
```
