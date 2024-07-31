# Running in docker

If you wish to run this in docker directly, folow the steps below.

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

## Running the Main Service: bundleutils

Start the bundleutils service using the following Docker command:

```sh
docker run -d --name bundleutils \
  --network host \
  --user "$(id -u):$(id -g)" \
  -e BUNDLEUTILS_USERNAME="${BUNDLEUTILS_USERNAME:-}" \
  -e BUNDLEUTILS_PASSWORD="${BUNDLEUTILS_PASSWORD:-}" \
  -e CASC_VALIDATION_LICENSE_KEY_B64="${CASC_VALIDATION_LICENSE_KEY_B64:-}" \
  -e CASC_VALIDATION_LICENSE_CERT_B64="${CASC_VALIDATION_LICENSE_CERT_B64:-}" \
  -v "${BUNDLES_WORKSPACE:-.}:/workspace" \
  -v bundleutils-cache:/opt/bundleutils/.cache \
  -w "${BUNDLES_WORKSPACE:-/opt/bundleutils/work}" \
  --entrypoint "sh" \
  ghcr.io/tsmp-falcon-platform/ci-bundle-utils \
  -c "sleep infinity"
```

