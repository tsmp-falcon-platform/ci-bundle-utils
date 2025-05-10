# Bundle Audits

This template repository contains files audit CI instances using the [ci-bundle-utils](https://github.com/tsmp-falcon-platform/ci-bundle-utils) tool.

## Local testing

Checkout this repository, then create a local docker bundleutils instance:

```sh
{
  # remove any current containers
  docker rm -f bundleutils

  # start the container
  IMAGE=ghcr.io/tsmp-falcon-platform/ci-bundle-utils
  docker pull "$IMAGE"
  docker run -v $(pwd):/repo -d --name bundleutils --entrypoint sleep "$IMAGE" infinity

  # copy the files and init a test repository
  docker exec bundleutils bash -c 'cp -r /repo .; cd repo; rm -rf .git/hooks/*;'

  # exec into container
  docker exec -it bundleutils bash
}
```

### Setup Environment Variables

You should now be in the container.

Setup the necessary environment variables **interactively**.

- run the following
- follow the instructions
- save the export statements for use later

```sh
{
  cd repo
  ./audit.sh setup
}
```

Alternatively, setup your environment variables manually.

For git commits:

```sh
# git details
export GIT_COMMITTER_NAME="bundleutils-bot"              # change as appropriate
export GIT_COMMITTER_EMAIL="bundleutils-bot@example.org" # change as appropriate
export GIT_AUTHOR_NAME="${GIT_COMMITTER_NAME}"
export GIT_AUTHOR_EMAIL="${GIT_COMMITTER_EMAIL}"
```

For your target instance:

```sh
# authentication details
export BUNDLEUTILS_PASSWORD=11....                       # your API token
export BUNDLEUTILS_USERNAME=bob                          # your username
export JENKINS_URL='https://ci.acme.org/controller1'     # the target instance
```

Git action. Since we are only testing, set the appropriate action to `commit-only`

```sh
# since this is a test, do not try and push changes to remote
export GIT_ACTION=commit-only
```

Run the script and examine the first commit:

```sh
# run the script
./audit.sh

# check the commit
git log

# see the commit contents
git --no-pager show --stat
git --no-pager show
```

Make a change to your target controller, run the script again and examine the second commit:

```sh
# making some change to my target controller...

# run the script
./audit.sh

# check the commit
git log

# see the commit contents
git --no-pager show --stat
git --no-pager show
```

### Sample output

```sh
bundle-user@e2f060cb4c8f:/opt/bundleutils/work/repo$ ./audit.sh
AUDITING: GIT_ACTION=commit-only
AUDITING: Running bundleutils extract-name-from-url...
AUDITING: Running bundleutils fetch...
INFO:root:Read YAML from url: http://35.227.58.163.nip.io/ken1/core-casc-export
INFO:root:Wrote target/docs/bundle.yaml
INFO:root:Wrote target/docs/jenkins.yaml
INFO:root:Wrote target/docs/plugins.yaml
INFO:root:Wrote target/docs/rbac.yaml
INFO:root:Wrote target/docs/items.yaml
...
...
AUDITING: Committing changes to ken1
[main 64be2f9] Audit bundle ken1
 4 files changed, 1032 insertions(+)
 create mode 100644 ken1/bundle.yaml
 create mode 100644 ken1/items.yaml
 create mode 100644 ken1/jenkins.yaml
 create mode 100644 ken1/plugins.yaml
AUDITING: Commit: YOUR_GIT_REPO/commit/64be2f9 Audit bundle ken1
AUDITING: Bundle audit complete.
```

Second run after change

```sh
bundle-user@e2f060cb4c8f:/opt/bundleutils/work/repo$ ./audit.sh
AUDITING: GIT_ACTION=commit-only
AUDITING: Running bundleutils extract-name-from-url...
AUDITING: Running bundleutils fetch...
INFO:root:Read YAML from url: http://35.227.58.163.nip.io/ken1/core-casc-export
INFO:root:Wrote target/docs/bundle.yaml
INFO:root:Wrote target/docs/jenkins.yaml
INFO:root:Wrote target/docs/plugins.yaml
INFO:root:Wrote target/docs/rbac.yaml
INFO:root:Wrote target/docs/items.yaml
...
...
diff --git a/ken1/items.yaml b/ken1/items.yaml
index f1d03d0..c1b8e36 100644
--- a/ken1/items.yaml
+++ b/ken1/items.yaml
@@ -4,7 +4,7 @@ removeStrategy:
 items:
 - kind: pipeline
   name: artifact-filler
-  concurrentBuild: true
+  concurrentBuild: false
   definition:
     cpsFlowDefinition:
       sandbox: true
AUDITING: Committing changes to ken1
[main c33629a] Audit bundle ken1
 1 file changed, 1 insertion(+), 1 deletion(-)
AUDITING: Commit: YOUR_GIT_REPO/commit/c33629a Audit bundle ken1
AUDITING: Bundle audit complete.
```

## Testing via Jenkins

### Create Repository

Repository:

- create your repository from this template (see [here](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template) for more details).
- create your own repository with the same files

Jenkins:

- create the credentials needed in the Jenkinsfile
- create a pipeline job
  - add the repository as the git source
  - building the main branch only
  - add checkout to local branch and leave field blank
  - add the Jenkinsfile
- run the build

### Example Pipeline Config

```yaml
kind: pipeline
name: bundleutils-audit
concurrentBuild: true
definition:
  cpsScmFlowDefinition:
    scriptPath: Jenkinsfile
    scm:
      scmGit:
        extensions:
        - localBranch: {
            }
        userRemoteConfigs:
        - userRemoteConfig:
            credentialsId: github-token-rw
            url: https://github.com/tsmp-falcon-platform/ken1-auditing
        branches:
        - branchSpec:
            name: '*/main'
    lightweight: true
description: ''
disabled: false
displayName: bundleutils-audit
resumeBlocked: false
```
