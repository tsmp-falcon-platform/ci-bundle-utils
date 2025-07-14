# 🛠️ Verify Deployment

To perform a dry-run of the Helm release without applying it to the cluster:

```bash
helm upgrade --install bundleutils-release -f myvalues.yaml ./bundleutils-chart  --dry-run
```

---

# 🚀 Chart Installation

> **Important:** Ensure the following SSH-related files are present in your working directory:
>
> * `privateKey` – your **private SSH key**
> * `config` – your **SSH config file**
> * `known_hosts` – your **SSH known hosts file**


## Install using a values file

```bash
helm upgrade --install bundleutils-release -f myvalues.yaml ./bundleutils-chart 
```

NOTE: 
* See [01-cloneBranchAuditPush.sh](01-cloneBranchAuditPush.sh) This is the audit script executed in the CronJob

```bash
#!/bin/bash

NAMESPACE=${1:-"cjoc1"}

# Set SSH file paths
SSH_SECRETS_PATH="/path/to/ssh/secrets"
SSH_KEY="$SSH_SECRETS_PATH/privateKey"
SSH_KNOWN_HOSTS="$SSH_SECRETS_PATH/known_hosts"
SSH_CONFIG="$SSH_SECRETS_PATH/config"

# Use your local custom audit script
#BUNDLEUTILS_ACTION="./yourauditscript.sh"
BUNDLEUTILS_ACTION="./cloneBranchAuditPush.sh"

helm upgrade --install bundleutils-release -f myvalues.yaml ./bundleutils-chart \
  --set-file sshSecret.privateKey="${SSH_KEY}" \
  --set-file sshSecret.config="${SSH_CONFIG}" \
  --set-file sshSecret.known_hosts="${SSH_KNOWN_HOSTS}" \
  --set-file bundleutilsAction.perform="${BUNDLEUTILS_ACTION}" \
  -n "$NAMESPACE"
```

---


---

## Install using CLI parameters

```bash
# Set paths to your SSH files
SSH_KEY="./privateKey"
SSH_KNOWN_HOSTS="./known_hosts"
SSH_CONFIG="./config"

# Install the Helm chart
helm upgrade --install bundleutils-release ./bundleutils-chart  \
  --set image.repository="caternberg/bundleutils" \
  --set image.tag="dev3" \
  --set image.pullPolicy="IfNotPresent" \
  --set cronjob.enabled=true \
  --set cronjob.schedule="*/2 * * * *" \
  --set cronjob.restartPolicy="OnFailure" \
  --set testPod.enabled=true \
  --set testPod.restartPolicy="Never" \
  --set sshSecret.name="secret-ssh-auth" \
  --set-file sshSecret.privateKey="${SSH_KEY}" \
  --set-file sshSecret.config="${SSH_CONFIG}" \
  --set-file sshSecret.known_hosts="${SSH_KNOWN_HOSTS}" \
  --set bundleUtilsSecrets.name="bundle-utils-secrets" \
  --set bundleUtilsSecrets.data.GIT_COMMITTER_NAME="Your Name" \
  --set bundleUtilsSecrets.data.GIT_AUTHOR_NAME="Your Name" \
  --set bundleUtilsSecrets.data.GIT_REPO="git@github.com:org/repo.git" \
  --set bundleUtilsSecrets.data.GIT_COMMITTER_EMAIL="you@example.com" \
  --set bundleUtilsSecrets.data.GIT_AUTHOR_EMAIL="you@example.com" \
  --set bundleUtilsSecrets.data.GIT_ACTION="push" \
  --set bundleUtilsSecrets.data.BUNDLEUTILS_USERNAME="change-me" \
  --set bundleUtilsSecrets.data.BUNDLEUTILS_PASSWORD="change-me" \
  --set bundleUtilsSecrets.data.BUNDLEUTILS_JENKINS_URL="http://jenkins.example.com" \  
  --set bundleUtilsSecrets.data.JENKINS_URL="http://jenkins.example.com" \
  --set-file bundleutilsAction.perform="/opt/bundleutils/work/examples/tutorials/auditing/audit.sh" \
  -n "$NAMESPACE"
```

---

## Hybrid (values file + CLI overrides)

```bash
# Set paths to your SSH files
SSH_KEY="./privateKey"
SSH_KNOWN_HOSTS="./known_hosts"
SSH_CONFIG="./config"

helm upgrade --install bundleutils-release -f myvalues.yaml ./bundleutils-chart  \
  --set-file sshSecret.privateKey="${SSH_KEY}" \
  --set-file sshSecret.config="${SSH_CONFIG}" \
  --set-file sshSecret.known_hosts="${SSH_KNOWN_HOSTS}" \
  --set bundleutilsAction.perform="/opt/bundleutils/work/examples/tutorials/auditing/audit.sh" \
  -n "$NAMESPACE"
```

---

## Use the built-in audit script

```bash
#!/bin/bash

NAMESPACE=${1:-"cjoc1"}

# Set SSH file paths
SSH_SECRETS_PATH="/path/to/ssh/secrets"
SSH_KEY="$SSH_SECRETS_PATH/privateKey"
SSH_KNOWN_HOSTS="$SSH_SECRETS_PATH/known_hosts"
SSH_CONFIG="$SSH_SECRETS_PATH/config"

# Use the default built-in audit script
BUNDLEUTILS_ACTION="/opt/bundleutils/work/examples/tutorials/auditing/audit.sh"

helm upgrade --install bundleutils-release -f myvalues.yaml  ./bundleutils-chart \
  --set-file sshSecret.privateKey="${SSH_KEY}" \
  --set-file sshSecret.config="${SSH_CONFIG}" \
  --set-file sshSecret.known_hosts="${SSH_KNOWN_HOSTS}" \
  --set bundleutilsAction.perform="${BUNDLEUTILS_ACTION}" \
  -n "$NAMESPACE"
```

