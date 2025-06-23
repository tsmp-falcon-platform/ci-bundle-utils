# Validating existing bundles

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Prerequisites](#prerequisites)
- [Assumptions](#assumptions)
- [Setup](#setup)
- [Commands](#commands)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Prerequisites

See the common [prerequisites](../README.md#prerequisites).

## Assumptions

- You have a CasC bundle available which you wish to validate.
- You have a single user wildcard license to start the test server.

## Setup

Export the wildcard test license environment variables.

```sh
# e.g. using base64 to cover line breaks, etc
# cat license.key | base64 -w0
# cat license.cert | base64 -w0
export CASC_VALIDATION_LICENSE_KEY_B64=$(cat license.key | base64 -w0)
export CASC_VALIDATION_LICENSE_CERT_B64=$(cat license.cert | base64 -w0)
```

## Commands

The validation commands expect:

- a source directory for the bundle to test
- the version of the test server
- the type of test server (operation center, modern controller, etc)

The version and type can be pulled from the URL if provided.

If your bundle is named after the controller/OC, you can also remove the `--source-dir` option.

```sh
bundleutils ci-setup    --url http://ci.target.acme.org/default-controller
bundleutils ci-start    --url http://ci.target.acme.org/default-controller
bundleutils ci-validate --url http://ci.target.acme.org/default-controller
bundleutils ci-stop     --url http://ci.target.acme.org/default-controller

```

Example output:

```sh
$ bundleutils ci-setup --url http://ci.target.acme.org/default-controller
INFO:root:Using default cloudbees image. Overwrite with environment variable BUNDLEUTILS_CB_WAR_DOWNLOAD_URL_MM
INFO:root:Using default cloudbees download URL. Overwrite with environment variable BUNDLEUTILS_CB_WAR_DOWNLOAD_URL_MM
INFO:root:Using skopeo to copy the WAR file from the Docker image cloudbees/cloudbees-core-mm:2.479.3.1
INFO:root:Skopeo copy options such as '--src-creds USR:PWD' with environment variable BUNDLEUTILS_SKOPEO_COPY_OPTS
Getting image source signatures
Copying blob ede68e582626 done
Copying blob dd4c79378820 done
Copying blob 30cadfb2ca31 done
Copying blob 6b629f60a395 done
Copying blob aa8134c9b3ab done
Copying blob b6ec4c7b7b4f done
Copying config 2368138fb5 done
Writing manifest to image destination
Storing signatures
INFO:root:Found jenkins.war in /opt/bundleutils/.cache/tar/mm/2.479.3.1/6b629f60a3957f18dd71a9c4bf20aa4271666757ff73975b09b507516fc63839. Copying to war cache directory.
INFO:root:Recreating target/ci_server_home/jenkins-home
INFO:root:Copying WAR file to target/ci_server_home/jenkins-home/jenkins.war
INFO:root:Using plugin files: ['default-controller/bundle.yaml', 'default-controller/plugins.yaml', 'default-controller/plugin-catalog.yaml']
INFO:root:Using validation-template from the defaults.configs package
INFO:root:Using validation template '/opt/bundleutils/.app/bundleutilspkg/src/bundleutilspkg/data/configs/validation-template'
INFO:root:Created startup bundle in target/ci_server_home/jenkins-home/casc-startup-bundle
INFO:root:Removing key items from the bundle as no files were found
INFO:root:Updated version to 69303248-b801-e073-63ef-1b6738c4e92e in target/ci_server_home/jenkins-home/casc-startup-bundle/bundle.yaml
```

```sh
$ bundleutils ci-start --url http://ci.target.acme.org/default-controller
INFO:root:Using default cloudbees image. Overwrite with environment variable BUNDLEUTILS_CB_WAR_DOWNLOAD_URL_MM
INFO:root:Using default cloudbees download URL. Overwrite with environment variable BUNDLEUTILS_CB_WAR_DOWNLOAD_URL_MM
INFO:root:Starting Jenkins server with version 2.479.3.1 and type mm
INFO:root:JAVA_HOME is set to /opt/java/openjdk
openjdk version "17.0.11" 2024-04-16
OpenJDK Runtime Environment Temurin-17.0.11+9 (build 17.0.11+9)
OpenJDK 64-Bit Server VM Temurin-17.0.11+9 (build 17.0.11+9, mixed mode, sharing)
INFO:root:ADMIN_PASSWORD not set. Creating a random password...
INFO:root:Temporary ADMIN_PASSWORD set to: <REDACTED>
INFO:root:Starting Jenkins server with command: /opt/java/openjdk/bin/java -Dcore.casc.config.bundle=target/ci_server_home/jenkins-home/casc-startup-bundle -jar target/ci_server_home/jenkins-home/jenkins.war --httpPort=8080 --webroot=target/ci_server_home/jenkins-webroot --prefix=/dummy-server
INFO:root:Jenkins server starting with PID 136
INFO:root:Jenkins server logging to target/ci_server_home/jenkins.log
INFO:root:Waiting max 120 seconds for server to start...
INFO:root:Waiting for server to start...
INFO:root:Process 136 is running. Server may not be started yet.
INFO:root:Waiting for server to start...
INFO:root:Waiting for server to start...
INFO:root:Waiting for server to start...
INFO:root:Waiting for server to start...
INFO:root:Waiting for server to start...
INFO:root:Waiting for server to start...
INFO:root:Waiting for server to start...
INFO:root:Waiting for server to start...
INFO:root:Waiting for server to start...
INFO:root:Waiting for server to start...
INFO:root:Waiting for server to start...
INFO:root:Server started
INFO:root:Checking authentication token...
INFO:root:Authentication successful. Response: {'_class': 'hudson.security.WhoAmI', 'authenticated': True}
INFO:root:Jenkins server - Checking for WARN or ERROR messages in the Jenkins log...
WARNING:root:2025-06-23 10:16:19.222+0000 [id=84]	WARNING	c.h.i.impl.HazelcastInstanceFactory: Hazelcast is starting in a Java modular environment (Java 9 and newer) but without proper access to required Java packages. Use additional Java arguments to provide Hazelcast access to Java internal API. The internal API access is used to get the best performance results. Arguments to be used:

WARNING:root:2025-06-23 10:16:31.298+0000 [id=33]	WARNING	c.c.j.p.r.b.FlowExecutionListAdoption#onLoaded: hudson.model.Queue.id unset, unable to check FlowExecutionList

WARNING:root:2025-06-23 10:16:34.587+0000 [id=78]	WARNING	c.c.o.c.p.OperationsCenterRootAction$DescriptorImpl#setDisabledState: Disabled

WARNING:root:2025-06-23 10:16:36.416+0000 [id=81]	WARNING	c.c.j.p.r.queue.QueueAdoption#check: hudson.model.Queue.id unset, unable to check queue

INFO:root:Jenkins server - Finished checking the Jenkins log
```

```sh
$ bundleutils ci-validate --url http://ci.target.acme.org/default-controller
INFO:root:Using default cloudbees image. Overwrite with environment variable BUNDLEUTILS_CB_WAR_DOWNLOAD_URL_MM
INFO:root:Using default cloudbees download URL. Overwrite with environment variable BUNDLEUTILS_CB_WAR_DOWNLOAD_URL_MM
INFO:root:Validating bundle in default-controller against http://ci.target.acme.org/default-controller/casc-bundle-mgnt/casc-bundle-validate
Traceback (most recent call last):
  File "/opt/bundleutils/.venv/bin/bundleutils", line 8, in <module>
    sys.exit(bundleutils())
  File "/opt/bundleutils/.venv/lib/python3.10/site-packages/click/core.py", line 1442, in __call__
    return self.main(*args, **kwargs)
  File "/opt/bundleutils/.venv/lib/python3.10/site-packages/click/core.py", line 1363, in main
    rv = self.invoke(ctx)
  File "/opt/bundleutils/.venv/lib/python3.10/site-packages/click/core.py", line 1830, in invoke
    return _process_result(sub_ctx.command.invoke(sub_ctx))
  File "/opt/bundleutils/.venv/lib/python3.10/site-packages/click/core.py", line 1226, in invoke
    return ctx.invoke(self.callback, **ctx.params)
  File "/opt/bundleutils/.venv/lib/python3.10/site-packages/click/core.py", line 794, in invoke
    return callback(*args, **kwargs)
  File "/opt/bundleutils/.venv/lib/python3.10/site-packages/click/decorators.py", line 34, in new_func
    return f(get_current_context(), *args, **kwargs)
  File "/opt/bundleutils/.app/bundleutilspkg/src/bundleutilspkg/bundleutils.py", line 1254, in ci_validate
    _validate(
  File "/opt/bundleutils/.app/bundleutilspkg/src/bundleutilspkg/bundleutils.py", line 1995, in _validate
    response.raise_for_status()
  File "/opt/bundleutils/.venv/lib/python3.10/site-packages/requests/models.py", line 1026, in raise_for_status
    raise HTTPError(http_error_msg, response=self)
requests.exceptions.HTTPError: 401 Client Error: Unauthorized for url: http://ci.target.acme.org/default-controller/casc-bundle-mgnt/casc-bundle-validate
$ bundleutils ci-validate
ERROR: No ci_type provided or URL to extract a type from.
$ bundleutils ci-validate
ERROR: No ci_type provided or URL to extract a type from.
$ bundleutils ci-validate --url http://ci.target.acme.org/default-controller
INFO:root:Using default cloudbees image. Overwrite with environment variable BUNDLEUTILS_CB_WAR_DOWNLOAD_URL_MM
INFO:root:Using default cloudbees download URL. Overwrite with environment variable BUNDLEUTILS_CB_WAR_DOWNLOAD_URL_MM
ERROR: Source directory 'dummy-server' does not exist
$ bundleutils ci-validate --url http://ci.target.acme.org/default-controller
INFO:root:Using default cloudbees image. Overwrite with environment variable BUNDLEUTILS_CB_WAR_DOWNLOAD_URL_MM
INFO:root:Using default cloudbees download URL. Overwrite with environment variable BUNDLEUTILS_CB_WAR_DOWNLOAD_URL_MM
INFO:root:Validating bundle in default-controller against http://localhost:8080/dummy-server/casc-bundle-mgnt/casc-bundle-validate
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

```sh
$ bundleutils ci-stop --url http://ci.target.acme.org/default-controller
INFO:root:Using default cloudbees image. Overwrite with environment variable BUNDLEUTILS_CB_WAR_DOWNLOAD_URL_MM
INFO:root:Using default cloudbees download URL. Overwrite with environment variable BUNDLEUTILS_CB_WAR_DOWNLOAD_URL_MM
INFO:root:Stopping Jenkins server with version 2.479.3.1 and type mm
INFO:root:Stopping server with PID 136
INFO:root:Stopped Jenkins server with PID 136
```
