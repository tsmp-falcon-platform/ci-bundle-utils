## Predefined Configs Example

Imagine the structure found in [../example-bundles-repo/bundles](../examples/example-bundles-repo/bundles):

```sh
├── bundles
│   ├── bundle-profiles.yaml
│   ├── controller-bundles
│   │   ├── controller-bundle
│   │   │   └── bundle.yaml
│   │   └── Makefile
│   ├── oc-bundles
│   │   ├── Makefile
│   │   └── oc-bundle
│   │       └── bundle.yaml
│   └── transformations
│       ├── add-local-users.yaml
│       ├── controllers-common.yaml
│       ├── oc-common.yaml
│       └── remove-dynamic-stuff.yaml
└── Makefile
```

### Bundle Profiles

See [Bundle Profiles](./bundle-profiles.md) for more information on the `bundle-profiles.yaml` file.

### Bundle Bootstrapping

See [Bootstrapping](./bundle-bootstrapping.md) for more information on adding bundles to the `bundle-profiles.yaml` file.

### Config Auto Discovery

The `bundleutils` tool will look for a `bundle-profiles.yaml` containing your predefined configuration.

- Predefined config is like a `.env` file for the bundleutils script.
- Provides values for the various steps (no need to pass cli options)
- Expected in any of the previous 5 parent directories of the CWD

e.g. navigate to `/example-bundles-repo/bundles/controller-bundles/controller-bundle/` and call `bundleutils config`

```sh
❯ cd /example-bundles-repo/bundles/controller-bundles/controller-bundle
```

Call `bundleutils config`

```sh
❯ bundleutils config
INFO:root:Found bundle config for controller-bundle
INFO:root:Setting environment variable: BUNDLEUTILS_JENKINS_URL=https://cjoc.acme.org/controller-a
INFO:root:Setting environment variable: BUNDLEUTILS_CI_TYPE=mm
INFO:root:Setting environment variable: BUNDLEUTILS_CI_VERSION=2.452.3.2
INFO:root:Setting environment variable: BUNDLEUTILS_CI_JAVA_OPTS=-Djenkins.security.SystemReadPermission=true -Djenkins.security.ManagePermission=true -Dhudson.security.ExtendedReadPermission=true
INFO:root:Setting environment variable: BUNDLEUTILS_TRANSFORM_CONFIGS=transformations/remove-dynamic-stuff.yaml transformations/controllers-common.yaml
INFO:root:AUTOSET environment variable: BUNDLEUTILS_FETCH_TARGET_DIR=target/docs-controller-bundle
INFO:root:AUTOSET environment variable: BUNDLEUTILS_TRANSFORM_SOURCE_DIR=target/docs-controller-bundle
INFO:root:AUTOSET environment variable: BUNDLEUTILS_TRANSFORM_TARGET_DIR=controller-bundles/controller-bundle
INFO:root:AUTOSET environment variable: BUNDLEUTILS_SETUP_SOURCE_DIR=controller-bundles/controller-bundle
INFO:root:AUTOSET environment variable: BUNDLEUTILS_VALIDATE_SOURCE_DIR=controller-bundles/controller-bundle
INFO:root:Evaluated configuration:
BUNDLEUTILS_CI_JAVA_OPTS=-Djenkins.security.SystemReadPermission=true -Djenkins.security.ManagePermission=true -Dhudson.security.ExtendedReadPermission=true
BUNDLEUTILS_CI_TYPE=mm
BUNDLEUTILS_CI_VERSION=2.452.3.2
BUNDLEUTILS_ENV=/example-bundles-repo/bundles/bundle-profiles.yaml
BUNDLEUTILS_FETCH_TARGET_DIR=target/docs-controller-bundle
BUNDLEUTILS_JENKINS_URL=https://cjoc.acme.org/controller-a
BUNDLEUTILS_SETUP_SOURCE_DIR=controller-bundles/controller-bundle
BUNDLEUTILS_TRANSFORM_CONFIGS=transformations/remove-dynamic-stuff.yaml transformations/controllers-common.yaml
BUNDLEUTILS_TRANSFORM_SOURCE_DIR=target/docs-controller-bundle
BUNDLEUTILS_TRANSFORM_TARGET_DIR=controller-bundles/controller-bundle
BUNDLEUTILS_VALIDATE_SOURCE_DIR=controller-bundles/controller-bundle
```

Calling with `DEBUG` shows how the config is found:

```sh
❯ bundleutils --log-level DEBUG config
DEBUG:root:Set log level to: DEBUG
DEBUG:root:Searching for auto env file bundle-profiles.yaml in parent directories
DEBUG:root:Checking for env file: /example-bundles-repo/bundles/controller-bundles/controller-bundle/bundle-profiles.yaml
DEBUG:root:Checking for env file: /example-bundles-repo/bundles/controller-bundles/bundle-profiles.yaml
DEBUG:root:Checking for env file: /example-bundles-repo/bundles/bundle-profiles.yaml
DEBUG:root:Auto env file found: /example-bundles-repo/bundles/bundle-profiles.yaml
DEBUG:root:Using auto env file: /example-bundles-repo/bundles/bundle-profiles.yaml
DEBUG:root:Loading config file: /example-bundles-repo/bundles/bundle-profiles.yaml
DEBUG:root:Current working directory: /example-bundles-repo/bundles/controller-bundles/controller-bundle
DEBUG:root:Switching to the base directory of env file: /example-bundles-repo/bundles
INFO:root:Found bundle config for controller-bundle
...
...
```