---


## Parameters

Note:
* `bundleutil` specific parameters can be added to `bundleUtilsSecrets.data` (values.yaml) according to your needs
* This setup focus only on the mandatory parameters for `bundleutils audit`

| **Helm Values Path**                                              | **Required** | **Type / Example**                                  | **Default / Sample**                                      | **Description**                                   |
|-------------------------------------------------------------------|--------------|-----------------------------------------------------|-----------------------------------------------------------|---------------------------------------------------|
| `image.repository`                                                |              | `string`                                            | `caternberg/bundleutils`                                 | Container image repository                        |
| `image.tag`                                                       |              | `string`                                            | `dev3`                                                    | Container image tag                               |
| `image.pullPolicy`                                                |              | `Always \| IfNotPresent \| Never`                   | `IfNotPresent`                                            | Kubernetes image pull policy                     |
| `cronjob.enabled`                                                 |              | `bool`                                              | `true`                                                    | Enable/disable the CronJob                       |
| `cronjob.schedule`                                                |              | Cron expression (`string`)                          | `*/2 * * * *`                                             | Cron schedule (every 2 min in sample)            |
| `cronjob.restartPolicy`                                           |              | `OnFailure \| Never`                                | `OnFailure`                                               | Pod restart policy for the CronJob               |
| `testPod.enabled`                                                 |              | `bool`                                              | `false`                                                   | Deploy auxiliary test pod                        |
| `testPod.restartPolicy`                                           |              | `Never`                                             | `Never`                                                   | Restart policy for the test pod                  |
| `sshSecret.name`                                                  |              | `string`                                            | `secret-ssh-auth`                                         | Name of the SSH `Secret`                         |
| `sshSecret.privateKey`                                            | X            | *multi‑line string*                                 | `REPLACE_WITH_SSH_PRIVATE_KEY`                           | SSH private key (use `--set-file`)               |
| `sshSecret.config`                                                | X            | *multi‑line string*                                 | `REPLACE_WITH_SSH_CONFIG`                                | Custom `ssh_config` content                      |
| `sshSecret.known_hosts`                                           | X            | *multi‑line string*                                 | `REPLACE_WITH_SSH_KNOWN_HOSTS`                           | Pre‑approved `known_hosts` entries               |
| `bundleutilsAction.perform`                                       | X            | Path or script (`string`)                           | `/opt/bundleutils/work/examples/tutorials/auditing/audit.sh` | Command executed inside the CronJob              |
| `bundleUtilsSecrets.name`                                         |              | `string`                                            | `bundle-utils-secrets`                                   | Name of env `Secret`                             |
| `bundleUtilsSecrets.data.GIT_COMMITTER_NAME` / `GIT_AUTHOR_NAME`  | X            | `string`                                            | `Your Name`                                               | Git committer / author names                     |
| `bundleUtilsSecrets.data.GIT_REPO`                                | X            | SSH URL (`string`)                                  | `git@github.com:org/repo.git`                            | Target Git repository                            |
| `bundleUtilsSecrets.data.GIT_COMMITTER_EMAIL` / `GIT_AUTHOR_EMAIL`| X            | `string`                                            | `you@example.com`                                        | Git committer / author e‑mails                   |
| `bundleUtilsSecrets.data.GIT_ACTION`                              |              | `push \| commit-only \| ...`                        | `push`                                                    | Git operation executed by the job                |
| `bundleUtilsSecrets.data.BUNDLEUTILS_USERNAME`                    | X            | `string`                                            | `change-me`                                               | CloudBees CI admin user                          |
| `bundleUtilsSecrets.data.BUNDLEUTILS_PASSWORD`                    | X            | `string`                                            | `change-me`                                               | CloudBees CI admin token                         |
| `bundleUtilsSecrets.data.BUNDLEUTILS_JENKINS_URL` / `JENKINS_URL` | X            | URL (`string`)                                      | `http://jenkins.example.com`                             | Jenkins/OC base URL                              |
| `bundleUtilsSecrets.data.BUNDLEUTILS_GBL_LOG_LEVEL`               |              | `INFO \| DEBUG \| ...`                              | `INFO`                                                    | Global log level for bundleutils                 |

> **Tip**  
> Use `--set-file` for any multi‑line values (SSH keys, configs, scripts) to keep line breaks intact during Helm rendering.



---

## 🛉 Uninstall

To remove the deployed Helm release:

```bash
helm uninstall bundleutils-release
```

---

## 🔍 Render Templates (Dry Render)

To render and inspect the final manifest output, including the `bundleutilsAction.perform` script:

```bash
helm template ./bundleutils-chart \
  -f myvalues.yaml  \
  --set-file bundleutilsAction.perform=./gitHubPrepare.sh \
  --debug
```

---

## ✅ Notes

* Use `--set-file` for multi-line values (e.g., private keys, SSH config, scripts).
* `bundleutils-release` is the default release name—feel free to customize it.
* Ensure all referenced files exist and are readable.
* The `--upgrade --install` combination guarantees idempotent Helm behavior.
