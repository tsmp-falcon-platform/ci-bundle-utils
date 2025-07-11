# 📦 `bundleutils` Kubernetes CronJob Integration

Instead of running `bundleutils` from within a CI controller using a Pipeline, you can run it as a native Kubernetes resource.
This content demonstrates how to use a **Kubernetes CronJob** to execute `bundleutils`.

➡️ See: [`yaml/bu-audit-k8s-crontask.yaml`](yaml/bu-audit-k8s-crontask.yaml)

---

## 📁 Resources Overview

| Resource                                                             | Description                                    |
| -------------------------------------------------------------------- | ---------------------------------------------- |
| [`00-verify.sh`](00-verify.sh)                                       | Verifies prerequisites and environment         |
| [`01-createBundleUtilSecrets.sh`](01-createBundleUtilSecrets.sh)     | Creates required Kubernetes secrets            |
| [`02-applyCronJob.sh`](02-applyCronJob.sh)                           | Applies the Kubernetes CronJob manifest        |
| [`03-readJobLogs.sh`](03-readJobLogs.sh)                             | Retrieves logs from `CronJob → Job → Pod`      |
| [`04-runAll.sh`](04-runAll.sh)                                       | Runs all setup scripts sequentially            |
| [`yaml/bu-audit-k8s-crontask.yaml`](yaml/bu-audit-k8s-crontask.yaml) | CronJob definition that triggers `bundleutils` |
| [`yaml/bu-secrets.yaml.tpl`](yaml/bu-secrets.yaml.tpl)               | Template for Kubernetes secrets                |
| [`yaml/bu-test-pod-git-ssh.yaml`](yaml/bu-test-pod-git-ssh.yaml)     | Test pod for validating SSH Git operations     |
| [`k8s-git-ssh-secret/config.tpl`](k8s-git-ssh-secret/config.tpl)     | SSH config template for GitHub access          |

---

## ⚙️ Prerequisites

* A dedicated **GitHub repository**
* **SSH key-based authentication** for GitHub
  Refer to:

  * [https://docs.github.com/en/authentication/connecting-to-github-with-ssh](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
  * [https://stackoverflow.com/questions/3225862/multiple-github-accounts-ssh-config](https://stackoverflow.com/questions/3225862/multiple-github-accounts-ssh-config)
* **CloudBees CI Controller** running on Kubernetes with:

  * Admin user ID
  * Admin API token (`JENKINS_TOKEN`)
* Access to kubernetes
  * `export KUBECONFIG=....`
* Docker image used: 
  * [Dockerfile](../../Dockerfile)
  * ghcr.io/tsmp-falcon-platform/ci-bundle-utils
  * caternberg/bundleutils:dev3 (extension with ssh tools included) (might be removed soon)
* Required CLI tools:
  * `yq`
  * `kubectl`
  * `git`
  * `ssh`
  * `ssh-keyscan`

---

## 🛠 Setup Instructions

### 1. Prepare Secrets

Copy the secret template:

```bash
cp yaml/bu-secrets.yaml.tpl yaml/bu-secrets.yaml
```

Edit the copied file and replace placeholder variables with actual values:

```yaml
BUNDLEUTILS_USERNAME: '${BUNDLEUTILS_USERNAME}'
BUNDLEUTILS_PASSWORD: '${BUNDLEUTILS_PASSWORD}'
BUNDLEUTILS_JENKINS_URL: '${BUNDLEUTILS_JENKINS_URL}'
GIT_COMMITTER_NAME: '${GIT_COMMITTER_NAME}'
GIT_AUTHOR_NAME: '${GIT_AUTHOR_NAME}'
GIT_REPO: '${GIT_REPO}'
GIT_COMMITTER_EMAIL: '${GIT_COMMITTER_EMAIL}'
GIT_AUTHOR_EMAIL: '${GIT_AUTHOR_EMAIL}'
GIT_ACTION: 'push' #commit-only
```

### 2. Set Up SSH Credentials

Copy the template directory

```bash
cp -R k8s-git-ssh-secret.tpl k8s-git-ssh-secret
mv k8s-git-ssh-secret/config.tpl k8s-git-ssh-secret/config
```

Edit `k8s-git-ssh-secret/config` and adjust the ssh config file for GitHub:
* Replace `${GIT_COMMITTER_NAME}` with your gitHub username

```
Host github.com
User ${GIT_COMMITTER_NAME}
Hostname ssh.github.com
AddKeysToAgent yes
PreferredAuthentications publickey
IdentitiesOnly yes
IdentityFile /root/.ssh/id_rsa
Port 443
```

Create the `known_hosts` file:

```bash
ssh-keyscan -H github.com 2>/dev/null | grep -v '^#' > k8s-git-ssh-secret/known_hosts
```

Add your SSH private key:

```bash
cp <PATH_TO_YOUR_SSH_KEY> k8s-git-ssh-secret/id_rsa
chmod 600 k8s-git-ssh-secret/id_rsa
```

The final structure should look like:

```
k8s-git-ssh-secret/
├── config
├── id_rsa
└── known_hosts
```

### 3. Verify SSH Setup

```bash
./00-verify.sh
```

### 4. Create Kubernetes Secrets

```bash
./01-createBundleUtilSecrets.sh <YOUR_NAMESPACE>
```

---

## ✅ Run the CronJob

### 1. Apply the CronJob Resource

```bash
./02-applyCronJob.sh <YOUR_NAMESPACE>
```

### 2. Watch Logs

```bash
./03-readJobLogs.sh <YOUR_NAMESPACE>
```

Example output:

```
➜  k8s-intergation git:(main) ✗ ./03-readJobLogs.sh
📋 Verifying CronJob exists:
NAME                SCHEDULE      TIMEZONE   SUSPEND   ACTIVE   LAST SCHEDULE   AGE
bundleutils-audit   */2 * * * *   <none>     False     0        107s            60m
⏳ Waiting for the first job to be created...
✅ Found job: bundleutils-audit-XXX
Fri Jul 11 09:46:00 AM UTC 2025
BUNDLEUTILS_CACHE_DIR=/opt/bundleutils/.cache
BUNDLEUTILS_JENKINS_URL=https://XXXX.beescloud.com/
BUNDLEUTILS_PASSWORD=XXXXX
BUNDLEUTILS_RELEASE_HASH=
BUNDLEUTILS_RELEASE_VERSION=
BUNDLEUTILS_USERNAME=XXX
.........

7de39ff Fri Jul 4 16:12:33 2025 +0000 - Audit bundle cjoc (version: 2.492.1.3)
 cjoc/bundle.yaml  |  13 ++
 cjoc/items.yaml   | 482 ++++++++++++++++++++++++++++++++++++++++++++++++++++++
 cjoc/jenkins.yaml | 457 +++++++++++++++++++++++++++++++++++++++++++++++++++
 cjoc/plugins.yaml |  13 ++
 cjoc/rbac.yaml    | 116 +++++++++++++
 5 files changed, 1081 insertions(+)

43dc637 Fri Jul 4 16:12:08 2025 +0000 - first commit
 README.md | 1 +
 1 file changed, 1 insertion(+)
######################################
AUDITING: Summary of the audit so far:
######################################

AUDITING: team-a - Gitleaks check PASSED (staged files).
AUDITING: team-a - Git check. No changes to commit.
######################################
```

---

## 🧪 Optional: Test Git over SSH

```bash
kubectl apply -f yaml/bu-test-pod-git-ssh.yaml
```

This creates a simple pod that attempts a `git clone` using the configured SSH key and verifies connectivity.

---



