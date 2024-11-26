# Bundle Bootstrapping

See [Bundle Profiles](./bundle-profiles.md) for more information on the `bundle-profiles.yaml` file.

This page will show you how to adding bundle configurations to the `bundle-profiles.yaml`.

Bootsptrapping allows us to bootstrap newly created instances into our repository.

## Example - `bootsptrap`

Given the following `bundle-profiles.yaml` with two pre-defined configurations or profiles.

- oc-common (common to all Operation Centers)
- controller-common (common to most controllers)

```yaml
profiles:
  oc-common: &oc-common
    BUNDLEUTILS_CI_TYPE: oc
    BUNDLEUTILS_CI_JAVA_OPTS: >-
      -Djenkins.security.SystemReadPermission=true
      -Djenkins.security.ManagePermission=true
      -Dhudson.security.ExtendedReadPermission=true
    BUNDLEUTILS_TRANSFORM_CONFIGS: >-
      transformations/remove-dynamic-stuff.yaml
      transformations/add-local-users.yaml
      transformations/split-casc-local-jobs.yaml
      transformations/oc-common.yaml

  controller-common: &controller-common
    BUNDLEUTILS_CI_TYPE: mm
    BUNDLEUTILS_CI_VERSION: 2.452.3.2
    BUNDLEUTILS_CI_JAVA_OPTS: >-
      -Djenkins.security.SystemReadPermission=true
      -Djenkins.security.ManagePermission=true
      -Dhudson.security.ExtendedReadPermission=true
    BUNDLEUTILS_TRANSFORM_CONFIGS: >-
      transformations/remove-dynamic-stuff.yaml
      transformations/add-local-users.yaml
      transformations/split-casc-local-jobs.yaml
      transformations/controllers-common.yaml

bundles: {}
```

### Use Case 1 - URL and Version Known

Running the following command would result in an entry being added for controller-a

```sh
❯ export JENKINS_URL=http://locahost.jenkins.me
❯ export BUNDLEUTILS_CI_VERSION=9.9.9.9
❯ export BUNDLEUTILS_BOOTSTRAP_PROFILE=controller-common
bundleutils bootstrap -s bundles/controller-bundles/controller-a
INFO:root:No bundle config found for controller-d. Adding it to the bundles
INFO:root:Creating an empty bundles/controller-bundles/controller-d/bundle.yaml

❯ tail bundle-profiles.yaml
  ...
  ...
  controller-a:
    <<: *controller-common
    BUNDLEUTILS_JENKINS_URL: http://locahost.jenkins.me
    BUNDLEUTILS_CI_VERSION: 9.9.9.9
```

### Use Case 2 - Running on the host server

If we were to run the bootstrap command on the actual CloudBees CI server, the URL and Version of CI can be derived.

In this case, only the profile is needed.

```sh
❯ export BUNDLEUTILS_BOOTSTRAP_PROFILE=controller-common
bundleutils bootstrap -s bundles/controller-bundles/controller-a
INFO:root:No bundle config found for controller-d. Adding it to the bundles
INFO:root:Creating an empty bundles/controller-bundles/controller-d/bundle.yaml

❯ tail bundle-profiles.yaml
  ...
  ...
  controller-a:
    <<: *controller-common
    BUNDLEUTILS_JENKINS_URL: https://controller-a.eks.sboardwell.aws.ps.beescloud.com
    BUNDLEUTILS_CI_VERSION: 2.452.3.2
```

### Use Case 3 - Updating

If the bundle is already present, an error will be thrown

```sh
❯ JENKINS_URL=http://locahost.jenkins.me BUNDLEUTILS_CI_VERSION=9.9.9.9 BUNDLEUTILS_BOOTSTRAP_PROFILE=controller-common bundleutils bootstrap -s bundles/controller-bundles/controller-d
ERROR:root:Bundle config for controller-d already exists. Please check, then either use update or remove it first.
```

In this case, it is possible to update the entry instead using `BUNDLEUTILS_BOOTSTRAP_UPDATE=true` or the `--update` option.

```sh
❯ export JENKINS_URL=http://locahost.jenkins.me
❯ export BUNDLEUTILS_CI_VERSION=1.1.1.1
❯ export BUNDLEUTILS_BOOTSTRAP_PROFILE=controller-common
❯ export BUNDLEUTILS_BOOTSTRAP_UPDATE=true
❯ bundleutils bootstrap -s bundles/controller-bundles/controller-d
INFO:root:Bundle config for controller-d already exists. Updating it.
INFO:root:The bundle yaml already exists bundles/controller-bundles/controller-d/bundle.yaml

❯ tail bundle-profiles.yaml
  ...
  ...
  controller-a:
    <<: *controller-common
    BUNDLEUTILS_JENKINS_URL: http://locahost.jenkins.me
    BUNDLEUTILS_CI_VERSION: 1.1.1.1                      # <-- UPDATED
```
