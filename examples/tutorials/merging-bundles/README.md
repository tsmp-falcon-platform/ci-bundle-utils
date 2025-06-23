# Merging Challenge - BETA

> [!WARNING]
> There are tests in place and this works with the majority of known configurations.
> However, it is impossible to test ALL available config snippets in ALL plugins.

Due to the `WARNING` above, the merge config (instructions as to how the bundles are merged) can be extended.

For more information, see the help page.

```sh
❯ bundleutils merge-bundles --help
Usage: bundleutils merge-bundles [OPTIONS]

...
...

  -m, --config FILE               An optional custom merge config file if needed (BUNDLEUTILS_MERGE_CONFIG)
```

## Assumptions

- You can run `bundleutils`
- You have some bundles you wish to merge.

## Merging Bundles

Seen as an alternative to the operations center version of merging, but:

- performing a deep merge as opposed to just adding multiple files.
- will merge lists based on specific keys (name of cloud, etc)

See [the merge-bundles test resource](../../../bundleutilspkg/tests/resources/merge-bundles) for example values.

Example of merging the `base` and `child1` bundles into `/tmp/merged-bundle`:

```sh
bundleutils merge-bundles -b /opt/bundleutils/.app/bundleutilspkg/tests/resources/merge-bundles/base -b /opt/bundleutils/.app/bundleutilspkg/tests/resources/merge-bundles/child1 -o /tmp/merged-bundle
```

Example output:

```sh
❯ bundleutils merge-bundles -b /opt/bundleutils/.app/bundleutilspkg/tests/resources/merge-bundles/base -b /opt/bundleutils/.app/bundleutilspkg/tests/resources/merge-bundles/child1 -o /tmp/merged-bundle
INFO:root:Using the following merge configs:
dict_custom_keys:
  jenkins.clouds.kubernetes: name
dict_strategy_config:
  jenkins.primaryView: replace
list_strategy_config:
  jenkins.clouds: append
  jenkins.clouds.kubernetes[*].kubernetes.templates: merge_key:name
  jenkins.globalNodeProperties: append
  jenkins.globalNodeProperties.envVars.env: merge_key:key
  support.automatedBundleConfiguration.componentIds: append
  plugins: merge_key:id
  items: merge_key:name
do_not_append:
  jenkins.globalNodeProperties:
  - envVars

INFO:root:Merging parent file: bundleutilspkg/tests/resources/merge-bundles/base/jenkins.yaml with child file: bundleutilspkg/tests/resources/merge-bundles/child1/jenkins.yaml
INFO:root:Deep merging path:
INFO:root:Deep merging path: jenkins
INFO:root:Deep merging path: unclassified
INFO:root:Deep merging path: unclassified.hibernationConfiguration
INFO:root:Deep merging path: unclassified.hibernationConfiguration.activities
...
...
...
INFO:root:Deep merging path: plugins[workflow-aggregator].id
INFO:root:Deep merging path: plugins[workflow-cps-checkpoint]
INFO:root:Deep merging path: plugins[workflow-cps-checkpoint].id
INFO:root:Deep merging path: plugins[child1]
INFO:root:Writing section: plugins to /tmp/merged-bundle/plugins.yaml
INFO:root:Updating bundle in /tmp/merged-bundle
INFO:root:Found exact match for jcasc: /tmp/merged-bundle/jenkins.yaml
INFO:root:File for jcasc: /tmp/merged-bundle/jenkins.yaml
INFO:root:Found exact match for items: /tmp/merged-bundle/items.yaml
INFO:root:File for items: /tmp/merged-bundle/items.yaml
INFO:root:Found exact match for plugins: /tmp/merged-bundle/plugins.yaml
INFO:root:File for plugins: /tmp/merged-bundle/plugins.yaml
INFO:root:Updated version to ae6255a3-15e2-9cba-31f2-820e31a5cd51
INFO:root:Wrote /tmp/merged-bundle/bundle.yaml
```

## Merging Yaml Files

You can also merge individual files.

Example of merging the `parent` and `child` plugins into `/tmp/merged-plugins.yaml`:

```sh
❯ bundleutils merge-yamls -f bundleutilspkg/tests/resources/plugins/parent.yaml -f bundleutilspkg/tests/resources/plugins/child.yaml -o /tmp/merged-plugins.yaml
INFO:root:Using the following merge configs:
dict_custom_keys:
  jenkins.clouds.kubernetes: name
dict_strategy_config:
  jenkins.primaryView: replace
list_strategy_config:
  jenkins.clouds: append
  jenkins.clouds.kubernetes[*].kubernetes.templates: merge_key:name
  jenkins.globalNodeProperties: append
  jenkins.globalNodeProperties.envVars.env: merge_key:key
  support.automatedBundleConfiguration.componentIds: append
  plugins: merge_key:id
  items: merge_key:name
do_not_append:
  jenkins.globalNodeProperties:
  - envVars

INFO:root:Merging parent file: bundleutilspkg/tests/resources/plugins/parent.yaml with child file: bundleutilspkg/tests/resources/plugins/child.yaml
INFO:root:Deep merging path:
INFO:root:Deep merging path: plugins
INFO:root:Deep merging path: plugins[cloudbees-casc-client]
INFO:root:Deep merging path: plugins[cloudbees-casc-client].id
INFO:root:Deep merging path: plugins[cloudbees-casc-client].version
INFO:root:Deep merging path: plugins[cloudbees-casc-items-controller]
INFO:root:Deep merging path: plugins[cloudbees-casc-items-controller].id
INFO:root:Deep merging path: plugins[cloudbees-github-reporting]
INFO:root:Deep merging path: plugins[cloudbees-github-reporting].id
INFO:root:Deep merging path: plugins[beer]
```

Merged plugins.yaml now contains the child version of the plugin:

```sh
❯ grep -B1 child /tmp/merged-plugins.yaml
- id: cloudbees-casc-client
  version: 1.0.0-child
```
