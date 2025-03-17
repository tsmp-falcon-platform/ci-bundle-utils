# CI Bundle Utils Tool


<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [What is it?](#what-is-it)
- [Why create it?](#why-create-it)
- [How can I run it?](#how-can-i-run-it)
- [Walkthrough](#walkthrough)
- [Commands](#commands)
- [Help Pages](#help-pages)
- [Local Development](#local-development)
  - [Setup](#setup)
  - [Code Completion](#code-completion)
  - [Makefile](#makefile)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## What is it?

The `bundleutils` tool is:

- a python utility
- packaged in a docker container
- used for managing CasC bundles

## Why create it?

The simple use-cases are:

- [validating your existing CasC bundles](./docs/use-case-validating-exsting-bundles.md)
- [fetching, transforming, and validating CasC bundles from existing servers](./docs/use-case-validating-exsting-bundles.md)
- [merge multiple bundles into one](./docs/use-case-merging-bundles.md)

## How can I run it?

Runtime variants explained here include:

- [docker](./docs/setup-docker.md)
- [docker-compose](./docs/setup-docker-compose.md)
- [kubernetes](./docs/setup-kubernetes.md)
- [using CloudBees Jobs](./docs/setup-cloudbees-casc.md)

**Since it is a container, it can be run virtually anywhere.**

## Walkthrough

A [walkthrough](https://dictionary.cambridge.org/dictionary/english/walkthrough) setup has been provided at [example-bundles-drift](https://github.com/tsmp-falcon-platform/example-bundles-drift).

The walkthough contains a comprehensive list of steps to setting up bundle management.

TODO: An issue has been created to add a "merge bundles" workflow to the walkthrough - see [Issue #70](https://github.com/tsmp-falcon-platform/ci-bundle-utils/issues/70)

## Commands

For a summary of commands, see [explaining the main commands](./docs/explaining-commands.md)

## Help Pages

Below is a list of the current help pages coming from the `bundleutils` tool. Ideally, the tools help pages will contain enough information to be self explanatory.

<!-- START help-pages-doc -->
```mono
Usage: bundleutils [OPTIONS] COMMAND [ARGS]...

  A tool to fetch and transform YAML documents.

Options:
  -i, --interactive     Run in interactive mode.
  -e, --env-file FILE   Optional bundle profiles file (BUNDLEUTILS_ENV).
  -l, --log-level TEXT  The log level (BUNDLEUTILS_LOG_LEVEL).
  --help                Show this message and exit.

Commands:
  audit                           Transform using the normalize.yaml but...
  bootstrap                       Bootstrap a bundle.
  ci-sanitize-plugins             Sanitizes plugins (needs ci-start).
  ci-setup                        Download CloudBees WAR file, and setup...
  ci-start                        Start CloudBees Server
  ci-stop                         Stop CloudBees Server
  ci-validate                     Validate bundle against controller...
  completion                      Print the shell completion script
  config                          List evaluated config based on cwd and...
  diff                            Diff two YAML directories or files.
  diff-merged                     Diff two bundle directories by...
  extract-name-from-url           Smart extraction of the controller...
  fetch                           Fetch YAML documents from a URL or path.
  find-bundle-by-url              Find a bundle by Jenkins URL and CI...
  help-pages                      Show all help pages by running...
  merge-bundles                   Used for merging bundles.
  merge-yamls                     Used for merging YAML files of the...
  normalize                       Transform using the normalize.yaml for...
  transform                       Transform using a custom...
  update-bundle                   Update the bundle.yaml file in the...
  update-plugins                  Update plugins in the target directory.
  update-plugins-from-test-server
                                  Update plugins in the target directory...
  validate                        Validate bundle in source dir against...
  version                         Show the app version.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils audit [OPTIONS]

  Transform using the normalize.yaml but obfuscating any sensitive data.

  NOTE: The credentials and sensitive data will be hashed and cannot be used
  in an actual bundle.

Options:
  -t, --target-dir DIRECTORY  The target directory for the YAML documents.
                              Defaults to the source directory suffixed with
                              -transformed.
  -s, --source-dir DIRECTORY  The source directory for the YAML documents.
  -c, --config FILE           The transformation config(s).
  -S, --strict                Fail when referencing non-existent files - warn
                              otherwise.
  -H, --hash-seed TEXT        Optional prefix for the hashing process (also
                              BUNDLEUTILS_CREDENTIAL_HASH_SEED).
                              
                              NOTE: Ideally, this should be a secret value
                              that is not shared with anyone. Changing this
                              value will result in different hashes.
  --help                      Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils bootstrap [OPTIONS]

  Bootstrap a bundle.

Options:
  -s, --source-dir DIRECTORY   The bundle to be bootstrapped.
  -S, --source-base DIRECTORY  Specify parent dir of source-dir, bundle name
                               taken from URL.
  -p, --profile TEXT           The bundle profile to use.
  -u, --update TEXT            Should the bundle be updated if present.
  -U, --url TEXT               The controller URL to bootstrap (JENKINS_URL).
  -v, --ci-version TEXT        Optional version (taken from the remote
                               instance otherwise).
  --help                       Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils ci-sanitize-plugins [OPTIONS]

  Sanitizes plugins (needs ci-start).

Options:
  -H, --ci-server-home TEXT   Defaults to
                              /tmp/ci_server_home/<ci_type>/<ci_version>.
  -t, --ci-type TEXT          The type of the CloudBees server.
  -v, --ci-version TEXT       The version of the CloudBees WAR file.
  -s, --source-dir DIRECTORY  The bundle of the plugins to be sanitized.
  -p, --pin-plugins           Add versions to 3rd party plugins (only
                              available for apiVersion 2).
  -c, --custom-url TEXT       Add a custom URL, e.g. http://plugins-
                              repo/plugins/PNAME/PVERSION/PNAME.hpi
  --help                      Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils ci-setup [OPTIONS]

  Download CloudBees WAR file, and setup the starter bundle.

  Env vars:
      BUNDLEUTILS_CB_DOCKER_IMAGE_{CI_TYPE}: Docker image for the CI_TYPE (MM, OC)
      BUNDLEUTILS_CB_WAR_DOWNLOAD_URL_{CI_TYPE}: WAR download URL for the CI_TYPE (CM, OC_TRADITIONAL)
      BUNDLEUTILS_SKOPEO_COPY_OPTS: options to pass to skopeo copy command

      NOTE:
      - All occurences of BUNDLEUTILS_CI_VERSION in the env var value will be replaced.
      - If the value does not include a tag, the CI_VERSION will be appended to it.

      e.g. Use either...
          BUNDLEUTILS_CB_DOCKER_IMAGE_MM=my-registry/cloudbees-core-mm:BUNDLEUTILS_CI_VERSION
          BUNDLEUTILS_CB_DOCKER_IMAGE_MM=my-registry/cloudbees-core-mm

Options:
  -H, --ci-server-home TEXT       Defaults to
                                  /tmp/ci_server_home/<ci_type>/<ci_version>.
  -t, --ci-type TEXT              The type of the CloudBees server.
  -v, --ci-version TEXT           The version of the CloudBees WAR file.
  -s, --source-dir DIRECTORY      The bundle to be validated (startup will use
                                  the plugins from here).
  -T, --ci-bundle-template DIRECTORY
                                  Path to a template bundle used to start the
                                  test server (defaults to in-built tempalte).
  -f, --force                     Force download of the WAR file even if
                                  exists.
  --help                          Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils ci-start [OPTIONS]

  Start CloudBees Server

Options:
  -H, --ci-server-home TEXT       Defaults to
                                  /tmp/ci_server_home/<ci_type>/<ci_version>.
  -t, --ci-type TEXT              The type of the CloudBees server.
  -v, --ci-version TEXT           The version of the CloudBees WAR file.
  -M, --ci-max-start-time INTEGER
                                  Max minutes to start.  [env var:
                                  BUNDLEUTILS_CI_MAX_START_TIME]
  --help                          Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils ci-stop [OPTIONS]

  Stop CloudBees Server

Options:
  -H, --ci-server-home TEXT  Defaults to
                             /tmp/ci_server_home/<ci_type>/<ci_version>.
  -t, --ci-type TEXT         The type of the CloudBees server.
  -v, --ci-version TEXT      The version of the CloudBees WAR file.
  --help                     Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils ci-validate [OPTIONS]

  Validate bundle against controller started with ci-start.

Options:
  -H, --ci-server-home TEXT   Defaults to
                              /tmp/ci_server_home/<ci_type>/<ci_version>.
  -t, --ci-type TEXT          The type of the CloudBees server.
  -v, --ci-version TEXT       The version of the CloudBees WAR file.
  -s, --source-dir DIRECTORY  The bundle to be validated.
  -w, --ignore-warnings       Do not fail if warnings are found.
  -r, --external-rbac FILE    Path to an external rbac.yaml from an Operations
                              Center bundle.
  --help                      Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils completion [OPTIONS]

  Print the shell completion script

Options:
  -s, --shell [bash|fish|zsh]  The shell to generate completion script for.
                               [required]
  --help                       Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils config [OPTIONS]

  List evaluated config based on cwd and env file.

Options:
  --help  Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils diff [OPTIONS]

  Diff two YAML directories or files.

Options:
  -s, --sources PATH  The directories or files to be diffed.
  --help              Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils diff-merged [OPTIONS]

  Diff two bundle directories by temporarily merging both before the diff.

Options:
  -m, --config FILE        An optional custom merge config file if needed.
  -s, --sources DIRECTORY  The bundles to be diffed.
  -a, --api-version TEXT   Optional apiVersion in case bundle does not contain
                           a bundle.yaml. Defaults to 2
  --help                   Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils extract-name-from-url [OPTIONS]

  Smart extraction of the controller name from the URL.

  Extracts NAME from the following URL formats:
  - http://a.b.c/NAME/
  - http://a.b.c/NAME
  - https://a.b.c/NAME/
  - https://a.b.c/NAME
  - http://NAME.b.c/
  - http://NAME.b.c
  - https://NAME.b.c/
  - https://NAME.b.c

Options:
  -u, --url TEXT  The URL to extract the controller name from.
  --help          Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils fetch [OPTIONS]

  Fetch YAML documents from a URL or path.

Options:
  -C, --catalog-warnings-strategy TEXT
                                  Strategy for handling beekeeper warnings in
                                  the plugin catalog
                                  (BUNDLEUTILS_CATALOG_WARNINGS_STRATEGY).
  -J, --plugins-json-merge-strategy TEXT
                                  Strategy for merging plugins from list into
                                  the bundle
                                  (BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY).
  -j, --plugins-json-list-strategy TEXT
                                  Strategy for creating list from the plugins
                                  json
                                  (BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY).
  -c, --cap                       Use the envelope.json from the war file to
                                  remove CAP plugin dependencies
                                  (BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE).
  -t, --target-dir DIRECTORY      The target directory for the YAML documents
                                  (BUNDLEUTILS_FETCH_TARGET_DIR).
  -p, --password TEXT             Password for basic authentication
                                  (BUNDLEUTILS_PASSWORD).
  -u, --username TEXT             Username for basic authentication
                                  (BUNDLEUTILS_USERNAME).
  -U, --url TEXT                  The URL to fetch YAML from
                                  (BUNDLEUTILS_JENKINS_URL).
  -O, --offline                   Save the export and plugin data to <target-
                                  dir>-offline (BUNDLEUTILS_FETCH_OFFLINE).
  -P, --path FILE                 The path to fetch YAML from
                                  (BUNDLEUTILS_PATH).
  -M, --plugin-json-path TEXT     The path to fetch JSON file from (found at /
                                  manage/pluginManager/api/json?pretty&depth=1
                                  &tree=plugins[*[*]]).
  --help                          Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils find-bundle-by-url [OPTIONS]

  Find a bundle by Jenkins URL and CI Version.

  Use -v '.*' to match any version.

Options:
  -U, --url TEXT               The controller URL to test for (JENKINS_URL).
  -v, --ci-version TEXT        Optional version (taken from the remote
                               instance otherwise).
  -b, --bundles-dir DIRECTORY  The directory containing the bundles.
  --help                       Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils help-pages [OPTIONS]

  Show all help pages by running 'bundleutils --help' at the global level and
  each sub command.

Options:
  --help  Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils merge-bundles [OPTIONS]

  Used for merging bundles. Given a list of bundles, merge them into a single
  bundle.

  The merging strategy is defined in a merge config file similar to the merge command.
  The api_version is taken from either (in order):
  - the api_version parameter
  - the last bundle.yaml file in the list of bundles if available
  - the api version of the bundle in BUNDLEUTILS_MERGE_TRANSFORM_DIFFCHECK_SOURCE_DIR
  - the default api_version

  Given at least two bundles, it will:
  - for each section of the bundle.yaml (plugins, catalog, items, etc)
  - collect all the referenced files in order of the bundles
  - merge them together
  - write the result to the outdir or stdout if not provided
  - update the outdir/bundle.yaml with the new references

  Prefer versioned directories (env: BUNDLEUTILS_MERGE_PREFER_VERSION):
  - listing "-b snippets/bootstrap" will look for "snippets/bootstrap-2.492.1.3" if the current version is 2.492.1.3

  Optional features:
  - transform the merged bundle using the transformation configs
      (BUNDLEUTILS_TRANSFORM_CONFIGS and BUNDLEUTILS_TRANSFORM_SOURCE_DIR needed for this)
  - perform a diff check against the source bundle and the transformed bundle
      (BUNDLEUTILS_MERGE_TRANSFORM_DIFFCHECK_SOURCE_DIR needed for this)

Options:
  -S, --strict             Fail when referencing non-existent files - warn
                           otherwise.
  -m, --config FILE        An optional custom merge config file if needed.
  -b, --bundles DIRECTORY  The bundles to be rendered.
  -p, --use-parent         Optionally use the (legacy) parent key to work out
                           which bundles to merge.
  -o, --outdir DIRECTORY   The target for the merged bundle.
  -a, --api-version TEXT   Optional apiVersion. Defaults to 2
  -t, --transform          Optionally transform using the transformation
                           configs (BUNDLEUTILS_MERGE_TRANSFORM_PERFORM).
  -d, --diffcheck          Optionally perform bundleutils diff against the
                           original source bundle and expected bundle
                           (BUNDLEUTILS_MERGE_TRANSFORM_DIFFCHECK).
  --help                   Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils merge-yamls [OPTIONS]

  Used for merging YAML files of the same type (jcasc, plugins, items, rbac,
  etc).

  The merging strategy is defined in a merge-config file. The default contents are shown on execution.

Options:
  -m, --config FILE   An optional custom merge config file if needed.
  -f, --files FILE    The files to be merged.
  -o, --outfile FILE  The target for the merged file.
  --help              Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils normalize [OPTIONS]

  Transform using the normalize.yaml for better comparison.

Options:
  -t, --target-dir DIRECTORY  The target directory for the YAML documents.
                              Defaults to the source directory suffixed with
                              -transformed.
  -s, --source-dir DIRECTORY  The source directory for the YAML documents.
  -c, --config FILE           The transformation config(s).
  -S, --strict                Fail when referencing non-existent files - warn
                              otherwise.
  --help                      Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils transform [OPTIONS]

  Transform using a custom transformation config.

Options:
  -t, --target-dir DIRECTORY  The target directory for the YAML documents.
                              Defaults to the source directory suffixed with
                              -transformed.
  -s, --source-dir DIRECTORY  The source directory for the YAML documents.
  -c, --config FILE           The transformation config(s).
  -S, --strict                Fail when referencing non-existent files - warn
                              otherwise.
  --help                      Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils update-bundle [OPTIONS]

  Update the bundle.yaml file in the target directory:
  - Updating keys according to the files found
  - Removing keys that have no files
  - Generating a new UUID for the id key

  Bundle version generation:
  - Sorts files alphabetically to ensure consistent order.
  - Sorts YAML keys recursively inside each file.
  - Generates a SHA-256 hash and converts it into a UUID.

Options:
  -t, --target-dir DIRECTORY  The target directory to update the bundle.yaml
                              file (defaults to CWD).
  -d, --description TEXT      Optional description for the bundle (also
                              BUNDLEUTILS_BUNDLE_DESCRIPTION).
  -o, --output-sorted TEXT    Optional place to put the sorted yaml string
                              used to created the version.
  --help                      Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils update-plugins [OPTIONS]

  Update plugins in the target directory.

Options:
  -C, --catalog-warnings-strategy TEXT
                                  Strategy for handling beekeeper warnings in
                                  the plugin catalog
                                  (BUNDLEUTILS_CATALOG_WARNINGS_STRATEGY).
  -J, --plugins-json-merge-strategy TEXT
                                  Strategy for merging plugins from list into
                                  the bundle
                                  (BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY).
  -j, --plugins-json-list-strategy TEXT
                                  Strategy for creating list from the plugins
                                  json
                                  (BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY).
  -c, --cap                       Use the envelope.json from the war file to
                                  remove CAP plugin dependencies
                                  (BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE).
  -t, --target-dir DIRECTORY      The target directory for the YAML documents
                                  (BUNDLEUTILS_FETCH_TARGET_DIR).
  -p, --password TEXT             Password for basic authentication
                                  (BUNDLEUTILS_PASSWORD).
  -u, --username TEXT             Username for basic authentication
                                  (BUNDLEUTILS_USERNAME).
  -U, --url TEXT                  The URL to fetch YAML from
                                  (BUNDLEUTILS_JENKINS_URL).
  -O, --offline                   Save the export and plugin data to <target-
                                  dir>-offline (BUNDLEUTILS_FETCH_OFFLINE).
  -P, --path FILE                 The path to fetch YAML from
                                  (BUNDLEUTILS_PATH).
  -M, --plugin-json-path TEXT     The path to fetch JSON file from (found at /
                                  manage/pluginManager/api/json?pretty&depth=1
                                  &tree=plugins[*[*]]).
  --help                          Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils update-plugins-from-test-server [OPTIONS]

  Update plugins in the target directory using the plugins from the test
  server started for validation.

Options:
  -C, --catalog-warnings-strategy TEXT
                                  Strategy for handling beekeeper warnings in
                                  the plugin catalog
                                  (BUNDLEUTILS_CATALOG_WARNINGS_STRATEGY).
  -J, --plugins-json-merge-strategy TEXT
                                  Strategy for merging plugins from list into
                                  the bundle
                                  (BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY).
  -j, --plugins-json-list-strategy TEXT
                                  Strategy for creating list from the plugins
                                  json
                                  (BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY).
  -c, --cap                       Use the envelope.json from the war file to
                                  remove CAP plugin dependencies
                                  (BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE).
  -H, --ci-server-home TEXT       Defaults to
                                  /tmp/ci_server_home/<ci_type>/<ci_version>.
  -t, --ci-type TEXT              The type of the CloudBees server.
  -v, --ci-version TEXT           The version of the CloudBees WAR file.
  -t, --target-dir DIRECTORY      The target directory in which to update the
                                  plugins.yaml.
  --help                          Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils validate [OPTIONS]

  Validate bundle in source dir against URL.

Options:
  -U, --url TEXT              The controller URL to validate agianst
                              (BUNDLEUTILS_JENKINS_URL).
  -u, --username TEXT         Username for basic authentication
                              (BUNDLEUTILS_USERNAME).
  -p, --password TEXT         Password for basic authentication
                              (BUNDLEUTILS_PASSWORD).
  -s, --source-dir DIRECTORY  The source directory for the YAML documents
                              (BUNDLEUTILS_VALIDATE_SOURCE_DIR).  [required]
  -w, --ignore-warnings       Do not fail if warnings are found.
  -r, --external-rbac FILE    Path to an external rbac.yaml from an Operations
                              Center bundle.
  --help                      Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils version [OPTIONS]

  Show the app version.

Options:
  --help  Show this message and exit.
```
<!-- END help-pages-doc -->

## Local Development

> [!TIP]
> Checkout the commands in the [Makefile](./Makefile) for more information on what is run.

### Setup

Python virtualenv setup:

```sh
# setup local python environment
make setup

# run the tests
make test
```

### Code Completion

Activate code completion:

```sh
# show shell completion options on ZSH
bundleutils completion -s zsh

# show shell completion options on BASH
bundleutils completion -s bash
```

### Makefile

The provided [Makefile](./Makefile) contains some targets for running local docker environments.

<!-- START makefile-doc -->
```bash
$ make help


Usage:
  make <target>

Targets:
  setup                  Setup virtualenv (optional PYTHON_CMD=python3.xx)
  install                Install the bundleutils package
  install-dev            Install the bundleutils package with dev dependencies
  test                   Run the pytest suite
  test                   Run the full pytest suite
  test/%                 Run the pytest suite tests containing 'test/<string>'
  pyinstaller            Build the bundleutils package
  compose/start-dev      Start the bundleutils container
  compose/start          Start the bundleutils container
  compose/stop           Stop the bundleutils container
  compose/enter          Enter the bundleutils container
  docker/create-volume   Create the bundleutils-cache volume
  docker/build-dev       Build the bundleutils:dev image
  docker/start-dev       Start the bundleutils:dev container
  docker/start           Start the bundleutils container
  docker/stop            Stop the bundleutils container
  docker/enter           Enter the bundleutils container
  docker/remove          Remove the bundleutils container
  help                   Makefile Help Page
```
<!-- END makefile-doc -->
