# CI Bundle Utils Tool

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [What is it?](#what-is-it)
- [5 Minute Challenges](#5-minute-challenges)
- [Commands and Help Pages](#commands-and-help-pages)
- [Local Development](#local-development)
  - [Setup](#setup)
  - [Code Completion](#code-completion)
  - [Makefile](#makefile)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## What is it?

The `bundleutils` is a python utility used for managing CasC bundles.

Simple use-cases are:

- [validating your existing CasC bundles](./docs/use-case-validating-exsting-bundles.md)
- [fetching, transforming, and validating CasC bundles from existing servers](./docs/use-case-validating-exsting-bundles.md)
- [merge multiple bundles into one](./docs/use-case-merging-bundles.md)

Runtime variants explained here include [docker](./docs/setup-docker.md), [docker-compose](./docs/setup-docker-compose.md), [kubernetes](./docs/setup-kubernetes.md), [using CloudBees Jobs](./docs/setup-cloudbees-casc.md)

**Since it is a container, it can be run virtually anywhere.**

## 5 Minute Challenges

The following tutorials get you **up and running** and **in your own environment** in just **5 mins**.

- [Auditing Challenge](./docs/5min_challenge_auditing.md)
- Coming soon - Bundle Management Challenge
- Coming soon - Upgrade Management Challenge

## Commands and Help Pages

For a summary of commands, see [explaining the main commands](./docs/explaining-commands.md)

Below is a list of the current help pages coming from the `bundleutils` tool. Ideally, the tools help pages will contain enough information to be self explanatory.

<!-- START help-pages-doc -->
```mono
Usage: bundleutils [OPTIONS] COMMAND [ARGS]...

  A tool to fetch and transform YAML documents.

Options:
  -l, --log-level [TRACE|DEBUG|INFO|WARNING]
                                  The log level (BUNDLEUTILS_GBL_LOG_LEVEL)
  -e, --raise-errors / --no-raise-errors
                                  Raise errors instead of printing them
                                  (BUNDLEUTILS_GBL_RAISE_ERRORS)
  -i, --interactive / --no-interactive
                                  Run in interactive mode
                                  (BUNDLEUTILS_GBL_INTERACTIVE)
  -a, --append-version / --no-append-version
                                  Append the current version to the bundle
                                  directory (BUNDLEUTILS_GBL_APPEND_VERSION)
  -b, --bundles-base DIRECTORY    The base directory for the bundles
                                  (BUNDLEUTILS_BUNDLES_BASE)
  --help                          Show this message and exit.

Commands:
  api                       Utility for calling the Jenkins API.
  audit                     Transform bundle but obfuscating any...
  ci-sanitize-plugins       Sanitizes plugins (needs ci-start).
  ci-setup                  Download CloudBees WAR file, and setup the...
  ci-start                  Start CloudBees Server
  ci-stop                   Stop CloudBees Server
  ci-validate               Validate bundle against controller started...
  completion                Print the shell completion script
  controllers               Return all online controllers from an...
  diff                      Diff two YAML directories or files.
  diff-merged               Diff two bundle directories by temporarily...
  extract-from-pattern      Extract the controller name from a string...
  extract-name-from-url     Smart extraction of the controller name from...
  extract-version-from-url  Get the instance version from the URL.
  fetch                     Fetch YAML documents from a URL.
  find-bundles              Find all bundle.yaml files in the target...
  help-pages                Show all help pages by running 'bundleutils...
  merge-bundles             Used for merging bundles.
  merge-yamls               Used for merging YAML files of the same type...
  preflight                 Preconditions for fetching the CasC export.
  transform                 Transform using a custom transformation config.
  update-bundle             Update the bundle.yaml file in the target...
  update-plugins            Update plugins in the target directory.
  validate                  Validate bundle in source dir against URL.
  version                   Show the app version.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils api [OPTIONS]

  Utility for calling the Jenkins API.  e.g. bundleutils api -P
  /whoAmI/api/json?pretty

Options:
  -U, --url TEXT        The URL to interact with (BUNDLEUTILS_JENKINS_URL)
  -u, --username TEXT   Username for basic authentication
                        (BUNDLEUTILS_USERNAME)
  -p, --password TEXT   Password for basic authentication
                        (BUNDLEUTILS_PASSWORD)
  -P, --path TEXT       Path to the API endpoint to call
                        (BUNDLEUTILS_API_PATH)
  -d, --data-file FILE  The data to post to the API endpoint
                        (BUNDLEUTILS_API_DATA_FILE)
  -o, --out-file FILE   The output file to write the API response to
                        (BUNDLEUTILS_API_OUT_FILE)
  --help                Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils audit [OPTIONS]

  Transform bundle but obfuscating any sensitive data.

  NOTE:
  - The credentials and sensitive data will be hashed and cannot be used in an actual bundle.
  - Use the hash arg to revert to the standard method.

Options:
  -K, --config-key TEXT         Returns value if key provided (error if not
                                found), or k=v when used as flag
                                (BUNDLEUTILS_CONFIG_KEY)
  -U, --url TEXT                The URL to interact with
                                (BUNDLEUTILS_JENKINS_URL)
  -d, --dry-run / --no-dry-run  Print the merged transform config and exit
                                (BUNDLEUTILS_DRY_RUN)
  -S, --strict / --no-strict    Fail when referencing non-existent files -
                                warn otherwise (BUNDLEUTILS_STRICT)
  -C, --configs-base DIRECTORY  The directory containing the transformation
                                config(s) (BUNDLEUTILS_CONFIGS_BASE)
  -c, --config FILE             The transformation config to use
                                (BUNDLEUTILS_CONFIG)
  -s, --source-dir DIRECTORY    The source directory for the YAML documents to
                                audit (BUNDLEUTILS_AUDIT_SOURCE_DIR)
  -t, --target-dir DIRECTORY    The target directory for the audited YAML
                                documents (BUNDLEUTILS_AUDIT_TARGET_DIR)
  -H, --hash-seed TEXT          Optional prefix for the hashing process.
                                
                                NOTE: Ideally, this should be a secret value
                                that is not shared with anyone. Changing this
                                value will result in different hashes.
                                (BUNDLEUTILS_AUDIT_HASH_SEED)
  -n, --hash / --no-hash        Replace sensitive data with its
                                ${THIS_IS_THE_SECRET} equivalent
                                (BUNDLEUTILS_AUDIT_HASH)
  --help                        Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils ci-sanitize-plugins [OPTIONS]

  Sanitizes plugins (needs ci-start).

Options:
  -H, --ci-server-home TEXT       Defaults to
                                  /tmp/ci_server_home/<ci_type>/<ci_version>
                                  (BUNDLEUTILS_CI_SERVER_HOME)
  -U, --url TEXT                  The URL to interact with
                                  (BUNDLEUTILS_JENKINS_URL)
  -t, --ci-type TEXT              The type of the CloudBees instance
                                  (BUNDLEUTILS_CI_TYPE)
  -v, --ci-version TEXT           The version of the CloudBees instance
                                  (BUNDLEUTILS_CI_VERSION)
  -s, --source-dir DIRECTORY      The bundle to be validated - startup will
                                  use the plugins from here
                                  (BUNDLEUTILS_CI_SETUP_SOURCE_DIR)
  -p, --pin-plugins / --no-pin-plugins
                                  Add versions to 3rd party plugins (only
                                  available for apiVersion 2)
                                  (BUNDLEUTILS_SANITIZE_PLUGINS_PIN_PLUGINS)
  -u, --custom-url TEXT           Add a custom URL, e.g. http://plugins-
                                  repo/plugins/PNAME/PVERSION/PNAME.hpi
                                  (BUNDLEUTILS_SANITIZE_PLUGINS_CUSTOM_URL)
  --help                          Show this message and exit.
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
                                  /tmp/ci_server_home/<ci_type>/<ci_version>
                                  (BUNDLEUTILS_CI_SERVER_HOME)
  -U, --url TEXT                  The URL to interact with
                                  (BUNDLEUTILS_JENKINS_URL)
  -t, --ci-type TEXT              The type of the CloudBees instance
                                  (BUNDLEUTILS_CI_TYPE)
  -v, --ci-version TEXT           The version of the CloudBees instance
                                  (BUNDLEUTILS_CI_VERSION)
  -s, --source-dir DIRECTORY      The bundle to be validated - startup will
                                  use the plugins from here
                                  (BUNDLEUTILS_CI_SETUP_SOURCE_DIR)
  -T, --ci-bundle-template DIRECTORY
                                  Path to a template bundle used to start the
                                  test server - defaults to in-built template
                                  (BUNDLEUTILS_CI_BUNDLE_TEMPLATE)
  -f, --force / --no-force        Force download of the WAR file even if
                                  exists (BUNDLEUTILS_CI_FORCE)
  --help                          Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils ci-start [OPTIONS]

  Start CloudBees Server

Options:
  -H, --ci-server-home TEXT       Defaults to
                                  /tmp/ci_server_home/<ci_type>/<ci_version>
                                  (BUNDLEUTILS_CI_SERVER_HOME)
  -U, --url TEXT                  The URL to interact with
                                  (BUNDLEUTILS_JENKINS_URL)
  -t, --ci-type TEXT              The type of the CloudBees instance
                                  (BUNDLEUTILS_CI_TYPE)
  -v, --ci-version TEXT           The version of the CloudBees instance
                                  (BUNDLEUTILS_CI_VERSION)
  -x, --ci-max-start-time INTEGER
                                  The maximum time to wait for the CI to start
                                  (in seconds) (BUNDLEUTILS_CI_MAX_START_TIME)
  --help                          Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils ci-stop [OPTIONS]

  Stop CloudBees Server

Options:
  -H, --ci-server-home TEXT  Defaults to
                             /tmp/ci_server_home/<ci_type>/<ci_version>
                             (BUNDLEUTILS_CI_SERVER_HOME)
  -U, --url TEXT             The URL to interact with
                             (BUNDLEUTILS_JENKINS_URL)
  -t, --ci-type TEXT         The type of the CloudBees instance
                             (BUNDLEUTILS_CI_TYPE)
  -v, --ci-version TEXT      The version of the CloudBees instance
                             (BUNDLEUTILS_CI_VERSION)
  --help                     Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils ci-validate [OPTIONS]

  Validate bundle against controller started with ci-start.

Options:
  -H, --ci-server-home TEXT       Defaults to
                                  /tmp/ci_server_home/<ci_type>/<ci_version>
                                  (BUNDLEUTILS_CI_SERVER_HOME)
  -K, --config-key TEXT           Returns value if key provided (error if not
                                  found), or k=v when used as flag
                                  (BUNDLEUTILS_CONFIG_KEY)
  -U, --url TEXT                  The URL to interact with
                                  (BUNDLEUTILS_JENKINS_URL)
  -t, --ci-type TEXT              The type of the CloudBees instance
                                  (BUNDLEUTILS_CI_TYPE)
  -v, --ci-version TEXT           The version of the CloudBees instance
                                  (BUNDLEUTILS_CI_VERSION)
  -s, --source-dir DIRECTORY      The source directory for the YAML documents
                                  to validate
                                  (BUNDLEUTILS_VALIDATE_SOURCE_DIR)
  -w, --ignore-warnings / --no-ignore-warnings
                                  Do not fail if warnings are found in
                                  validation
                                  (BUNDLEUTILS_VALIDATE_IGNORE_WARNINGS)
  -r, --external-rbac FILE        Path to an external rbac.yaml from an
                                  operations center bundle
                                  (BUNDLEUTILS_VALIDATE_EXTERNAL_RBAC)
  --help                          Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils completion [OPTIONS]

  Print the shell completion script

Options:
  -s, --shell [bash|fish|zsh]  The shell to generate completion script for
                               (BUNDLEUTILS_SHELL)  [required]
  --help                       Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils controllers [OPTIONS]

  Return all online controllers from an operation center.

Options:
  -U, --url TEXT       The URL to interact with (BUNDLEUTILS_JENKINS_URL)
  -u, --username TEXT  Username for basic authentication
                       (BUNDLEUTILS_USERNAME)
  -p, --password TEXT  Password for basic authentication
                       (BUNDLEUTILS_PASSWORD)
  --help               Show this message and exit.
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
Usage: bundleutils extract-from-pattern [OPTIONS]

  Extract the controller name from a string using a regex pattern. This
  command is useful for extracting controller name from a feature branch name
  or similar strings.

  \b e.g.

  - Full string. Pattern: ^([a-z0-9\-]+)$

  - Prefix: main-, Suffix: -drift. Pattern: ^main-([a-z0-9\-]+)-drift$

  - Prefix: feature/testing-, no suffix. Pattern:
  ^feature/testing-([a-z0-9\-]+)$

  - Prefix: testing-, no suffix. Pattern: ^testing-([a-z0-9\-]+)$

  - Prefix: feature/JIRA-1234/, Suffix: optional __something. Pattern:
  ^feature/[A-Z]+-\d+/([a-z0-9\-]+)(?:__[a-z0-9\-]+)*$

Options:
  -s, --string TEXT   The string to test (e.g. a feature/testing-controller-a
                      or main-controller-a-drift) (BUNDLEUTILS_EXTRACT_STRING)
                      [required]
  -p, --pattern TEXT  Optional pattern to match against
                      (BUNDLEUTILS_EXTRACT_PATTERN)
  --help              Show this message and exit.
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
  -U, --url TEXT  The URL to interact with (BUNDLEUTILS_JENKINS_URL)
                  [required]
  --help          Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils extract-version-from-url [OPTIONS]

  Get the instance version from the URL.

Options:
  -U, --url TEXT  The URL to interact with (BUNDLEUTILS_JENKINS_URL)
                  [required]
  --help          Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils fetch [OPTIONS]

  Fetch YAML documents from a URL.

Options:
  -K, --config-key TEXT           Returns value if key provided (error if not
                                  found), or k=v when used as flag
                                  (BUNDLEUTILS_CONFIG_KEY)
  -P, --path FILE                 The path to fetch YAML from
                                  (BUNDLEUTILS_FETCH_LOCAL_PATH)
  -U, --url TEXT                  The URL to interact with
                                  (BUNDLEUTILS_JENKINS_URL)
  -u, --username TEXT             Username for basic authentication
                                  (BUNDLEUTILS_USERNAME)
  -p, --password TEXT             Password for basic authentication
                                  (BUNDLEUTILS_PASSWORD)
  -t, --target-dir DIRECTORY      The target directory for the fetched YAML
                                  documents (BUNDLEUTILS_FETCH_TARGET_DIR)
  -I, --ignore-items / --no-ignore-items
                                  Do not fetch the computationally expensive
                                  items.yaml (BUNDLEUTILS_FETCH_IGNORE_ITEMS)
  -k, --keys-to-scalars TEXT      Comma-separated list of yaml dict keys to
                                  convert to "|" type strings instead of
                                  quoted strings, defaults to
                                  'systemMessage,script,description'
                                  (BUNDLEUTILS_FETCH_KEYS_TO_SCALARS)
  -c, --use-cap / --no-use-cap    Use the envelope.json from the war file to
                                  remove CAP plugin dependencies
                                  (BUNDLEUTILS_PLUGINS_USE_CAP)
  -j, --plugins-json-list-strategy TEXT
                                  Strategy for creating list from the plugins
                                  json
                                  (BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY)
  -J, --plugins-json-merge-strategy TEXT
                                  Strategy for merging plugins from list into
                                  the bundle
                                  (BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY)
  -C, --catalog-warnings-strategy TEXT
                                  Strategy for handling beekeeper warnings in
                                  the plugin catalog (BUNDLEUTILS_PLUGINS_CATA
                                  LOG_WARNINGS_STRATEGY)
  --help                          Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils find-bundles [OPTIONS]

  Find all bundle.yaml files in the target directory and print their paths. If
  no target directory is provided, the current working directory is used.

Options:
  -t, --target-dir DIRECTORY  The target directory to find bundles (defaults
                              to CWD).
  --help                      Show this message and exit.
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

Options:
  -U, --url TEXT                  The URL to interact with
                                  (BUNDLEUTILS_JENKINS_URL)
  -S, --strict / --no-strict      Fail when referencing non-existent files -
                                  warn otherwise (BUNDLEUTILS_STRICT)
  -m, --config FILE               An optional custom merge config file if
                                  needed (BUNDLEUTILS_MERGE_CONFIG)
  -b, --bundles DIRECTORY         The bundles to be rendered
                                  (BUNDLEUTILS_MERGE_BUNDLES)
  -p, --use-parent / --no-use-parent
                                  Optionally use the (legacy) parent key to
                                  work out which bundles to merge
                                  (BUNDLEUTILS_MERGE_USE_PARENT)
  -o, --outdir DIRECTORY          The target for the merged bundle
                                  (BUNDLEUTILS_MERGE_OUTDIR)
  -a, --api-version TEXT          Optional apiVersion. Defaults to 2
                                  (BUNDLEUTILS_MERGE_API_VERSION)
  --help                          Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils merge-yamls [OPTIONS]

  Used for merging YAML files of the same type (jcasc, plugins, items, rbac,
  etc).

  The merging strategy is defined in a merge-config file. The default contents are shown on execution.

Options:
  -m, --config FILE  An optional custom merge config file if needed
                     (BUNDLEUTILS_MERGE_CONFIG)
  -f, --files FILE   The files to merge (BUNDLEUTILS_MERGE_FILES)
  -o, --outdir FILE  The target for the merged bundle
                     (BUNDLEUTILS_MERGE_OUTDIR)
  --help             Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils preflight [OPTIONS]

  Preconditions for fetching the CasC export.

Options:
  -U, --url TEXT       The URL to interact with (BUNDLEUTILS_JENKINS_URL)
                       [required]
  -u, --username TEXT  Username for basic authentication
                       (BUNDLEUTILS_USERNAME)  [required]
  -p, --password TEXT  Password for basic authentication
                       (BUNDLEUTILS_PASSWORD)  [required]
  --help               Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils transform [OPTIONS]

  Transform using a custom transformation config.

Options:
  -K, --config-key TEXT         Returns value if key provided (error if not
                                found), or k=v when used as flag
                                (BUNDLEUTILS_CONFIG_KEY)
  -U, --url TEXT                The URL to interact with
                                (BUNDLEUTILS_JENKINS_URL)
  -d, --dry-run / --no-dry-run  Print the merged transform config and exit
                                (BUNDLEUTILS_DRY_RUN)
  -S, --strict / --no-strict    Fail when referencing non-existent files -
                                warn otherwise (BUNDLEUTILS_STRICT)
  -C, --configs-base DIRECTORY  The directory containing the transformation
                                config(s) (BUNDLEUTILS_CONFIGS_BASE)
  -c, --config FILE             The transformation config to use
                                (BUNDLEUTILS_CONFIG)
  -s, --source-dir DIRECTORY    The source directory for the YAML documents to
                                transform (BUNDLEUTILS_TRANSFORM_SOURCE_DIR)
  -t, --target-dir DIRECTORY    The target directory for the transformed YAML
                                documents (BUNDLEUTILS_TRANSFORM_TARGET_DIR)
  --help                        Show this message and exit.
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

  Empty bundle strategy must be one of:
  - 'fail': Fail if the bundle is empty.
  - 'delete': Delete the bundle if it is empty
  - 'noop': Create a noop jenkins.yaml and continue

Options:
  -t, --target-dir DIRECTORY      The target directory to update the
                                  bundle.yaml file (defaults to CWD)
                                  (BUNDLEUTILS_UPDATE_BUNDLE_TARGET_DIR)
  -d, --description TEXT          Optional description for the bundle
                                  (BUNDLEUTILS_UPDATE_BUNDLE_DESCRIPTION)
  -o, --output-sorted TEXT        Optional place to put the sorted yaml string
                                  used to create the version
                                  (BUNDLEUTILS_UPDATE_BUNDLE_OUTPUT_SORTED)
  -e, --empty-bundle-strategy TEXT
                                  Optional strategy for handling empty bundles
                                  (BUNDLEUTILS_UPDATE_BUNDLE_EMPTY_BUNDLE_STRA
                                  TEGY)
  -r, --recursive / --no-recursive
                                  Update recursively on all bundles found from
                                  target dir
                                  (BUNDLEUTILS_UPDATE_BUNDLE_RECURSIVE)
  --help                          Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils update-plugins [OPTIONS]

  Update plugins in the target directory.

Options:
  -U, --url TEXT                  The URL to interact with
                                  (BUNDLEUTILS_JENKINS_URL)
  -u, --username TEXT             Username for basic authentication
                                  (BUNDLEUTILS_USERNAME)
  -p, --password TEXT             Password for basic authentication
                                  (BUNDLEUTILS_PASSWORD)
  -t, --target-dir DIRECTORY      The target directory for the fetched YAML
                                  documents (BUNDLEUTILS_FETCH_TARGET_DIR)
  -I, --ignore-items / --no-ignore-items
                                  Do not fetch the computationally expensive
                                  items.yaml (BUNDLEUTILS_FETCH_IGNORE_ITEMS)
  -c, --use-cap / --no-use-cap    Use the envelope.json from the war file to
                                  remove CAP plugin dependencies
                                  (BUNDLEUTILS_PLUGINS_USE_CAP)
  -j, --plugins-json-list-strategy TEXT
                                  Strategy for creating list from the plugins
                                  json
                                  (BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY)
  -J, --plugins-json-merge-strategy TEXT
                                  Strategy for merging plugins from list into
                                  the bundle
                                  (BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY)
  -C, --catalog-warnings-strategy TEXT
                                  Strategy for handling beekeeper warnings in
                                  the plugin catalog (BUNDLEUTILS_PLUGINS_CATA
                                  LOG_WARNINGS_STRATEGY)
  --help                          Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils validate [OPTIONS]

  Validate bundle in source dir against URL.

Options:
  -K, --config-key TEXT           Returns value if key provided (error if not
                                  found), or k=v when used as flag
                                  (BUNDLEUTILS_CONFIG_KEY)
  -U, --url TEXT                  The URL to interact with
                                  (BUNDLEUTILS_JENKINS_URL)
  -u, --username TEXT             Username for basic authentication
                                  (BUNDLEUTILS_USERNAME)
  -p, --password TEXT             Password for basic authentication
                                  (BUNDLEUTILS_PASSWORD)
  -s, --source-dir DIRECTORY      The source directory for the YAML documents
                                  to validate
                                  (BUNDLEUTILS_VALIDATE_SOURCE_DIR)
  -w, --ignore-warnings / --no-ignore-warnings
                                  Do not fail if warnings are found in
                                  validation
                                  (BUNDLEUTILS_VALIDATE_IGNORE_WARNINGS)
  -r, --external-rbac FILE        Path to an external rbac.yaml from an
                                  operations center bundle
                                  (BUNDLEUTILS_VALIDATE_EXTERNAL_RBAC)
  --help                          Show this message and exit.
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

Initial tests:

```sh
{
  # setup local python environment
  make setup

  # activate the virtual env
  source .venv/bin/activate

  # activate the virtual env
  make install

  # run the tests
  make test
}
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
  test                   Run the pytest suite
  test/%                 Run the pytest suite tests containing 'test/<string>'
  lock-files             Install the bundleutils package
  pyinstaller            Build the bundleutils package
  marp                   Build the Marp presentation
  compose/start-dev      Start the bundleutils container
  compose/start          Start the bundleutils container
  compose/stop           Stop the bundleutils container
  compose/enter          Enter the bundleutils container
  docker/create-volume   Create the bundleutils-cache volume
  docker/build-dev       Build the bundleutils:dev image
  docker/update-dev      Update the bundleutils:dev image with local changes
  docker/start-dev       Start the bundleutils:dev container
  docker/start           Start the bundleutils container
  docker/stop            Stop the bundleutils container
  docker/enter           Enter the bundleutils container
  docker/remove          Remove the bundleutils container
  help                   Makefile Help Page
```
<!-- END makefile-doc -->
