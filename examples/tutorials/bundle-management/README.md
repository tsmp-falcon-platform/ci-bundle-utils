# 5 Minute Challenge: Auditing

This tutorial will explain how to have your bundles managed in 5 mins.

>[!TIP]
> Have a look at the presentation on [Bob the DevOps Engineer](../../../docs/presentations/intro.md) for a quick summary.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Prerequisites](#prerequisites)
- [3, 2, 1...Go](#3-2-1go)
- [Bonus Exercise: Using `BUNDLEUTILS_GBL_URL_BASE_PATTERN`](#bonus-exercise-using-bundleutils_gbl_url_base_pattern)
- [Bonus Exercise: find all online controllers](#bonus-exercise-find-all-online-controllers)
- [Bonus Exercise: using `BUNDLEUTILS_INTERACTIVE`](#bonus-exercise-using-bundleutils_interactive)
- [Bonus Exercise: using the `gitleaks` check](#bonus-exercise-using-the-gitleaks-check)
  - [THE PROBLEM](#the-problem)
  - [GitLeaks For Everything Else](#gitleaks-for-everything-else)
  - [GitLeaks Config](#gitleaks-config)
- [Bonus Exercise: using a custom `transform.yaml`](#bonus-exercise-using-a-custom-transformyaml)
- [Bonus Exercise: using `--config auto`](#bonus-exercise-using---config-auto)
- [Bonus Exercise: avoid downloading expensive `items.yaml`](#bonus-exercise-avoid-downloading-expensive-itemsyaml)
  - [PROBLEM](#problem)
  - [PROPOSED SOLUTION](#proposed-solution)
- [Bonus Exercise: version based bundles](#bonus-exercise-version-based-bundles)
- [Bonus Exercise: version based bundles (and preserving git history)](#bonus-exercise-version-based-bundles-and-preserving-git-history)
- [Bonus Exercise: all in one](#bonus-exercise-all-in-one)
- [Running in Production](#running-in-production)
  - [Pipeline Job](#pipeline-job)
  - [Pipeline Job - All Online Controllers](#pipeline-job---all-online-controllers)
  - [Operation Center](#operation-center)
  - [Git over SSH](#git-over-ssh)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Prerequisites

See the common [prerequisites](../README.md#prerequisites).

## 3, 2, 1...Go

We wish to manage your controllers configuration. We want to:

- `fetch` the current state of your controller
- `transform` the raw bundle
  - removing any unnecessary data
  - reshaping other sections as required
  - managing any credentials or sensitive data so that they can be re-ingested by the controller.
- `validate` the results to a git repository
- save the results to a git repository

> [!NOTE]
> 1 minute...

Create a test repo with a default main branch and the `.gitignore` file:

```sh
{
  mkdir my-bundles
  cd my-bundles
  git init -b main
  touch .gitignore
  echo target >> .gitignore
  echo .bundleutils.env >> .gitignore
  git add .gitignore
}
```

I've predefined some git variables for commit actions later - change if you wish:

```sh
{
  export GIT_COMMITTER_NAME="bundleutils-bot"
  export GIT_COMMITTER_EMAIL="bundleutils-bot@example.org"
  export GIT_AUTHOR_NAME="bundleutils-bot"
  export GIT_AUTHOR_EMAIL="bundleutils-bot@example.org"
  export GIT_ACTION=commit-only
}
```

Set the credentials and target URL:

```sh
{
  export BUNDLEUTILS_USERNAME=...
  export BUNDLEUTILS_PASSWORD=...
  export JENKINS_URL=...
}
```

Let's run the individual steps manually first:

```sh
bundleutils fetch # the raw bundle from the target server
```

```sh
bundleutils transform # the raw bundle into something consumable
```

```sh
bundleutils validate # the new consumable bundle against the target server to ensure it is valid
```

The bundle could now theoretically be committed to your git repository.

> [!NOTE]
> 2 minutes...

Let's do the same thing using the provided `bundle-management.sh`.

Please note the potential WARNING below before running the script.

```sh
../examples/tutorials/bundle-management/bundle-management.sh
```

> [!WARNING]
> **GITLEAKS IS ENABLED BY DEFAULT! This script may fail if you have sensitive data in your export!**
>
> (THIS IS NOT THE SCRIPTS FAULT)
>
> Following the principle of being [secure by design](https://en.wikipedia.org/wiki/Secure_by_design):
>
> - the `bundle-management.sh` script has a `gitleaks` check **enabled for all staged files**.
> - as a result, the check may fail if it finds sensitive data in your export.
> - to disable for this challenge, use `export GITLEAKS_CHECK=none`
> - see [the gitleaks exercise](#bonus-exercise-using-the-gitleaks-check) for more information.

**NOTE:** the new files in your git repository:

```sh
git show --stat
```

> [!NOTE]
> 4 minutes...

Make a change to your target controller and run the `bundle-management.sh` again:

```sh
../examples/tutorials/bundle-management/bundle-management.sh
```

**NOTE:** the new commit in your git repository:

```sh
{
  git show --stat
  git show
}
```

> [!NOTE]
> 5 minutes...aaaand stop!

## Bonus Exercise: Using `BUNDLEUTILS_GBL_URL_BASE_PATTERN`

More info under `bundleutils --help`.

Say you are maintaining multiple servers which all have similar URLs.

Instead of setting each URL separately, you can use the url base pattern to deduce the target URL.

Now you simply navigate to the bundle and run the command from there, e.g.:

```sh
export BUNDLEUTILS_GBL_URL_BASE_PATTERN="https://ci.acme.org/NAME"
```

```sh
$ cd cjoc/
$ bundleutils fetch -K BUNDLEUTILS_JENKINS_URL
https://ci.acme.org/cjoc

$ cd ../default-controller
$ bundleutils fetch -K BUNDLEUTILS_JENKINS_URL
https://ci.acme.org/default-controller

$ cd ../another-controller/
$ bundleutils fetch -K BUNDLEUTILS_JENKINS_URL
https://ci.acme.org/another-controller
```

## Bonus Exercise: find all online controllers

From the operations center you can find all online controllers.

```sh
$ bundleutils controllers
https://ci.acme.org/default-controller
https://ci.acme.org/another-controller
```

This can be useful for running bulk actions.

## Bonus Exercise: using `BUNDLEUTILS_INTERACTIVE`

More info under `bundleutils --help`.

Using the `--interactive` flag allows you to enter configuration parameters in real time.

```sh
$ bundleutils --interactive fetch -K
Please enter the value for BUNDLEUTILS_JENKINS_URL []: https://ci.acme.org/default-controller
Please enter the value for BUNDLEUTILS_USERNAME []: admin
Please enter the value for BUNDLEUTILS_PASSWORD []:
INFO:root:Evaluated configuration:
BUNDLEUTILS_BUNDLES_BASE=/workspace/my-bundles
BUNDLEUTILS_BUNDLE_NAME=default-controller
...
...
```

## Bonus Exercise: using the `gitleaks` check

### THE PROBLEM

You do not want to add sensitive values to git.

If your bundle configuration includes encrypted values, you will have to manage them somehow.

Options include:

- removing sensitive sections from the bundle and managing them separately outside of the bundle.
- using [Jenkins CasC Secrets](https://github.com/jenkinsci/configuration-as-code-plugin/blob/master/docs/features/secrets.adoc) and mounted volumes to provide values.
- using other external secret management tools.

The credentials feature used in the [transformation config](../../../bundleutilspkg/src/bundleutilspkg/data/configs/README.md#credentials) transforms credentials into their environment variable equivalent.

This makes it easy to deduce the expected variables to mount in the kubernetes secret.

### GitLeaks For Everything Else

This docker image comes with a version of [gitleaks](https://github.com/gitleaks/gitleaks), currently 8.26.0 at the time of writing.

Gitleaks can check your repository for secrets and prevent you from checking in sensitive data.

> [!IMPORTANT]
> This is a useful check in a export since ***people could hardcode secrets into job scripts, etc.***
>
> The `bundle-management.sh` will **only check staged files** before a commit.
> Please create an issue, contribute a PR, or use your own script if you need something else.

### GitLeaks Config

The gitleaks run is determined by setting `export GITLEAKS_CHECK=...`:

- `none`    - do not run checks
- `all`     - run the check on the staged files and all previous commits within the directory
- `staged`  - run the check on the staged files
- `<OTHER>` - defaults to staged

The gitleaks config  Setting `export GITLEAKS_CONFIG=...` is set, this is used.

- If not set, the config file packaged with this image is used
  - The file used is here: [.gitleaks.toml](./.gitleaks.toml)
  - This config extends the default gitleaks rules with:
    - a rule to detect Jenkins apiTokens
    - a rule to detect Jenkins encrypted values (`{AQAAABAAAA....`)
    - an allowlist regex to skip the `bu-hash-.*` values
- Use `export GITLEAKS_USE_EMBEDDED_CONFIG=false` if you do not want to use the packaged config file
  - e.g. you have your own `.gitleaks.toml` in the repository root

Let us see how it works.

```sh
# this will scan all commits in the BUNDLE_DIR, before scanning the staged files, if any.
export GITLEAKS_CHECK=all
```

Run the transform:

```sh
../examples/tutorials/bundle-management/bundle-management.sh
```

Depending on how good you've been, you may see something like this:

```sh
TRANSFORM: Running gitleaks check with gitleaks version 8.26.0
TRANSFORM: Using gitleaks config: /opt/bundleutils/work/examples/tutorials/bundle-management/.gitleaks.toml
TRANSFORM: Running gitleaks check on all files...

    ○
    │╲
    │ ○
    ○ ░
    ░    gitleaks

Finding:     accessKey: REDACTED
Secret:      REDACTED
RuleID:      aws-access-token
Entropy:     3.684184
File:        cjoc/jenkins.yaml
Line:        66
Commit:      af1b8d2a24f605fcc1990e9197eae172017da8d4
Author:      bundleutils-bot
Email:       bundleutils-bot@example.org
Date:        2025-05-15T13:07:52Z
Fingerprint: af1b8d2a24f605fcc1990e9197eae172017da8d4:cjoc/jenkins.yaml:aws-access-token:66

3:01PM INF 2 commits scanned.
3:01PM INF scanned ~28931 bytes (28.93 KB) in 118ms
3:01PM WRN leaks found: 1
TRANSFORM: Gitleaks found leaks. Please check the output.
```

**Resolution** - Make the changes, or disable the checks `¯\_(ツ)_/¯`

Let's remove the checks before continuing:

```sh
{
  export GITLEAKS_CHECK=none
  ../examples/tutorials/bundle-management/bundle-management.sh
}
```

## Bonus Exercise: using a custom `transform.yaml`

Transform will, by default, use the [default `transform.yaml`](../../../bundleutilspkg/src/bundleutilspkg/data/configs/transform.yaml) to transform the fetched raw bundle.

You will very likely want to use a custom `transform.yaml`.

The script will, by default, look for files in the following order:

- in the root directory
- in the `.bundleutils` directory
- in the internal configuration directory

A `(x)` marks files found, see:

```sh
$ bundleutils -l DEBUG transform -K
DEBUG:root:Set log level to: DEBUG
DEBUG:root:Setting BUNDLEUTILS_DRY_RUN...
DEBUG:root:Setting BUNDLEUTILS_STRICT...
DEBUG:root:Setting BUNDLEUTILS_CONFIGS_BASE...
DEBUG:root:Setting BUNDLEUTILS_JENKINS_URL...
DEBUG:root:Checking for config file:      ./transform.yaml
DEBUG:root:Checking for config file:      .bundleutils/transform.yaml
DEBUG:root:Checking for config file:  (x) /opt/bundleutils/.app/bundleutilspkg/src/bundleutilspkg/data/configs/transform.yaml
INFO:root:Using config file: /opt/bundleutils/.app/bundleutilspkg/src/bundleutilspkg/data/configs/transform.yaml
```

Simply place the file in the root directory and make the appropriate changes.

Example: copy and alter the file (removing the patch which deletes the labelAtoms):

```sh
cp ../../.app/bundleutilspkg/src/bundleutilspkg/data/configs/transform.yaml .
```

After copying, it will use the local file:

```sh
$ bundleutils -l DEBUG transform -K
DEBUG:root:Set log level to: DEBUG
DEBUG:root:Setting BUNDLEUTILS_DRY_RUN...
DEBUG:root:Setting BUNDLEUTILS_STRICT...
DEBUG:root:Setting BUNDLEUTILS_CONFIGS_BASE...
DEBUG:root:Setting BUNDLEUTILS_JENKINS_URL...
DEBUG:root:Checking for config file:  (x) ./transform.yaml
DEBUG:root:Checking for config file:      .bundleutils/transform.yaml
DEBUG:root:Checking for config file:  (x) /opt/bundleutils/.app/bundleutilspkg/src/bundleutilspkg/data/configs/transform.yaml
INFO:root:Using config file: ./transform.yaml
```

```sh
# we will remove the labelAtoms section
vi transform.yaml

$ diff ../bundleutilspkg/src/bundleutilspkg/data/configs/transform.yaml transform.yaml
7,8d6
<     path: /jenkins/labelAtoms
<   - op: remove
```

Running the `transform` command again now results in:

```sh
$ ../examples/tutorials/bundle-management/bundle-management.sh
BUNDLES: GIT_ACTION=commit-only
BUNDLES: Running bundleutils config...
INFO:root:Using config file: ./transform.yaml      # <-- Here we see it using the custom transform.yaml
```

With the new local transformation config, the labelAtoms are still present since we haven't removed them.

```sh
$ git show
commit 2ca070092dfe5eba33a68d411c77fe2c65f1ddb7 (HEAD -> main)
Author: bundleutils-bot <bundleutils-bot@example.org>
Date:   Sun Jun 22 19:40:12 2025 +0000

    Transform bundle cjoc (version: 2.492.2.2)

diff --git a/cjoc/bundle.yaml b/cjoc/bundle.yaml
index 09fe306..02adb57 100644
--- a/cjoc/bundle.yaml
+++ b/cjoc/bundle.yaml
@@ -2,7 +2,7 @@ apiVersion: 1
 id: cjoc
 description: |-
   Bundle for cjoc
-version: 6cd2969d-6d5a-2178-4938-908ba016fc4f
+version: cd9e1e39-f1af-73e2-4d6e-c1d4b36231a5
 jcasc:
 - jenkins.yaml
 plugins:
diff --git a/cjoc/jenkins.yaml b/cjoc/jenkins.yaml
index 61664aa..d4d71a9 100644
--- a/cjoc/jenkins.yaml
+++ b/cjoc/jenkins.yaml
@@ -112,6 +112,8 @@ jenkins:
   - OldData
   - hudson.util.DoubleLaunchChecker
   - controllerBundlesWithErrorMonitor
+  labelAtoms:                                            # <-- Here we see labelAtoms are now not deleted
+  - name: built-in
   log:
     recorders:
     - loggers:
```

Revert by removing the custom file:

```sh
{
  rm transform.yaml
  ../examples/tutorials/bundle-management/bundle-management.sh
}
```

## Bonus Exercise: using `--config auto`

Using the special `auto` value will check the target instance for version, type, and name.

It will then search in order:

- `transform-INSTANCE_NAME-CI_VERSION.yaml`
- `transform-CI_TYPE-CI_VERSION.yaml`
- `transform-INSTANCE_NAME.yaml`
- `transform-CI_TYPE.yaml`

This allows for individual configs for specific versions, type, and even instances.

e.g.

```sh
$ bundleutils -l DEBUG transform -K --config auto
...
...
DEBUG:root:Type: oc (taken from remote)
...
...
DEBUG:root:Version: 2.492.2.2 (taken from remote)
...
...
DEBUG:root:Checking for config file:      ./transform-cjoc-2.492.2.2.yaml
DEBUG:root:Checking for config file:      .bundleutils/transform-cjoc-2.492.2.2.yaml
DEBUG:root:Checking for config file:      ./transform-oc-2.492.2.2.yaml
DEBUG:root:Checking for config file:      .bundleutils/transform-oc-2.492.2.2.yaml
DEBUG:root:Checking for config file:      ./transform-cjoc.yaml
DEBUG:root:Checking for config file:      .bundleutils/transform-cjoc.yaml
DEBUG:root:Checking for config file:      ./transform-oc.yaml
DEBUG:root:Checking for config file:      .bundleutils/transform-oc.yaml
DEBUG:root:Checking for config file:      ./transform-2.492.2.2.yaml
DEBUG:root:Checking for config file:      .bundleutils/transform-2.492.2.2.yaml
DEBUG:root:Checking for config file:      ./transform.yaml
DEBUG:root:Checking for config file:      .bundleutils/transform.yaml
DEBUG:root:Checking for config file:      /opt/bundleutils/.app/bundleutilspkg/src/bundleutilspkg/data/configs/transform-cjoc-2.492.2.2.yaml
DEBUG:root:Checking for config file:      /opt/bundleutils/.app/bundleutilspkg/src/bundleutilspkg/data/configs/transform-oc-2.492.2.2.yaml
DEBUG:root:Checking for config file:      /opt/bundleutils/.app/bundleutilspkg/src/bundleutilspkg/data/configs/transform-cjoc.yaml
DEBUG:root:Checking for config file:      /opt/bundleutils/.app/bundleutilspkg/src/bundleutilspkg/data/configs/transform-oc.yaml
DEBUG:root:Checking for config file:      /opt/bundleutils/.app/bundleutilspkg/src/bundleutilspkg/data/configs/transform-2.492.2.2.yaml
DEBUG:root:Checking for config file:  (x) /opt/bundleutils/.app/bundleutilspkg/src/bundleutilspkg/data/configs/transform.yaml
INFO:root:Using config file: /opt/bundleutils/.app/bundleutilspkg/src/bundleutilspkg/data/configs/transform.yaml
```

## Bonus Exercise: avoid downloading expensive `items.yaml`

### PROBLEM

Sometimes it is not required to include the items in the bundle, e.g.

- it is simply not required by the corporate management
- exporting the `items.yaml` is computationally expensive due to the large number of jobs

### PROPOSED SOLUTION

In this case, either add the `--ignore-items` option to the fetch command, or set `export BUNDLEUTILS_FETCH_IGNORE_ITEMS=true` environment variable.

Let's try it out in our example:

```sh
{
  export BUNDLEUTILS_FETCH_IGNORE_ITEMS=true
  ../examples/tutorials/bundle-management/bundle-management.sh
  git show --stat
}
```

Example output:

```sh
...
...
INFO:root:Wrote target/fetched/cjoc/bundle.yaml
INFO:root:Wrote target/fetched/cjoc/jenkins.yaml
INFO:root:Wrote target/fetched/cjoc/plugins.yaml
INFO:root:Wrote target/fetched/cjoc/rbac.yaml
INFO:root:Not downloading the items.yaml (computationally expensive)
...
...
######################################
BUNDLES: Summary of the transform so far:
######################################

BUNDLES: Bundle validation PASSED.
BUNDLES: cjoc - Git check. Committed changes.
######################################
commit 42ce936a33ad4fbd5b1e1f710b1939005c5cc3e9 (HEAD -> main)
Author: bundleutils-bot <bundleutils-bot@example.org>
Date:   Sun Jun 22 19:52:48 2025 +0000

    Transform bundle cjoc (version: 2.492.2.2)

 cjoc/bundle.yaml |    4 +-
 cjoc/items.yaml  | 1393 --------------------------------------------------------------------------------------------------------------------------------------------------------------------
 2 files changed, 1 insertion(+), 1396 deletions(-)
```

And revert our changes (re-adding the items):

```sh
{
  export BUNDLEUTILS_FETCH_IGNORE_ITEMS=false
  ../examples/tutorials/bundle-management/bundle-management.sh
  git show --stat
}
```

So, just to recap:

**Using...** `export BUNDLEUTILS_FETCH_IGNORE_ITEMS=false`

```sh
❯ time BUNDLEUTILS_FETCH_IGNORE_ITEMS=false bundleutils fetch
INFO:root:Read YAML from url: http://ci.acme.org/default-controller/core-casc-export
...
...
1,83s user 0,04s system 16% cpu 21,317 total    # <-- 21 seconds

❯ find target/docs                              # <-- contains items.yaml
target/docs
target/docs/rbac.yaml
target/docs/items.yaml
target/docs/plugins.yaml
target/docs/plugin-catalog.yaml
target/docs/bundle.yaml
target/docs/jenkins.yaml
```

**Using...** `export BUNDLEUTILS_FETCH_IGNORE_ITEMS=true`

```sh
❯ time BUNDLEUTILS_FETCH_IGNORE_ITEMS=true bundleutils fetch
INFO:root:Not downloading the items.yaml (computationally expensive)
...
...
1,10s user 0,06s system 23% cpu 4,863 total     # <-- 5 seconds

❯ find target/docs                              # <-- no items.yaml
target/docs
target/docs/rbac.yaml
target/docs/plugins.yaml
target/docs/plugin-catalog.yaml
target/docs/bundle.yaml
target/docs/jenkins.yaml
```

## Bonus Exercise: version based bundles

It might be useful to track the CI versions on bundles when performing my-bundles.

- The controller with the name `team-mobility` would normally result in a bundle of the same name.
- Wouldn't it be nice if the bundle was called `team-mobility-2.492.3.5` instead?
- This way, changes within a particular version could be tracked more easily.

This is where the `BUNDLEUTILS_GBL_APPEND_VERSION` comes in.

Up until now, we have simple bundle names. E.g.

```sh
bundle-user@66df4d9bcd27:/opt/bundleutils/work/my-bundles$ git ls-files
.gitignore
team-mobility/bundle.yaml
team-mobility/items.yaml
team-mobility/jenkins.yaml
team-mobility/plugins.yaml
```

Let us use version based bundle names:

```sh
{
  export BUNDLEUTILS_GBL_APPEND_VERSION=true
  ../examples/tutorials/bundle-management/bundle-management.sh
  git show --stat
}
```

Performing the transform again appends the version to the bundle:

```sh
bundle-user@66df4d9bcd27:/opt/bundleutils/work/my-bundles$ ../examples/tutorials/bundle-management/bundle-management.sh
...
...
AUDITING: Committing changes to team-mobility-2.479.3.1
[main fda2da8] Transform bundle team-mobility-2.479.3.1 (version: 2.479.3.1)
 4 files changed, 1053 insertions(+)
 create mode 100644 team-mobility-2.479.3.1/bundle.yaml
 create mode 100644 team-mobility-2.479.3.1/items.yaml
 create mode 100644 team-mobility-2.479.3.1/jenkins.yaml
 create mode 100644 team-mobility-2.479.3.1/plugins.yaml
AUDITING: Commit: YOUR_GIT_REPO/commit/fda2da8 Transform bundle team-mobility-2.479.3.1 (version: 2.479.3.1)
AUDITING: Bundle transform complete.
```

List the files to see:

```sh
bundle-user@66df4d9bcd27:/opt/bundleutils/work/my-bundles$ git ls-files
.gitignore
team-mobility-2.479.3.1/bundle.yaml
team-mobility-2.479.3.1/items.yaml
team-mobility-2.479.3.1/jenkins.yaml
team-mobility-2.479.3.1/plugins.yaml
team-mobility/bundle.yaml
team-mobility/items.yaml
team-mobility/jenkins.yaml
team-mobility/plugins.yaml
```

## Bonus Exercise: version based bundles (and preserving git history)

**NOTE:** you must have completed [Bonus Exercise: version based bundles](#bonus-exercise-version-based-bundles) before doing this exercise.

Following on from the version based bundles example, you may want to:

- Have version based bundles for the sake of transparency
- Still preserve the git history on individual directories

Enter the mandatory variable `GIT_BUNDLE_PRESERVE_HISTORY`.

The [./bundle-management.sh](./bundle-management.sh) file needs to know what to do when:

- a new version is detected
- a previous version exists

> Should the git history of the previous version be preserved in the new version, or should we add the files and start a new git history?

**NONE:** If not set at all, the script will fail.

**FALSE:** Setting `export GIT_BUNDLE_PRESERVE_HISTORY=false` will:

- add a new/fresh directory for the new version
- commit the changes
- the previous versions directory will retain its own git history
- the new versions directory will have a no previous git history

**TRUE:** Setting `export GIT_BUNDLE_PRESERVE_HISTORY=true` will:

- rename the previous versions directory to the new versions directory
- commit the changes (thus preserving the git history)
- add a new/fresh directory previous version with the last known configuration
- commit the changes

**Let's try this in our example:**

Preparation: Normally, this will happen organically when upgrading controllers. However, for the challenge, we will just immitate having a previous version installed.

- set your current version - enter: `MY_CURRENT_VERSION=team-mobility-2.479.3.1`
- and a 'pretend' earlier version - enter: `MY_PREVIOUS_VERSION=team-mobility-2.479.3.0`.

Now run:

```sh
{
  git mv "$MY_CURRENT_VERSION" "$MY_PREVIOUS_VERSION"
  git commit -m "We are just pretending this is an earlier version" "$MY_CURRENT_VERSION" "$MY_PREVIOUS_VERSION"
  git ls-files
}
```

Now the 'previous' version is in place, let's set the environment variable to preserve the git history.

```sh
export GIT_BUNDLE_PRESERVE_HISTORY=true
```

And perform the transform again:

```sh
../examples/tutorials/bundle-management/bundle-management.sh
```

You will see something like:

```sh
bundle-user@66df4d9bcd27:/opt/bundleutils/work/my-bundles$ ../examples/tutorials/bundle-management/bundle-management.sh
...
...
AUDITING: Bundle team-mobility-2.479.3.1 not found. Looking for a previous version...
AUDITING: Migrating from previous version team-mobility-2.479.3.0 to team-mobility-2.479.3.1
[main 40ee945] Renaming team-mobility-2.479.3.0 to team-mobility-2.479.3.1 to preserve the git history
 4 files changed, 0 insertions(+), 0 deletions(-)
 rename {team-mobility-2.479.3.0 => team-mobility-2.479.3.1}/bundle.yaml (100%)
 rename {team-mobility-2.479.3.0 => team-mobility-2.479.3.1}/items.yaml (100%)
 rename {team-mobility-2.479.3.0 => team-mobility-2.479.3.1}/jenkins.yaml (100%)
 rename {team-mobility-2.479.3.0 => team-mobility-2.479.3.1}/plugins.yaml (100%)
[main aa9b096] Last known state of team-mobility-2.479.3.0 before moving to team-mobility-2.479.3.1
 5 files changed, 1055 insertions(+)
 create mode 100644 .gitignore
 create mode 100644 team-mobility-2.479.3.0/bundle.yaml
 create mode 100644 team-mobility-2.479.3.0/items.yaml
 create mode 100644 team-mobility-2.479.3.0/jenkins.yaml
 create mode 100644 team-mobility-2.479.3.0/plugins.yaml
...
...
```

The git history of the 'new' version is a continuation of the old...

```sh
bundle-user@66df4d9bcd27:/opt/bundleutils/work/my-bundles$ git log --oneline team-mobility-2.479.3.1
40ee945 Renaming team-mobility-2.479.3.0 to team-mobility-2.479.3.1 to preserve the git history
380be9e We are just pretending this is an earlier version
fda2da8 Transform bundle team-mobility-2.479.3.1 (version: 2.479.3.1)
```

## Bonus Exercise: all in one

The `bundle-management.sh` has a special feature which, given an operation center URL, will:

- find all ONLINE controllers
- perform an transform on each
- perform a final transform on the operation center

```sh
bundle-user@b7df010ce271:/opt/bundleutils/work/my-bundles$ ../examples/tutorials/bundle-management/bundle-management.sh cjoc-and-online-controllers
...
...
AUDITING: Transform online controllers and then the OC:
https://ci.acme.org/transformed-1/
https://ci.acme.org/transformed-2/
...
...
INFO:root:Read YAML from url: https://ci.acme.org/transformed-1//core-casc-export
...
...
INFO:root:Read YAML from url: https://ci.acme.org/transformed-2//core-casc-export
...
...
INFO:root:Read YAML from url: https://ci.acme.org/cjoc//core-casc-export
```

The resulting commits:

```sh
bundle-user@b7df010ce271:/opt/bundleutils/work/my-bundles$ git log --oneline
0696183 (HEAD -> main) Transform bundle cjoc (version: 2.492.2.3)
8881562 Transform bundle transformed-2 (version: 2.492.2.3)
380be9e Transform bundle transformed-1 (version: 2.492.2.3)
```

## Running in Production

To run this in production, we need a way of running these commands automatically.

### Pipeline Job

- For controllers, a [Jenkinsfile.singleServer](./Jenkinsfile.singleServer) has been provided.
- Create a repository
- Place the Jenkinsfile a the root level
- Ensure the referenced credentials exist
- On the target controller, create a pipeline job which:
  - Uses the repository
  - Discovers the main branch only
  - Includes the option "Check out to a local branch"
  - Includes the Jenkinsfile as the build script
- Run the job

### Pipeline Job - All Online Controllers

- For an admin controller, a [Jenkinsfile.allServers](./Jenkinsfile.allServers) has been provided.
- Create a repository
- Place the Jenkinsfile a the root level
- **Replace the URL environment variable in the Jenkinsfile**
- Ensure the referenced credentials exist
- On the target controller, create a pipeline job which:
  - Uses the repository
  - Discovers the main branch only
  - Includes the option "Check out to a local branch"
  - Includes the Jenkinsfile as the build script
- Run the job

### Operation Center

Running on an operation center is more complicated since running pipelines is not permitted.

There are various methods, such as:

- Kubernetes Cloud:
  - Adding a kubernetes cloud, pod template, and appropriate label to run the `ci-bundle-utils` container.
  - Create a freestyle job which can only run with that particular label.
    - Add the git repository
    - Add credential bindings for the aforementioned credentials
    - Run the appropriate `transform.sh` command as before

- Static Agent
  - Create a static agent with the appropriate label
  - Create a kubernetes pod/deployment and connect to the operations center
  - Create the freestyle job as mentioned above

- On one of the controllers:
  - create a special **CJOC** pipeline job similar to one above:
  - Add the `BUNDLEUTILS_JENKINS_URL=<operations-center-url>` environment variable instead of using the controllers own `JENKINS_URL`

Once created, run the job.

### Git over SSH

Sometimes, by policy, it is required to use the git SSH protocol rather than HTTPS.
This [Pipeline](Jenkinsfile.allServersGitSSHPush) shows, how git push over SSH can be utilised.

The Pipeline requires additional settings:

* environment variables:
```
GIT_ACTION = 'push'
GIT_REPO = '<YOUR_GITHUB_SSH_REPO_URL>'
```
* Jenkins SSH Credentials (GitHub SSH private key)
