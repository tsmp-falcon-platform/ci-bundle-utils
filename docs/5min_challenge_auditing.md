# 5 Minute Challenge: Auditing

This tutorial will explain how to have your controller audited in 5 mins.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Prerequisites](#prerequisites)
  - [Minimum Required Permissions](#minimum-required-permissions)
- [3, 2, 1...Go](#3-2-1go)
- [Bonus Exercise #1: using `BUNDLEUTILS_CREDENTIAL_HASH`](#bonus-exercise-1-using-bundleutils_credential_hash)
- [Bonus Exercise #2: using a custom `normalize.yaml`](#bonus-exercise-2-using-a-custom-normalizeyaml)
- [Bonus Exercise #3: avoid downloading expensive `items.yaml`](#bonus-exercise-3-avoid-downloading-expensive-itemsyaml)
- [Bonus Exercise #4: version based bundles](#bonus-exercise-4-version-based-bundles)
- [Bonus Exercise #5: version based bundles (and preserving git history)](#bonus-exercise-5-version-based-bundles-and-preserving-git-history)
- [Bonus Exercise #6: all in one](#bonus-exercise-6-all-in-one)
- [Running in Production](#running-in-production)
  - [Pipeline Job](#pipeline-job)
  - [Operation Center](#operation-center)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Prerequisites

- **TARGET URL:** One or more target URL's (controller or operations center)
- **PLUGINS:** The following plugins are installed:
  - On both: `cloudbees-casc-client`
  - On operations center: `cloudbees-casc-items-server`
  - On controller: `cloudbees-casc-items-controller`
- **CREDENTIALS:** A valid username and corresponding API token, referenced below as:
  - `BUNDLEUTILS_USERNAME`
  - `BUNDLEUTILS_PASSWORD`

### Minimum Required Permissions

The minimum set of permissions needed for the user are as follows:

```mono
CloudBees CasC Permissions/Administer
CloudBees CasC Permissions/Checkout
CloudBees CasC Permissions/Item
CloudBees CasC Permissions/Read
CloudBees CasC Permissions/ReadCheckout
Agent/ExtendedRead
Overall/Read
Overall/SystemRead
Job/ExtendedRead
View/Read
```

In RBAC, this would look like (please ignore the ordering - it came out this way):

```yaml
removeStrategy:
  rbac: SYNC
roles:
- permissions:
  - hudson.model.Hudson.Read
  - com.cloudbees.jenkins.plugins.casc.permissions.CascPermission.Item
  - hudson.model.View.Read
  - hudson.model.Hudson.SystemRead
  - hudson.model.Computer.ExtendedRead
  - hudson.model.Item.ExtendedRead
  - com.cloudbees.jenkins.plugins.casc.permissions.CascPermission.Administer
  name: validate-casc
```

> [!NOTE]
> System properties can be used to enable the [Overall/SystemRead](https://www.jenkins.io/doc/book/managing/system-properties/#jenkins-security-systemreadpermission) and [Computer/ExtendedRead and Item/ExtendedRead](https://www.jenkins.io/doc/book/managing/system-properties/#hudson-security-extendedreadpermission) permissions.
>
> If you do not have the SystemRead available, `hudson.model.Hudson.Administer` will be needed.

## 3, 2, 1...Go

A common usecase is to audit your controllers configuration. We want to:

- save the current state of your controller
- obfuscate any credentials or sensitive data
- save the results to a git repository

> [!NOTE]
> 1 minute...

Start a container:

```sh
{
  docker pull ghcr.io/tsmp-falcon-platform/ci-bundle-utils
  docker run --rm -it --name bundleutils --entrypoint bash ghcr.io/tsmp-falcon-platform/ci-bundle-utils
}
```

Create a test repo with a default main branch and the `.gitignore` file:

```sh
{
  mkdir audits
  cd audits
  git init -b main
  touch .gitignore
  echo target >> .gitignore
  echo .bundleutils.env >> .gitignore
  git add .gitignore
}
```

> [!NOTE]
> 2 minutes...

Run the `audit.sh` with `setup` mode to set the appropriate environment variables.

I've predefined some git variables - change if you wish:

```sh
{
  export GIT_COMMITTER_NAME="bundleutils-bot"
  export GIT_COMMITTER_EMAIL="bundleutils-bot@example.org"
  export GIT_ACTION=commit-only
  ../examples/tutorials/auditing/audit.sh setup
}
```

**NOTE:** the new files in your git repository:

```sh
git show --stat
```

> [!NOTE]
> 4 minutes...

Make a change to your target controller and run the `audit.sh` again:

```sh
../examples/tutorials/auditing/audit.sh
```

**NOTE:** the new commit in your git repository:

```sh
{
  git show --stat
  git show
}
```

> [!NOTE]
> 5 minutes...and stop!

## Bonus Exercise #1: using `BUNDLEUTILS_CREDENTIAL_HASH`

Auditing will, by default, hash any encrypted values it finds, so that...

Original:

```yaml
       - usernamePassword:
           description: |-
             My secret thing
           id: my-secret-thing
           password: '{AQAAABAAAAAwqlTuvlbCX3zD6/M5K....}'
           scope: GLOBAL
           username: bob
```

**Using...** `export BUNDLEUTILS_CREDENTIAL_HASH=true`

```yaml
       - usernamePassword:
           description: |-
             My secret thing
           id: my-secret-thing
           password: 0292890669736921577497db2ea2f22cadb9778dcb0241456750a2dc2a23c941
           scope: GLOBAL
           username: bob
```

This is useful for noticing when the encrypted value changes without actually knowing the encrypted value.

> [!WARNING]
> If a credential object is updated, the encrypted value on disk is changed and thus the hash value with it.
>
> Credentials are re-encrypted when:
>
> - the credentials are changed in the UI (even it the change does not include the credential value, e.g. changing the description)
> - reloading a CasC bundle which includes credentials (in this case, the credentials are recreated and thus re-encrypted)

If false positives such as those above are not wanted, setting `BUNDLEUTILS_CREDENTIAL_HASH=false` will use a env var like representation instead.

**Using...** `export BUNDLEUTILS_CREDENTIAL_HASH=false`

```yaml
       - usernamePassword:
           description: |-
             My secret thing
           id: my-secret-thing
-          password: a9740aca387854a95ffc0272491d872781f48d178ddc4d410064ea927046e5ab
+          password: ${MY_SECRET_THING_PASSWORD}
           scope: GLOBAL
           username: bob
```

## Bonus Exercise #2: using a custom `normalize.yaml`

Auditing will, by default, use the [default `normalize.yaml`](../bundleutilspkg/src/bundleutilspkg/data/configs/normalize.yaml) to transform the fetched bundle.

If you wish to use a custom `normalize.yaml`, simply place the file in the root directory and make the appropriate changes.

Example: copy and alter the file (removing the patch which deletes the labelAtoms):

```sh
cp ../../.app/bundleutilspkg/src/bundleutilspkg/data/configs/normalize.yaml .
```

```sh
vi normalize.yaml
```

Example Output:

```sh
bundle-user@82b69d6e24b9:/opt/bundleutils/work/audits$ cp ../../.app/bundleutilspkg/src/bundleutilspkg/data/configs/normalize.yaml .

bundle-user@82b69d6e24b9:/opt/bundleutils/work/audits$ vi normalize.yaml

bundle-user@82b69d6e24b9:/opt/bundleutils/work/audits$ diff ../../.app/bundleutilspkg/src/bundleutilspkg/data/configs/normalize.yaml normalize.yaml
7,9d6
<     # these labels are dynamic based on the agents available
<   - op: remove
<     path: /jenkins/labelAtoms
```

Running the audit again now results in:

```sh
bundle-user@82b69d6e24b9:/opt/bundleutils/work/audits$ ../examples/tutorials/auditing/audit.sh
AUDITING: GIT_ACTION=commit-only
AUDITING: Running bundleutils extract-name-from-url...
AUDITING: Running bundleutils fetch -t target/fetched/cjoc
...
...
INFO:root:Using normalize.yaml in the current directory            # <-- Here we see it using the custom normalize.yaml
INFO:root:Transformation: processing normalize.yaml
...
...
diff --git a/cjoc/jenkins.yaml b/cjoc/jenkins.yaml
index 85649d5..7e562cd 100644
--- a/cjoc/jenkins.yaml
+++ b/cjoc/jenkins.yaml
@@ -109,6 +109,8 @@ jenkins:
   - OldData
   - hudson.util.DoubleLaunchChecker
   - controllerBundlesWithErrorMonitor
+  labelAtoms:                                                     # <-- Here we see labelAtoms are now not deleted
+  - name: built-in
   log:
     recorders:
     - loggers:
AUDITING: Committing changes to cjoc
[main a5e4b17] Audit bundle cjoc
 1 file changed, 2 insertions(+)
AUDITING: Commit: YOUR_GIT_REPO/commit/a5e4b17 Audit bundle cjoc
AUDITING: Bundle audit complete.
```

Revert by removing the custom file:

```sh
{
  rm normalize.yaml
  ../examples/tutorials/auditing/audit.sh
}
```

## Bonus Exercise #3: avoid downloading expensive `items.yaml`

Sometimes it is not required to include the items in the bundle, e.g.

- it is simply not required by the corporate management
- exporting the `items.yaml` is computationally expensive due to the large number of jobs

In this case, either add the `--ignore-items` option to the fetch command, or set `export BUNDLEUTILS_FETCH_IGNORE_ITEMS=true` environment variable.

Let's try it out in our example:

```sh
{
  export BUNDLEUTILS_FETCH_IGNORE_ITEMS=true
  ../examples/tutorials/auditing/audit.sh
  git show --stat
}
```

And revert our changes (re-adding the items):

```sh
{
  export BUNDLEUTILS_FETCH_IGNORE_ITEMS=false
  ../examples/tutorials/auditing/audit.sh
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
1,83s user 0,04s system 16% cpu 11,317 total    # <-- 11 seconds

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

## Bonus Exercise #4: version based bundles

It might be useful to track the CI versions on bundles when performing audits.

- The controller with the name `team-mobility` would normally result in a bundle of the same name.
- Wouldn't it be nice if the bundle was called `team-mobility-2.492.3.5` instead?
- This way, changes within a particular version could be tracked more easily.

This is where the `BUNDLEUTILS_AUTO_ENV_APPEND_VERSION` comes in.

Up until now, we have simple bundle names. E.g.

```sh
bundle-user@66df4d9bcd27:/opt/bundleutils/work/audits$ git ls-files
.gitignore
team-mobility/bundle.yaml
team-mobility/items.yaml
team-mobility/jenkins.yaml
team-mobility/plugins.yaml
```

Let us use version based bundle names:

```sh
{
  export BUNDLEUTILS_AUTO_ENV_APPEND_VERSION=true
  ../examples/tutorials/auditing/audit.sh
  git show --stat
}
```

Performing the audit again appends the version to the bundle:

```sh
bundle-user@66df4d9bcd27:/opt/bundleutils/work/audits$ ../examples/tutorials/auditing/audit.sh
...
...
AUDITING: Committing changes to team-mobility-2.479.3.1
[main fda2da8] Audit bundle team-mobility-2.479.3.1 (version: 2.479.3.1)
 4 files changed, 1053 insertions(+)
 create mode 100644 team-mobility-2.479.3.1/bundle.yaml
 create mode 100644 team-mobility-2.479.3.1/items.yaml
 create mode 100644 team-mobility-2.479.3.1/jenkins.yaml
 create mode 100644 team-mobility-2.479.3.1/plugins.yaml
AUDITING: Commit: YOUR_GIT_REPO/commit/fda2da8 Audit bundle team-mobility-2.479.3.1 (version: 2.479.3.1)
AUDITING: Bundle audit complete.
```

List the files to see:

```sh
bundle-user@66df4d9bcd27:/opt/bundleutils/work/audits$ git ls-files
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

## Bonus Exercise #5: version based bundles (and preserving git history)

**NOTE:** you must have completed [Bonus Exercise #4: version based bundles](#bonus-exercise-4-version-based-bundles) before doing this exercise.

Following on from the version based bundles example, you may want to:

- Have version based bundles for the sake of transparency
- Still preserve the git history on individual directories

Enter the mandatory variable `GIT_BUNDLE_PRESERVE_HISTORY`.

The [../examples/tutorials/auditing/audit.sh](../examples/tutorials/auditing/audit.sh) file needs to know what to do when:

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

And perform the audit again:

```sh
../examples/tutorials/auditing/audit.sh
```

You will see something like:

```sh
bundle-user@66df4d9bcd27:/opt/bundleutils/work/audits$ ../examples/tutorials/auditing/audit.sh
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
bundle-user@66df4d9bcd27:/opt/bundleutils/work/audits$ git log --oneline team-mobility-2.479.3.1
40ee945 Renaming team-mobility-2.479.3.0 to team-mobility-2.479.3.1 to preserve the git history
380be9e We are just pretending this is an earlier version
fda2da8 Audit bundle team-mobility-2.479.3.1 (version: 2.479.3.1)
```

## Bonus Exercise #6: all in one

The `audit.sh` has a special feature which, given an operation center URL, will:

- find all ONLINE controllers
- perform an audit on each
- perform a final audit on the operation center

```sh
bundle-user@b7df010ce271:/opt/bundleutils/work/audits$ ../examples/tutorials/auditing/audit.sh cjoc-and-online-controllers
...
...
AUDITING: Auditing online controllers and then the OC:
https://ci.acme.org/audited-1/
https://ci.acme.org/audited-2/
...
...
INFO:root:Read YAML from url: https://ci.acme.org/audited-1//core-casc-export
...
...
INFO:root:Read YAML from url: https://ci.acme.org/audited-2//core-casc-export
...
...
INFO:root:Read YAML from url: https://ci.acme.org/cjoc//core-casc-export
```

The resulting commits:

```sh
bundle-user@b7df010ce271:/opt/bundleutils/work/audits$ git log --oneline
0696183 (HEAD -> main) Audit bundle cjoc (version: 2.492.2.3)
8881562 Audit bundle audited-2 (version: 2.492.2.3)
380be9e Audit bundle audited-1 (version: 2.492.2.3)
```

## Running in Production

To run this in production, we need a way of running these commands automatically.

### Pipeline Job

- For controllers, a [Jenkinsfile](../examples/tutorials/auditing/Jenkinsfile) has been provided.
- Create a repository
- Place the Jenkinsfile a the root level
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
    - Run the appropriate `audit.sh` command as before

- Static Agent
  - Create a static agent with the appropriate label
  - Create a kubernetes pod/deployment and connect to the operations center
  - Create the freestyle job as mentioned above

- On one of the controllers:
  - create a special **CJOC** pipeline job similar to one above:
  - Add the `BUNDLEUTILS_JENKINS_URL=<operations-center-url>` environment variable instead of using the controllers own `JENKINS_URL`

Once created, run the job.
