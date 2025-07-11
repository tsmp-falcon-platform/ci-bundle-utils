# 📦 `bundleutils` Kubernetes CronJob Integration

Instead of running `bundleutils` from within a CI controller using a Pipeline, you can run it as a native Kubernetes resource.
This content demonstrates how to use a **Kubernetes CronJob** to execute `bundleutils`.

➡️ See: [cronjob.yaml](helm/bundleutils-chart/templates/cronjob.yaml)

---

## 📁 Resources Overview

| Resource                                                           | Description                                        |
|--------------------------------------------------------------------|----------------------------------------------------|
| [`00-verify.sh`](00-verify.sh)                                     | Verifies prerequisites and environment             |
| [`01-readJobLogs.sh`](01-readJobLogs.sh)                           | Retrieves logs from `CronJob → Job → Pod`          |
| [`Helm Chart bundleutils`](helm/bundleutils-chart/README.md)       | Helm Chart to install the `bundleutils` as CronJob |
| [`yaml/bu-test-pod-git-ssh.yaml`](yaml/bu-test-pod-git-ssh.yaml)   | Test pod for validating SSH Git connection         |

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
* Required CLI tools:
  * `yq`
  * `kubectl`
  * `git`
  * `ssh`
  * `ssh-keyscan`
  * `helm`

---

## 🛠 Setup Instructions

### 1. Prepare SSH for GitHub

Create the `known_hosts` file:

```bash
mkdir -p k8s-git-ssh-secret
ssh-keyscan -p 443 -H ssh.github.com | sed 's/^#\s//g ' | tee  k8s-git-ssh-secret/known_hosts
ssh-keyscan -H github.com | sed 's/^#\s//g ' | tee -a  k8s-git-ssh-secret/known_hosts

```

Copy your SSH private key:

```bash
cp <PATH_TO_YOUR_SSH_KEY> k8s-git-ssh-secret/privateKey
chmod 600 k8s-git-ssh-secret/privateKey
```

Next, add your ssh config, similar to this below
Replace <YOUR_GIT_HUB_USER_ID> with your GitHub account id 

GitHub
```config
cat <<EOF> k8s-git-ssh-secret/known_hosts
    Host github.com
    User <YOUR_GIT_HUB_USER_ID>
    Hostname ssh.github.com
    AddKeysToAgent yes
    PreferredAuthentications publickey
    IdentitiesOnly yes
    IdentityFile /root/.ssh/privateKey
    Port 443
EOF
```

BitBucket (Cloud, BB Server not tested yet)

```config
cat <<EOF> k8s-git-ssh-secret/known_hosts
    Host bitbucket.org
    HostName bitbucket.org
    User <YOUR_BB_USER>
    AddKeysToAgent yes
    PreferredAuthentications publickey
    IdentitiesOnly yes
    IdentityFile ~/.ssh/privateKey
EOF
```


The final structure should look like:

```
k8s-git-ssh-secret/
├── config
├── privateKey
└── known_hosts
```

You can verify if the known_hosts file is valid like this:

```bash
ssh -o UserKnownHostsFile=$(pwd)/k8s-git-ssh-secret/known_hosts -i $(pwd)/k8s-git-ssh-secret/privateKey git@github.com
```


### 2. Verify SSH Setup

```bash
./00-verify.sh
```

### 3. Install

See [README.md](helm/bundleutils-chart/README.md)

### 4. Watch Logs

It takes 1 or 2 minutes to het the logs. If the first try is not successfully, try again until the CronJobs triggered the first time a Job 

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



