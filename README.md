# CI Bundle Utils Tool

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Show me the money](#show-me-the-money)
- [What is it?](#what-is-it)
- [Why create it?](#why-create-it)
- [Where can I run it?](#where-can-i-run-it)
- [Commands](#commands)
- [Help Pages](#help-pages)
- [Local Development](#local-development)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Show me the money

If you don't like reading documentation and just want to try it out in your current setup, see [this document](./docs/show-me-the-money.md).

## What is it?

The `bundleutils` tool is:

- a python utility
- packaged in a docker container
- used for managing CasC bundles

## Why create it?

The simple use-cases are:

- [validating your existing CasC bundles](./docs/use-case-validating-exsting-bundles.md)
- [fetching, transforming, and validating CasC bundles from existing servers](./docs/use-case-validating-exsting-bundles.md)

## Where can I run it?

Runtime variants explained here include:

- [docker](./docs/setup-docker.md)
- [docker-compose](./docs/setup-docker-compose.md)
- [kubernetes](./docs/setup-kubernetes.md)
- [using CloudBees Jobs](./docs/setup-cloudbees-casc.md)

**Since it is a container, it can be run virtually anywhere.**

## Commands

For a summary of commands, see [explaining the main commands](./docs/explaining-commands.md)

## Help Pages

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
  audit                  Transform using the normalize.yaml but...
  bootstrap              Bootstrap a bundle.
  ci-sanitize-plugins    Sanitizes plugins (needs ci-start).
  ci-setup               Download CloudBees WAR file, and setup the...
  ci-start               Start CloudBees Server
  ci-stop                Stop CloudBees Server
  ci-validate            Validate bundle against controller started with...
  completion             Print the shell completion script
  config                 List evaluated config based on cwd and env file.
  diff                   Diff two YAML directories or files.
  extract-name-from-url  Smart extraction of the controller name from the...
  fetch                  Fetch YAML documents from a URL or path.
  find-bundle-by-url     Find a bundle by Jenkins URL and CI Version.
  help-pages             Show all help pages by running 'bundleutils...
  normalize              Transform using the normalize.yaml for better...
  transform              Transform using a custom transformation config.
  update-bundle          Update the bundle.yaml file in the target...
  update-plugins         Update plugins in the target directory.
  validate               Validate bundle in source dir against URL.
  version                Show the app version.
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
  -c, --config TEXT           The transformation config(s).
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
Usage: bundleutils diff [OPTIONS] SRC1 SRC2

  Diff two YAML directories or files.

Options:
  --help  Show this message and exit.
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
  -t, --target-dir DIRECTORY      The target directory for the YAML documents
                                  (BUNDLEUTILS_FETCH_TARGET_DIR).
  -p, --password TEXT             Password for basic authentication
                                  (BUNDLEUTILS_PASSWORD).
  -u, --username TEXT             Username for basic authentication
                                  (BUNDLEUTILS_USERNAME).
  -U, --url TEXT                  The URL to fetch YAML from
                                  (BUNDLEUTILS_JENKINS_URL).
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
  -O, --offline                   Save the export and plugin data to <target-
                                  dir>-offline (BUNDLEUTILS_FETCH_OFFLINE).
  -c, --cap                       Use the envelope.json from the war file to
                                  remove CAP plugin dependencies
                                  (BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE).
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
Usage: bundleutils normalize [OPTIONS]

  Transform using the normalize.yaml for better comparison.

Options:
  -t, --target-dir DIRECTORY  The target directory for the YAML documents.
                              Defaults to the source directory suffixed with
                              -transformed.
  -s, --source-dir DIRECTORY  The source directory for the YAML documents.
  -c, --config TEXT           The transformation config(s).
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
  -c, --config TEXT           The transformation config(s).
  -S, --strict                Fail when referencing non-existent files - warn
                              otherwise.
  --help                      Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils update-bundle [OPTIONS]

  Update the bundle.yaml file in the target directory.

Options:
  -t, --target-dir DIRECTORY  The target directory to update the bundle.yaml
                              file (defaults to CWD).
  -d, --description TEXT      Optional description for the bundle (also
                              BUNDLEUTILS_BUNDLE_DESCRIPTION).
  --help                      Show this message and exit.
------------------------------------------------------------------------------------------------------------------------
Usage: bundleutils update-plugins [OPTIONS]

  Update plugins in the target directory.

Options:
  -t, --target-dir DIRECTORY      The target directory for the YAML documents
                                  (BUNDLEUTILS_FETCH_TARGET_DIR).
  -p, --password TEXT             Password for basic authentication
                                  (BUNDLEUTILS_PASSWORD).
  -u, --username TEXT             Username for basic authentication
                                  (BUNDLEUTILS_USERNAME).
  -U, --url TEXT                  The URL to fetch YAML from
                                  (BUNDLEUTILS_JENKINS_URL).
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
  -O, --offline                   Save the export and plugin data to <target-
                                  dir>-offline (BUNDLEUTILS_FETCH_OFFLINE).
  -c, --cap                       Use the envelope.json from the war file to
                                  remove CAP plugin dependencies
                                  (BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE).
  -P, --path FILE                 The path to fetch YAML from
                                  (BUNDLEUTILS_PATH).
  -M, --plugin-json-path TEXT     The path to fetch JSON file from (found at /
                                  manage/pluginManager/api/json?pretty&depth=1
                                  &tree=plugins[*[*]]).
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

To run locally:

```sh
# create a virtual environment
python -m venv .venv

# install dependencies in edit mode
pip install -e bundleutilspkg

# activate environment
source .venv/bin/activate

# show shell completion options on ZSH
bundleutils completion -s zsh

# show shell completion options on BASH
bundleutils completion -s bash
```

Alternatively, the provided [Makefile](./Makefile) contains some targets for running local docker environments.

<!-- START makefile-doc -->
```bash
$ make help


Usage:
  make <target>

Targets:
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