This allows us to have the configuration for `controller-a` separate from the bundle `controller-a`.

```sh
└── bundles
    ├── bundle-profiles.yaml          # <-- config
    ├── controller-bundles
    │   └── controller-a              # <-- bundle
    │       └── bundle.yaml
    └── transformations               # <-- transformations
        ├── add-local-users.yaml
        ├── controllers-common.yaml
        ├── oc-common.yaml
        └── remove-dynamic-stuff.yaml
```

### Overriding Config Values

By default, configuration values cannot be overridden by environment variables of the same.

You can allow overrides by setting the `BUNDLEUTILS_ENV_OVERRIDE=1` before running the command.

e.g. normal setting

```sh
❯ bundleutils fetch
...
...
INFO:root:Setting environment variable: BUNDLEUTILS_JENKINS_URL=https://cjoc.acme.org
```

e.g. overriding with `BUNDLEUTILS_ENV_OVERRIDE=1`

```sh
❯ BUNDLEUTILS_ENV_OVERRIDE=1 \
  BUNDLEUTILS_JENKINS_URL=bla \
  bundleutils fetch
...
...
INFO:root:Overriding with env, setting: BUNDLEUTILS_JENKINS_URL=bla
```

e.g. unsuccesful override without `BUNDLEUTILS_ENV_OVERRIDE=1`

```sh
❯ BUNDLEUTILS_ENV_OVERRIDE=0 \
  BUNDLEUTILS_JENKINS_URL=bla \
  bundleutils fetch
...
...
INFO:root:Ignoring passed env, setting: BUNDLEUTILS_JENKINS_URL=https://cjoc.acme.org
```

### Reusable Transformation Files

The transformation yaml can be re-used by different bundles.

```sh
transformations
├── add-local-users.yaml
├── controllers-common.yaml
├── oc-common.yaml
└── remove-dynamic-stuff.yaml
```

### Config Example

Take a look the exploded config `controller-a.yaml`

```yaml
❯ yq 'explode(.)|.bundles."controller-a"' bundle-profiles.yaml
BUNDLEUTILS_CI_TYPE: mm
BUNDLEUTILS_CI_VERSION: 2.452.3.2
BUNDLEUTILS_CI_JAVA_OPTS: >-
  -Djenkins.security.SystemReadPermission=true -Djenkins.security.ManagePermission=true -Dhudson.security.ExtendedReadPermission=true
BUNDLEUTILS_TRANSFORM_CONFIGS: >-
  transformations/remove-dynamic-stuff.yaml transformations/controllers-common.yaml
BUNDLEUTILS_JENKINS_URL: https://cjoc.acme.org/controller-a
# These are directories to use when running fetch, transform, setup, and validate
# They are automatically deduced from the bundle if not provided
# BUNDLEUTILS_FETCH_TARGET_DIR: target/docs-controller-bundle
# BUNDLEUTILS_TRANSFORM_SOURCE_DIR: target/docs-controller-bundle
# BUNDLEUTILS_TRANSFORM_TARGET_DIR: &src_dir controller-bundles/controller-bundle
# BUNDLEUTILS_SETUP_SOURCE_DIR: *src_dir
# BUNDLEUTILS_VALIDATE_SOURCE_DIR: *src_dir
```

This would be the equivalent of running commands like...

```sh
bundleutils fetch --url ... --target-dir ...
bundleutils transform --source-dir ... --target-dir ... --config ...1.yaml --config ...2.yaml --config ...3.yaml
bundleutils ci-setup --ci-type ... --ci-version ... --source-dir ...
bundleutils ci-start --ci-type ... --ci-version ...
bundleutils ci-validate --source-dir ...
bundleutils ci-stop --ci-type ... --ci-version ...
```

Instead, we can now run...

```sh
bundleutils fetch
bundleutils transform
bundleutils ci-setup
bundleutils ci-start
bundleutils ci-validate
bundleutils ci-stop
```

### Optional Makefile

The provided `Makefile` allows us the run the above commands from the root directory by:

- navigating to the bundle directory
- performing the commands

```sh
❯ make

Usage:
  make <target>

Targets:
  run/%/update-bundle        Run bundleutils update-bundle in the directory '%'
  run/%/fetch                Run bundleutils fetch in the directory '%'
  run/%/transform            Run bundleutils fetch in the directory '%'
  run/%/refresh              Run bundleutils fetch and transform in the directory '%'

...
...
```

Example

```sh
❯ make run/bundles/oc-bundles/oc-bundle/config
cd bundles/oc-bundles/oc-bundle
bundleutils config
INFO:root:Found bundle config for oc-bundle
INFO:root:Setting environment variable: BUNDLEUTILS_JENKINS_URL=https://cjoc.acme.org/cjoc
...
...
```
