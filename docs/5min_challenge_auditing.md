# 5 Minute Challenge: Auditing

This tutorial will explain have your controller audited in 5 mins.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Prerequisites](#prerequisites)
- [3, 2, 1...Go](#3-2-1go)
- [Bonus Exercise #1: using `BUNDLEUTILS_CREDENTIAL_HASH`](#bonus-exercise-1-using-bundleutils_credential_hash)
- [Bonus Exercise #2: using a custom `normalize.yaml`](#bonus-exercise-2-using-a-custom-normalizeyaml)
- [Bonus Exercise #3: avoid downloading expensive `items.yaml`](#bonus-exercise-3-avoid-downloading-expensive-itemsyaml)
- [Running in Production](#running-in-production)
  - [Pipeline Job](#pipeline-job)
  - [Operation Center](#operation-center)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Prerequisites

- One or more target URL's (controller or operations center)
- A valid username and corresponding API token

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

Make a change to your target controller the `audit.sh` after making a change:

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

If this is not wanted, setting `BUNDLEUTILS_CREDENTIAL_HASH=false` will use a env var like representation instead.

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

## Bonus Exercise #3: avoid downloading expensive `items.yaml`

Sometimes it is not required to include the items in the bundle, e.g.

- it is simply not required by the corporate management
- exporting the `items.yaml` is computationally expensive due to the large number of jobs

In this case, either add the `--ignore-items` option to the fetch command, or set `export BUNDLEUTILS_FETCH_IGNORE_ITEMS=true` environment variable.

**Using...** `export BUNDLEUTILS_FETCH_IGNORE_ITEMS=false`

```sh
❯ time BUNDLEUTILS_FETCH_IGNORE_ITEMS=false bundleutils fetch
INFO:root:Read YAML from url: http://35.227.58.163.nip.io/default-controller/core-casc-export
...
...
1,83s user 0,04s system 16% cpu 11,317 total    # <-- 11 seconds

❯ find target/docs
target/docs
target/docs/rbac.yaml
target/docs/items.yaml                          # <-- items downloaded
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
