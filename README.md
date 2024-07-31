# CI Bundle Utils Tool

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Show me the money](#show-me-the-money)
- [What is it?](#what-is-it)
- [Why create it?](#why-create-it)
- [Where can I run it?](#where-can-i-run-it)
- [Commands](#commands)
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
  docker/start           Start the bundleutils container
  docker/stop            Stop the bundleutils container
  docker/enter           Enter the bundleutils container
  docker/remove          Remove the bundleutils container
  help                   Makefile Help Page
```
<!-- END makefile-doc -->