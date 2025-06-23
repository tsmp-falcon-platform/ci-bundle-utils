# Tutorials

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Prerequisites](#prerequisites)
  - [Minimum Required Permissions](#minimum-required-permissions)
  - [Start a container](#start-a-container)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

Here are a list of 5 minute tutorials to get you started.

Most tutorials require the following prerequisites.

## Prerequisites

- **TARGET URL:** One or more target URL's (controller or operations center)
- **PLUGINS:** The following plugins are installed:
  - On both: `cloudbees-casc-client`
  - On operations center: `cloudbees-casc-items-server`
  - On controller: `cloudbees-casc-items-controller`
- **CREDENTIALS:** A valid username and corresponding API token, referenced below as:
  - `BUNDLEUTILS_USERNAME`
  - `BUNDLEUTILS_PASSWORD`

### Minimum Required Permissions

The minimum set of permissions needed for the user are as follows:

```mono
CloudBees CasC Permissions/Administer
CloudBees CasC Permissions/Checkout
CloudBees CasC Permissions/Item
CloudBees CasC Permissions/Read
CloudBees CasC Permissions/ReadCheckout
Agent/ExtendedRead
Overall/Read
Overall/SystemRead
Job/ExtendedRead
View/Read
```

In RBAC, this would look like (please ignore the ordering - it came out this way):

```yaml
removeStrategy:
  rbac: SYNC
roles:
- permissions:
  - hudson.model.Hudson.Read
  - com.cloudbees.jenkins.plugins.casc.permissions.CascPermission.Item
  - hudson.model.View.Read
  - hudson.model.Hudson.SystemRead
  - hudson.model.Computer.ExtendedRead
  - hudson.model.Item.ExtendedRead
  - com.cloudbees.jenkins.plugins.casc.permissions.CascPermission.Administer
  name: validate-casc
```

> [!NOTE]
> System properties can be used to enable the [Overall/SystemRead](https://www.jenkins.io/doc/book/managing/system-properties/#jenkins-security-systemreadpermission) and [Computer/ExtendedRead and Item/ExtendedRead](https://www.jenkins.io/doc/book/managing/system-properties/#hudson-security-extendedreadpermission) permissions.
>
> If you do not have the SystemRead available, `hudson.model.Hudson.Administer` will be needed.

### Start a container

Prepare cache and image.

```sh
{
  # create a volume if needed
  docker volume inspect bundleutils-cache > /dev/null 2>&1 || docker volume create bundleutils-cache
  # ensure latest image
  docker pull ghcr.io/tsmp-falcon-platform/ci-bundle-utils
}
```

If you are not validating existing bundles, start a simple container with the cache volume:

```sh
docker run --rm -it --name bundleutils \
  -v bundleutils-cache:/opt/bundleutils/.cache \
  -e BUNDLEUTILS_USERNAME="${BUNDLEUTILS_USERNAME:-}" \
  -e BUNDLEUTILS_PASSWORD="${BUNDLEUTILS_PASSWORD:-}" \
  ghcr.io/tsmp-falcon-platform/ci-bundle-utils \
  bash
```

If you are validating existing bundles, mount your CWD workspace accordingly:

```sh
docker run --rm -it --name bundleutils \
  -v bundleutils-cache:/opt/bundleutils/.cache \
  -e BUNDLEUTILS_USERNAME="${BUNDLEUTILS_USERNAME:-}" \
  -e BUNDLEUTILS_PASSWORD="${BUNDLEUTILS_PASSWORD:-}" \
  -e BUNDLE_UID=$(id -u) \
  -e BUNDLE_GID=$(id -u) \
  -v $(pwd):/workspace \
  -w /workspace \
  ghcr.io/tsmp-falcon-platform/ci-bundle-utils \
  bash
```
