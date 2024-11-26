# Bundle Profiles

The `bundle-profiles.yaml` contains pre-defined configs for your cluster.

## Format

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

bundles:
  oc-bundle:
    <<: *oc-common
    BUNDLEUTILS_JENKINS_URL: https://cjoc.eks.sboardwell.aws.ps.beescloud.com
    BUNDLEUTILS_CI_VERSION: 2.462.1.3
  controller-a:
    <<: *controller-common
    BUNDLEUTILS_JENKINS_URL: http://localhost.me
    BUNDLEUTILS_CI_VERSION: 2.452.3.2
```

- the `profiles` section contains common configurations
- the `bundles` section contains the bundles themselves along with any server specific infromation and overrides.

## Example - `config`

Use the `config` command to output the configuration based on the current bundle directory.

e.g. given the configuration above, navigate to your bundle directory and call `bundleutils config`.

```sh
❯ cd bundles/controller-bundles/controller-d

❯ bundleutils config
INFO:root:Found bundle config for controller-d
INFO:root:Setting environment variable: BUNDLEUTILS_JENKINS_URL=http://locahost.jenkins.me
INFO:root:Setting environment variable: BUNDLEUTILS_CI_VERSION=9.9.9.9
INFO:root:Setting environment variable: BUNDLEUTILS_CI_TYPE=mm
INFO:root:Setting environment variable: BUNDLEUTILS_CI_JAVA_OPTS=-Djenkins.security.SystemReadPermission=true -Djenkins.security.ManagePermission=true -Dhudson.security.ExtendedReadPermission=true
INFO:root:Setting environment variable: BUNDLEUTILS_TRANSFORM_CONFIGS=transformations/remove-dynamic-stuff.yaml transformations/add-local-users.yaml transformations/split-casc-local-jobs.yaml transformations/controllers-common.yaml
INFO:root:AUTOSET environment variable: BUNDLEUTILS_FETCH_TARGET_DIR=target/docs-controller-d
INFO:root:AUTOSET environment variable: BUNDLEUTILS_TRANSFORM_SOURCE_DIR=target/docs-controller-d
INFO:root:AUTOSET environment variable: BUNDLEUTILS_TRANSFORM_TARGET_DIR=bundles/controller-bundles/controller-d
INFO:root:AUTOSET environment variable: BUNDLEUTILS_SETUP_SOURCE_DIR=bundles/controller-bundles/controller-d
INFO:root:AUTOSET environment variable: BUNDLEUTILS_VALIDATE_SOURCE_DIR=bundles/controller-bundles/controller-d
INFO:root:Evaluated configuration:
BUNDLEUTILS_CI_JAVA_OPTS=-Djenkins.security.SystemReadPermission=true -Djenkins.security.ManagePermission=true -Dhudson.security.ExtendedReadPermission=true
BUNDLEUTILS_CI_TYPE=mm
BUNDLEUTILS_CI_VERSION=9.9.9.9
BUNDLEUTILS_ENV=/path/to/the/bundles-repo/bundle-profiles.yaml
BUNDLEUTILS_FETCH_TARGET_DIR=target/docs-controller-d
BUNDLEUTILS_JENKINS_URL=http://locahost.jenkins.me
BUNDLEUTILS_SETUP_SOURCE_DIR=bundles/controller-bundles/controller-d
BUNDLEUTILS_TRANSFORM_CONFIGS=transformations/remove-dynamic-stuff.yaml transformations/add-local-users.yaml transformations/split-casc-local-jobs.yaml transformations/controllers-common.yaml
BUNDLEUTILS_TRANSFORM_SOURCE_DIR=target/docs-controller-d
BUNDLEUTILS_TRANSFORM_TARGET_DIR=bundles/controller-bundles/controller-d
BUNDLEUTILS_VALIDATE_SOURCE_DIR=bundles/controller-bundles/controller-d
```
