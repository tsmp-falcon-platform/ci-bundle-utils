## Predefined Configs Example

Imagine the structure:

```sh
├── bundles
│   ├── controller-bundles
│   │   ├── controller-a
│   │   │   ├── bundle.yaml
│   │   │   ├── jenkins.yaml
│   │   │   └── plugins.yaml
│   │   └── env.controller-a.yaml
│   ├── oc-bundles
│   │   ├── env.oc-bundle
│   │   ├── env.oc-bundle.yaml
│   │   ├── oc-bundle
│   │   │   ├── bundle.yaml
│   │   │   ├── items.yaml
│   │   │   ├── jenkins.yaml
│   │   │   └── plugins.yaml
│   │   └── oc-bundle.transform.yaml
│   └── transformations
│       ├── add-local-users.yaml
│       ├── controllers-common.yaml
│       ├── oc-common.yaml
│       └── remove-dynamic-stuff.yaml
└── Makefile
```

### Config Auto Discovery

The `bundleutils` script will try to discover a predefined config.

A prefefined config is like a `.env` file for the bundleutils script.

- provides values for the various steps (no need to pass cli options)
- has the possible forms
  - `env.<cwd-basename>.yaml` (env vars using YAML KEY: VAL)
  - `env.<cwd-basename>` (env var in the normal KEY=VAL format)
- expected in the parent directory of the CWD

This allows us to have the configuration for `controller-a` next to the bundle for `controller-a`

```sh
├── controller-a
│   ├── bundle.yaml
│   ├── jenkins.yaml
│   └── plugins.yaml
└── env.controller-a.yaml
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

Take a look at `env.controller-a.yaml`

```yaml
BUNDLEUTILS_CI_TYPE: mm
BUNDLEUTILS_CI_VERSION: 2.452.3.2
BUNDLEUTILS_JAVA_OPTS: >-
  -Djenkins.security.SystemReadPermission=true
  -Djenkins.security.ManagePermission=true
  -Dhudson.security.ExtendedReadPermission=true
BUNDLEUTILS_JENKINS_URL: https://controller-a.eks.sboardwell.aws.ps.beescloud.com
BUNDLEUTILS_TRANSFORM_CONFIGS: >-
  ../transformations/remove-dynamic-stuff.yaml
  ../transformations/add-local-users.yaml
  ../transformations/controllers-common.yaml

BUNDLEUTILS_FETCH_TARGET_DIR: target/docs
BUNDLEUTILS_TRANSFORM_SOURCE_DIR: target/docs
BUNDLEUTILS_TRANSFORM_TARGET_DIR: controller-a
BUNDLEUTILS_SETUP_SOURCE_DIR: controller-a
BUNDLEUTILS_VALIDATE_SOURCE_DIR: controller-a
```

This would be the equivalent of running commands like...

```sh
bundleutils fetch --url ... --target-dir ...
bundleutils transform --source-dir ... --target-dir ... --config ...1 --config ...2 --config ...3
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

### Makefile

The provided `Makefile` allows us the run commands from the root directory by:

- navigating to the bundle directory
- performing the commands

```sh
❯ make

Usage:
  make <target>

Targets:
  %/fetch                Run bundleutils fetch in the directory '%'
  %/transform            Run bundleutils fetch in the directory '%'
  %/validate             Run all validation steps in the directory '%'
  %/process              Run all validation steps in the directory '%'
  help                   Makefile Help Page
```

Example

```sh
❯ make bundles/oc-bundles/oc-bundle/transform
cd bundles/oc-bundles/oc-bundle
bundleutils transform
INFO:root:Auto env file found: /home/sboardwell/Workspace/tsmp-falcon-platform/sboardwell-bundles-drift/bundles/oc-bundles/env.oc-bundle.yaml
INFO:root:Switching directory: /home/sboardwell/Workspace/tsmp-falcon-platform/sboardwell-bundles-drift/bundles/oc-bundles
...
...
```