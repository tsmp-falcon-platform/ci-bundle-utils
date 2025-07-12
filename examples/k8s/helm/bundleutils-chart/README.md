## 🛠️ Verify Deployment

To perform a dry-run of the Helm release without applying it to the cluster:

```bash
helm upgrade --install bundleutils-release -f myvalues.yaml ./ --dry-run
```

---

## 🚀 Chart Installation

> **Important:** Ensure the following SSH-related files are present in your working directory:
>
> * `privateKey` – your **private SSH key**
> * `config` – your **SSH config file**
> * `known_hosts` – your **SSH known hosts file**

### Option 1: Install using a values file

```bash
helm upgrade --install bundleutils-release -f myvalues.yaml ./
```

---

### Option 2: Install using CLI parameters

```bash
# Set paths to your SSH files
SSH_KEY="./privateKey"
SSH_KNOWN_HOSTS="./known_hosts"
SSH_CONFIG="./config"

# Install the Helm chart
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

---

### Option 3: Hybrid (values file + CLI overrides)

```bash
# Set paths to your SSH files
SSH_KEY="./privateKey"
SSH_KNOWN_HOSTS="./known_hosts"
SSH_CONFIG="./config"

helm upgrade --install bundleutils-release -f myvalues.yaml ./ \
  --set-file sshSecret.privateKey="${SSH_KEY}" \
  --set-file sshSecret.config="${SSH_CONFIG}" \
  --set-file sshSecret.known_hosts="${SSH_KNOWN_HOSTS}" \
  --set bundleutilsAction.perform="/opt/bundleutils/work/examples/tutorials/auditing/audit.sh"
```

---

### Example 1: Use the built-in audit script

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

helm upgrade --install bundleutils-release -f my-values-gke-dev.yaml ./bundleutils-chart \
  --set-file sshSecret.privateKey="${SSH_KEY}" \
  --set-file sshSecret.config="${SSH_CONFIG}" \
  --set-file sshSecret.known_hosts="${SSH_KNOWN_HOSTS}" \
  --set bundleutilsAction.perform="${BUNDLEUTILS_ACTION}" \
  -n "$NAMESPACE"
```

---

### Example 2: Use your custom audit script

```bash
#!/bin/bash

NAMESPACE=${1:-"cjoc1"}

# Set SSH file paths
SSH_SECRETS_PATH="/path/to/ssh/secrets"
SSH_KEY="$SSH_SECRETS_PATH/privateKey"
SSH_KNOWN_HOSTS="$SSH_SECRETS_PATH/known_hosts"
SSH_CONFIG="$SSH_SECRETS_PATH/config"

# Use your local custom audit script
BUNDLEUTILS_ACTION="./yourauditscript.sh"

helm upgrade --install bundleutils-release -f my-values-gke-dev.yaml ./bundleutils-chart \
  --set-file sshSecret.privateKey="${SSH_KEY}" \
  --set-file sshSecret.config="${SSH_CONFIG}" \
  --set-file sshSecret.known_hosts="${SSH_KNOWN_HOSTS}" \
  --set-file bundleutilsAction.perform="${BUNDLEUTILS_ACTION}" \
  -n "$NAMESPACE"
```

---

### 🛉 Uninstall

To remove the deployed Helm release:

```bash
helm uninstall bundleutils-release
```

---

### 🔍 Render Templates (Dry Render)

To render and inspect the final manifest output, including the `bundleutilsAction.perform` script:

```bash
helm template ./bundleutils-chart \
  -f my-values.yaml \
  --set-file bundleutilsAction.perform=./gitHubPrepare.sh \
  --debug
```

---

### ✅ Notes

* Use `--set-file` for multi-line values (e.g., private keys, SSH config, scripts).
* `bundleutils-release` is the default release name—feel free to customize it.
* Ensure all referenced files exist and are readable.
* The `--upgrade --install` combination guarantees idempotent Helm behavior.
