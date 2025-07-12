
---

## 🛠️ Verify Deployment

To verify the Helm release without applying it to the cluster:

```bash
helm upgrade --install bundleutils-release -f myvalues.yaml ./ --dry-run
```

---

## 🚀 Install the Chart

> **Note:** Prepare the following SSH-related files in your working directory:
>
> * `privateKey` – your **private SSH key**
> * `ssh_config` – your **SSH config** file
> * `known_hosts` – your **SSH known hosts** file

### Option 1: Install using a values file

```bash
helm upgrade --install bundleutils-release -f myvalues.yaml ./
```

### Option 2: Install using command-line parameters

```bash
# Export SSH-related file,path as environment variables 
# Adjust the path to the files if required
SSH_KEY="./privateKey"
SSH_KNOWN_HOSTS="./known_hosts"
SSH_CONFIG="./config"

# Install the chart from local directory
helm upgrade --install bundleutils-release ./ \
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
  --set bundleUtilsSecrets.data.BUNDLEUTILS_ACTION="/opt/bundleutils/work/examples/tutorials/auditing/audit.sh"
```

### Option 3: Mixed

```bash
# Export SSH-related file,path as environment variables 
# Adjust the path to the files if required
SSH_KEY="./privateKey"
SSH_KNOWN_HOSTS="./known_hosts"
SSH_CONFIG="./config"
helm upgrade --install bundleutils-release -f myvalues.yaml ./ \
  --set-file sshSecret.privateKey="${SSH_KEY}" \
  --set-file sshSecret.config="${SSH_CONFIG}" \
  --set-file sshSecret.known_hosts="${SSH_KNOWN_HOSTS}" \
  --set bundleutilsAction.perfom="/opt/bundleutils/work/examples/tutorials/auditing/audit.sh"
```

* Example reference the build in audit.sh script

```bash
#! /bin/bash

NAMESPACE=${1:-"cjoc1"}
# Export SSH-related file,path as environment variables
# Adjust the path to the files if required
SSH_SECRETS_PATH="YOU_PATH_TO_SSH_SECRETS"
SSH_KEY="$SSH_SECRETS_PATH/privateKey"
SSH_KNOWN_HOSTS="$SSH_SECRETS_PATH/known_hosts"
SSH_CONFIG="$SSH_SECRETS_PATH/config"
# Refer to the audit script inside the bundleutis container. This script is the deafult bakes in
BUNDLEUTILS_ACTION="/opt/bundleutils/work/examples/tutorials/auditing/audit.sh"

helm upgrade --install bundleutils-release -f my-values-gke-dev.yaml ./bundleutils-chart \
  --set-file sshSecret.privateKey="${SSH_KEY}" \
  --set-file sshSecret.config="${SSH_CONFIG}" \
  --set-file sshSecret.known_hosts="${SSH_KNOWN_HOSTS}" \
  --set bundleutilsAction.perfom="/opt/bundleutils/work/examples/tutorials/auditing/audit.sh"
  -n $NAMESPACE 
```

* Example bring your own audit script

```bash
#! /bin/bash

NAMESPACE=${1:-"cjoc1"}
# Export SSH-related file,path as environment variables
# Adjust the path to the files if required
SSH_SECRETS_PATH="YOU_PATH_TO_SSH_SECRETS"
SSH_KEY="$SSH_SECRETS_PATH/privateKey"
SSH_KNOWN_HOSTS="$SSH_SECRETS_PATH/known_hosts"
SSH_CONFIG="$SSH_SECRETS_PATH/config"
# Refer to the audit script local on youer mashine where you run helm from
BUNDLEUTILS_ACTION="./yourauditscript.sh"
helm upgrade --install bundleutils-release -f my-values-gke-dev.yaml ./bundleutils-chart \
  --set-file sshSecret.privateKey="${SSH_KEY}" \
  --set-file sshSecret.config="${SSH_CONFIG}" \
  --set-file sshSecret.known_hosts="${SSH_KNOWN_HOSTS}" \
  --set-file bundleutilsAction.perfom="${BUNDLEUTILS_ACTION}" 
  -n $NAMESPACE 
```

---

### Uninstall

```bash
 helm uninstall bundleutils-release
```

## Dry render

Example on how to render the bundleutilsAction.perform key

```bash
 helm template ./bundleutils-chart \
  -f my-values.yaml \
  --set-file bundleutilsAction.perform=./gitHubPrepare.sh \
  --debug
```


### ✅ Notes

* Use `--set-file` for multi-line values such as private keys, SSH configs, and scripts.
* `bundleutils-release` is the name of the Helm release. You can change it as needed.
* Ensure the specified files exist and are readable.
* `--upgrade --install` ensures idempotent behavior—installing if not present, upgrading if already deployed.

