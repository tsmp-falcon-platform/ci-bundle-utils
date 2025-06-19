# Commands

Here you will find a quick summary of the main commands available.

## Main Commands

Main commands are:

- `fetch` to fetch the exported bundle from a given controller URL, zip file, or text file
  - defaults to the `core-casc-export-*.zip` in the current directory
- `transform` to transform the exported bundle
  - takes one or more transformation configurations
- `validate` to validate a bundle against a target server
  - takes a source directory, url, username, password, etc

## CI Testing Commands

Special `ci-*` commands to provide local testing capabilities:

Common variables used by all `ci-*` commands:

- The server version with either `BUNDLEUTILS_CI_VERSION` or `--ci-version`
- The server type with either `BUNDLEUTILS_CI_TYPE` or `--ci-type` (defaults to `mm`)

The commands:

- `ci-setup`
  - prepares a server for local testing
  - takes a bundle directory as a source for expected plugins
  - downloads the appropriate war file
  - creates a startup bundle using
    - the plugins from the source directory
    - the [default validation template](./bundleutilspkg/defaults/configs/validation-template) (can be overridden)
- `ci-start`
  - starts the test server
  - starting the java process
  - saves the pid file
  - tests the authentication token
- `ci-validate`
  - validates a bundle aginst the started server
  - takes the bundle source directory
  - returns the validation result JSON
- `ci-stop`
  - stops the test server
  - uses the pid file from the start command above

## The `transform` Command

See the [internal configs directory](../bundleutilspkg/src/bundleutilspkg/data/configs) for an explanation on how the transformation process works.
