# Validating existing bundles

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Prerequisites](#prerequisites)
- [Validation Simple Bundles](#validation-simple-bundles)
- [Validation With Inheritance](#validation-with-inheritance)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Prerequisites

See the common [prerequisites](../README.md#prerequisites).

## Validation Simple Bundles

Run the commands to validate your bundle, for example:

```sh
bundleutils validate --url http://ci.target.acme.org/default-controller --source-dir path/to/my/bundle
```

If your bundle is named after the controller, you can remove the `--source-dir` option.

```sh
bundleutils validate --url http://ci.target.acme.org/default-controller
```

Example output:

```sh
$ bundleutils validate --url http://ci.target.acme.org/default-controller
INFO:root:Validating bundle in default-controller against http://ci.target.acme.org/default-controller/casc-bundle-mgnt/casc-bundle-validate
{
  "valid": true,
  "validation-messages": [
    "INFO - [STRUCTURE] - [FileSystemBundleValidator] All files indicated in the bundle exist and have the correct type.",
    "INFO - [DESCVAL] - [DescriptorValidator] All files referenced in the descriptor are folders or yaml files.",
    "INFO - [VERSIONVAL] - [VersionValidator] Version correctly indicated in bundle.yaml.",
    "INFO - [APIVAL] - [ApiValidator] apiVersion correctly indicated in bundle.yaml.",
    "INFO - [JCASCSTRATEGY] - [JcascMergeStrategyValidator] No (optional) jcascMergeStrategy defined in the bundle.",
    "INFO - [ITEMSTRATEGY] - [ItemRemoveStrategyValidator] No (optional) itemRemoveStrategy defined in the bundle.",
    "INFO - [CONTVAL] - [ContentBundleValidator] All files specified in the bundle exist and no unreferenced files indicated.",
    "INFO - [SCHEMA] - All YAML files validated correctly against their corresponding schemas",
    "INFO - [CATALOGVAL] - [PluginCatalogInOCValidator] Plugin catalog is supported.",
    "INFO - [PLUGINVAL] - [PluginsToInstallValidator] All plugins can be installed.",
    "INFO - [CATALOGVAL] - [MultipleCatalogFilesValidator] Just one file defining the plugin catalog.",
    "WARNING - [ITEMS] - The items.yaml file cannot be properly parsed:\n- Impossible to parse item new_org_folder of type organizationFolder. Reason: Organization folder must have one navigator. Found none for organization folder named new_org_folder. Aborting\nPlease check the items format. If any property cannot be parsed, verify the required plugin is included in the plugins.yaml file.",
    "INFO - [JCASC] - [JCasCValidator] All configurations validated successfully.",
    "INFO - [CATALOGVAL] - [PluginCatalogValidator] All plugins in catalog were added to the envelope",
    "INFO - [PLUGINVAL] - [PluginsToInstallValidator] All plugins can be installed.",
    "INFO - [RBAC] - [RbacValidator] RBAC configuration validated successfully."
  ]
}
ERROR: Validation failed with warnings
```

## Validation With Inheritance

If your bundles use inheritance, you can use the `validate-effective` command.

Getting the effective bundle requires an operations center URL.

Run the commands to validate your bundle, for example:

```sh
bundleutils validate-effective --url http://ci.target.acme.org/default-controller --oc-url http://ci.target.acme.org/cjoc --source-dir path/to/my/bundle
```

If your bundle is named after the controller, you can remove the `--source-dir` option.

```sh
bundleutils validate-effective --url http://ci.target.acme.org/default-controller --oc-url http://ci.target.acme.org/cjoc
```

Example output:

```sh
$ bundleutils validate-effective --url http://ci.target.acme.org/default-controller --oc-url http://ci.target.acme.org/cjoc
INFO:root:Zipped all bundles to /workspace/test-bundles/target/validate_effective/default-controller/all-bundles.zip
INFO:root:Requesting effective bundle from OC at http://ci.target.acme.org/cjoc with path /casc-bundle/get-effective-bundle?bundle=test-bundles/default-controller
INFO:root:Wrote response to /workspace/test-bundles/target/validate_effective/default-controller/effective-bundle-default-controller.zip
INFO:root:Effective bundle zip created at /workspace/test-bundles/target/validate_effective/default-controller/effective-bundle-default-controller.zip
INFO:root:Effective bundle extracted to /workspace/test-bundles/target/validate_effective/default-controller/effective-bundle-default-controller
INFO:root:Validating bundle in /workspace/test-bundles/target/validate_effective/default-controller/effective-bundle-default-controller against http://ci.target.acme.org/default-controller/casc-bundle-mgnt/casc-bundle-validate
{
  "valid": true,
  "validation-messages": [
    "INFO - [STRUCTURE] - [FileSystemBundleValidator] All files indicated in the bundle exist and have the correct type.",
    "INFO - [DESCVAL] - [DescriptorValidator] All files referenced in the descriptor are folders or yaml files.",
    "INFO - [VERSIONVAL] - [VersionValidator] Version correctly indicated in bundle.yaml.",
    "INFO - [APIVAL] - [ApiValidator] apiVersion correctly indicated in bundle.yaml.",
    "INFO - [JCASCSTRATEGY] - [JcascMergeStrategyValidator] No (optional) jcascMergeStrategy defined in the bundle.",
    "INFO - [ITEMSTRATEGY] - [ItemRemoveStrategyValidator] No (optional) itemRemoveStrategy defined in the bundle.",
    "INFO - [CONTVAL] - [ContentBundleValidator] All files specified in the bundle exist and no unreferenced files indicated.",
    "INFO - [SCHEMA] - All YAML files validated correctly against their corresponding schemas",
    "INFO - [CATALOGVAL] - [PluginCatalogInOCValidator] Plugin catalog is supported.",
    "INFO - [PLUGINVAL] - [PluginsToInstallValidator] All plugins can be installed.",
    "INFO - [CATALOGVAL] - [MultipleCatalogFilesValidator] Just one file defining the plugin catalog.",
    "WARNING - [ITEMS] - The items/01-1750673127059.bundles.test-bundles.default-controller.items.yaml file cannot be properly parsed:\n- Impossible to parse item new_org_folder of type organizationFolder. Reason: Organization folder must have one navigator. Found none for organization folder named new_org_folder. Aborting\nPlease check the items format. If any property cannot be parsed, verify the required plugin is included in the plugins.yaml file.",
    "INFO - [JCASC] - [JCasCValidator] All configurations validated successfully.",
    "INFO - [CATALOGVAL] - [PluginCatalogValidator] All plugins in catalog were added to the envelope",
    "INFO - [PLUGINVAL] - [PluginsToInstallValidator] All plugins can be installed.",
    "INFO - [RBAC] - [RbacValidator] RBAC configuration validated successfully."
  ]
}
ERROR: Validation failed with warnings
```
