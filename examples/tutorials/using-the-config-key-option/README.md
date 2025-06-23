# 5-Minute Challenge: `--config-key`

Welcome to this quick hands-on challenge! In just five minutes, you'll explore how the `-K / --config-key` option works in the `bundleutils <fetch|transform|audit>` commands and how environment variables or CLI flags affect its output.

---

## 🎯 Goal

Learn how to query evaluated configuration keys using `-K / --config-key` and verify how command-line arguments and environment variables impact these values.

---

## 🔧 Prerequisites

- `bundleutils` is installed and in your `$PATH`.

---

## ✅ 1. View all evaluated configuration keys

Run:

```sh
bundleutils fetch --config-key
```

🧾 **Example Output:**

```sh
INFO:root:Evaluated configuration:
BUNDLEUTILS_BUNDLES_BASE=/home/user/ci-bundle-utils
BUNDLEUTILS_BUNDLE_NAME=default-controller
BUNDLEUTILS_CI_INSTANCE_NAME=default-controller
BUNDLEUTILS_CI_TYPE=mm
BUNDLEUTILS_CI_VERSION=2.479.3.1
BUNDLEUTILS_FETCH_IGNORE_ITEMS=true
...
BUNDLEUTILS_USERNAME=ci-admin
```

> ✅ Lists all active config keys resolved from env vars, CLI, or defaults.

---

## ✅ 2. Query a single key using `--config-key <ENV_VAR>`

Run:

```sh
bundleutils fetch --config-key BUNDLEUTILS_FETCH_IGNORE_ITEMS
```

🧾 **Output:**

```sh
true
```

> ✅ Confirms the current value for `BUNDLEUTILS_FETCH_IGNORE_ITEMS`.

---

### ✅ 3. Environment variable overrides

Run:

```sh
BUNDLEUTILS_FETCH_IGNORE_ITEMS=false bundleutils fetch --config-key BUNDLEUTILS_FETCH_IGNORE_ITEMS
```

🧾 **Output:**

```sh
false
```

> 🔁 Shows the value reflects the overridden environment variable.

---

### ✅ 4. CLI overrides

Run:

```sh
bundleutils fetch --no-ignore-items --config-key BUNDLEUTILS_FETCH_IGNORE_ITEMS
```

🧾 **Output:**

```sh
false
```

Then try:

```sh
bundleutils fetch --ignore-items --config-key BUNDLEUTILS_FETCH_IGNORE_ITEMS
```

🧾 **Output:**

```sh
true
```

> ⚠️ CLI flags **take precedence** over env vars — use this to test overrides.

---

### ✅ 5. Try version appending logic

Run:

```sh
bundleutils --append-version fetch --config-key BUNDLEUTILS_BUNDLE_NAME
```

🧾 **Output:**

```sh
default-controller-2.479.3.1
```

Now try:

```sh
bundleutils --no-append-version fetch --config-key BUNDLEUTILS_BUNDLE_NAME
```

🧾 **Output:**

```sh
default-controller
```

> 🧩 Shows how flags like `--append-version` influence dynamic values like bundle names.

---

## ✅ Summary

The `--config-key` flag is a powerful tool to:

- Inspect **effective config values**
- Validate overrides from env vars or flags
- Debug why certain behaviors occur

Use it to trace and verify configuration before running expensive or destructive operations.
