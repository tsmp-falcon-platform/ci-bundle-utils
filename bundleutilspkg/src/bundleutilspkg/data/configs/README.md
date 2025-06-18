# Transformation Process

The transformation from exported bundle to a more sanitized form uses transformation instructions.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Includes](#includes)
- [Patches](#patches)
  - [Advanced patching (using selectors)](#advanced-patching-using-selectors)
- [Credentials](#credentials)
- [Splits](#splits)
- [Substitutions](#substitutions)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

The process is executed in the following order:

1. **Includes**: Merge additional configuration files as specified before continuing.
2. **Patches**: Apply JSON patches to add, modify or remove specific configuration elements.
3. **Credentials**: Replace credentials with environment variables or explicit values.
4. **Splits**: Split configuration files into multiple files based on patterns or paths.
5. **Substitutions**: Perform pattern-based replacements within the configuration files.

## Includes

This phase allows you to merge configuration from other files before applying any changes.

The YAML under `includes` lists files (like `base.yaml`) whose contents will be merged into your main configuration.
This is useful for sharing common settings or base configurations across multiple environments or projects.

Think of this like importing a header file in C++ (`#include "base.h"`), but for configuration.

> [!TIP]
> See the results of any merge by running your `audit` or `transform` command with the `--dry-run` flag.

```yaml
# This section allows you to define other files to be merged.
includes:
  # Include the base configuration
  - base.yaml
```

## Patches

After merging any `includes`, you can modify the combined configuration using patches.

The `patches` section uses JSON Patch (https://jsonpatch.com/).

```yaml
# Patches based upon https://jsonpatch.com/
patches:
  jenkins.yaml:
    # add a system message
  - op: replace
    path: /jenkins/systemMessage
    value: Hello from bundleutils!
    # you may want to keep this if you have a license file
  - op: remove
    path: /license
    # these labels are dynamic based on the agents available
  - op: remove
    path: /jenkins/labelAtoms
    # remove the operationsCenterRootAction because it is provided by the OC
  - op: remove
    path: /unclassified/operationsCenterRootAction
```

### Advanced patching (using selectors)

A simple selectors feature has also been included for navigating lists, etc.

> [!TIP]
> More examples can be found under the examples section.

```yaml
  jenkins.yaml:
    # Replace the password of the deployerCredentialsConfig of all jfrogInstances
  - op: replace
    path: /unclassified/artifactoryBuilder/jfrogInstances/*/deployerCredentialsConfig/password
    value: new-pass
    # Replace the username of the deployerCredentialsConfig of jFrogServer1 and jFrogServer2
  - op: replace
    path: /unclassified/artifactoryBuilder/jfrogInstances/{{select "instanceId=jFrogServer1"}}/deployerCredentialsConfig/username
    value: new-user1
    # Replace the username of the deployerCredentialsConfig of jFrogServer2
  - op: replace
    path: /unclassified/artifactoryBuilder/jfrogInstances/{{select "instanceId=jFrogServer2"}}/deployerCredentialsConfig/username
    value: new-user2

  items.yaml:
    # Disable the base-drift pipeline
  - op: replace
    path: /items/{{select "kind=pipeline,name=base-drift"}}/disabled
    value: true
```

## Credentials

The `credentials` section traverses the files specified and replaces any credentials found with its env var equivalent.

> [!WARN]
> We do not want to leave encrypted values in the bundle, even if they are encrypted.

This allows you to provide credentials as a volume mount or secret and have them recognised on a bundle reload.

> [!TIP]
> Setting values explicitly is also supported.

```yaml
# Replace credentials with references to variables
# Autosetting:
# - github-token-ro/password -> GITHUB_TOKEN_RO_PASSWORD
# - github-token-rw/password -> GITHUB_TOKEN_RW_PASSWORD
# Explicit:
# - id: github-token-ro
#   password: ${MY_READ_TOKEN}
# - id: github-org-hooks-shared-secret
#   secret: ${MY_SHARED_ORGS_HOOKS_SECRET}
credentials:
  jenkins.yaml:
  - id: github-token-ro
    password: "${MY_READ_TOKEN}"
  - id: github-token-rw
    password: "${MY_WRITE_TOKEN}"
  items.yaml:
  - id: test-folder-cred
    password: "${MY_FOLDER_TOKEN}"
```

## Splits

After sanitizing the bundle, you may want to split your configuration into smaller sections.

The `splits` section provides a way to split both the `jenkins.yaml` and `items.yaml`

> [!TIP]
> Experiment with wildcards `paths` or `patterns` fields.


```yaml
splits:
  # Split by name on regex (auto takes each item separately)
  items:
    items.yaml:
    - target: auto
      patterns: ['casc-test-.*']
    - target: controllers.yaml
      patterns: ['controller-.*']
    - target: delete
      patterns: ['test-fs']
  # Split by path whereby target can take 'auto', 'delete', or the specific file name:
  #   'auto' takes each item separately, replacing '/' with '.'
  #   'delete' deletes the file completely
  jcasc:
    jenkins.yaml:
    - target: auto
      # Split clouds and artifactoryBuilder into separate files
    - target: auto
      paths:
      - jenkins/clouds
      - unclassified/artifactoryBuilder
      # Split the kubernetes stuff into its own file
    - target: kubernetes.yaml
      paths:
      - masterprovisioning
      - kube
      # Delete all other sections
    - target: delete
      paths:
      - /*
```

## Substitutions

This can be used as a backdoor to replace anything that may not be covered in the previous sections.

```yaml
# Replace all instances of 'pattern' with 'value' in the yaml files
substitutions: {}
  jenkins.yaml:
  - pattern: cloudbees/cloudbees-core-agent:[0-9\.]+
    value: cloudbees/cloudbees-core-agent:${readFile:/var/jenkins_home/jenkins.install.InstallUtil.lastExecVersion}
```
