---
marp: true
title: "Example Bundles Drift Workflow"
author: "Steve Boardwell"
theme: default
paginate: true
class: lead
---
<!--
footer: <sup>1</sup> thanks [@teilo]()![alt text](https://a.slack-edge.com/production-standard-emoji-assets/14.0/apple-small/1f412.png)
-->

# 👷‍♂️ Meet Bob McBobface<sup>1<sup>

DevOps Engineer.
Shared Services team.
Maintainer of the entire **CloudBees CI** ecosystem.

_Sounds impressive, right?_

---
<!--
footer: ''
-->
# 😬 But There's a Catch

- Bob isn’t great with **YAML**
- And he works on **Windows**
- Aaaand he only uses the **Jenkins Web UI**

_No terminal. No CLI. Just clicky 🖱️ colourful 🌈 buttons 🔘_

---

# 😫 The Old Way Was Rough

- Create CasC bundles manually
- Write YAML by hand
- Push to Git
- Wait for sync to apply
- Debug when it breaks 😵‍💫

_One wrong indent, and everything explodes._

---

# 💡 Then Bob Had an Idea

> _"What if the server wrote the config for me?"_

---

# ✅ Enter CasC Export Mode

Bob enables **CasC Export** on his controllers.

Now he can:

1. Make changes in the UI
2. Click **“Export Configuration”**
3. Get a clean YAML bundle
4. Commit it to Git

_All without touching a terminal_ 👌

---

# 🧼 A Little Magic Helps

Helper scripts clean up:

- Secrets 🔒
- Superfluous entries 🧽
- Environment-specific values 🌐

The output = version-safe, deployment-ready config 💾

---

# 🛠️ Bob Still Doesn’t Like YAML

But now…
He doesn’t have to write it.
The system does the heavy lifting.

CloudBees CI meets him **where he is**.

---

# 🧰 Bob's new hero? `bundleutils`

A toolset for managing and transforming
**CloudBees CI CasC bundles** with ease.

---

# 📦 Code & Resources

- Code: [https://github.com/tsmp-falcon-platform/ci-bundle-utils](https://github.com/tsmp-falcon-platform/ci-bundle-utils)
- Container: [ghcr.io/tsmp-falcon-platform/ci-bundle-utils](https://github.com/tsmp-falcon-platform/ci-bundle-utils/pkgs/container/ci-bundle-utils)
- Walkthrough: [tsmp-falcon-platform/example-bundles-drift](https://github.com/tsmp-falcon-platform/example-bundles-drift)

---

# 🔁 Bob's Workflow

Three steps:

- `fetch`
- `transform`
- `test`

Simple. Scriptable. GitOps-friendly.

---

# 📥 Fetch

```mono
bundleutils fetch
...
...
INFO:root:Read YAML from url: https://tc3.acme.org/core-casc-export
INFO:root:Wrote target/fetched/tc3/bundle.yaml
INFO:root:Wrote target/fetched/tc3/jenkins.yaml
INFO:root:Wrote target/fetched/tc3/plugins.yaml
INFO:root:Wrote target/fetched/tc3/rbac.yaml
INFO:root:Wrote target/fetched/tc3/items.yaml
```

---

# 🔧 Transform

```mono
bundleutils transform
...
...
INFO:root:Transformation: processing transformations/remove-dynamic-stuff.yaml
INFO:root:Transformation: processing transformations/controllers-split.yaml
INFO:root:Transform: source target/fetched/tc3 to target bundles/tc3
INFO:root:Transform: applying JSON patches to bundles/tc3/jenkins.yaml
INFO:root:Transform: applying JSON patches to bundles/tc3/rbac.yaml
INFO:root:Transform: no credentials to replace
INFO:root:Transform: no substitutions to apply
INFO:root:Transform: applying item split to bundles/tc3/items.yaml
INFO:root:Checking item casc-local-audit (target: delete)
INFO:root:Checking for pattern test-.*
```

---

# 🧪 Test

```mono
bundleutils ci-setup
bundleutils ci-start
...
...
INFO:root:Waiting max 120 seconds for server to start...
INFO:root:Server started
...
...
bundleutils ci-validate
bundleutils ci-stop
```

---

# 💡 "Wait a minute..." Bob thought

> _"...besides sanitising, what else can I `transform`?"_

---

# ✂️ Remove Items

```mono
❯ cat tc1/bundle.yaml
apiVersion: '2'
id: tc1
description: Bundle for tc1
version: b68fda1e-d68c-5135-5146-bde9fce4358a
jcasc:
- jenkins.yaml
plugins:
- plugins.yaml
```

---

# ✂️ Custom YAML Splitting

```mono
❯ cat tc2/bundle.yaml
apiVersion: '2'
id: tc2
description: Bundle for tc2
version: 97f63a98-373b-e418-156d-7ffd36ea150c
jcasc:
- jenkins.yaml
- jenkins.casc.yaml
- jenkins.credentials.yaml
- jenkins.jenkins.clouds.yaml
- jenkins.security.yaml
- jenkins.support.yaml
- jenkins.views.yaml
plugins:
- plugins.yaml
items:
- items.yaml
```

---

# ✂️ Even Wildcard-Based Splitting 🫣

```mono
❯ cat tc3/bundle.yaml
apiVersion: '2'
id: tc3
description: Bundle for tc3
version: e7fdfc43-2a28-1a1f-3c86-728208581b3e
jcasc:
- jenkins.appearance.yaml
- jenkins.beekeeper.yaml
- jenkins.globalCredentialsConfiguration.yaml
- jenkins.jenkins.authorizationStrategy.yaml
- jenkins.jenkins.clouds.yaml
- jenkins.jenkins.crumbIssuer.yaml
- jenkins.jenkins.disableRememberMe.yaml
- jenkins.jenkins.markupFormatter.yaml
- jenkins.jenkins.mode.yaml
- jenkins.jenkins.myViewsTabBar.yaml
- jenkins.jenkins.noUsageStatistics.yaml
- jenkins.jenkins.nodeMonitors.yaml
- jenkins.jenkins.numExecutors.yaml
- jenkins.jenkins.primaryView.yaml
- jenkins.jenkins.projectNamingStrategy.yaml
- jenkins.jenkins.quietPeriod.yaml
- jenkins.jenkins.scmCheckoutRetryCount.yaml
- jenkins.jenkins.securityRealm.yaml
- jenkins.jenkins.views.yaml
- jenkins.jenkins.viewsTabBar.yaml
- jenkins.jenkins.yaml
- jenkins.security.yaml
- jenkins.support.yaml
- jenkins.tool.yaml
- jenkins.unclassified.buildDiscarders.yaml
- jenkins.unclassified.bundleUpdateTiming.yaml
- jenkins.unclassified.cascItemsConfiguration.yaml
- jenkins.unclassified.cloudBeesSCMReporting.yaml
- jenkins.unclassified.cloudbeesPipelineExplorer.yaml
- jenkins.unclassified.experimentalPlugins.yaml
- jenkins.unclassified.fingerprints.yaml
- jenkins.unclassified.gitHubConfiguration.yaml
- jenkins.unclassified.gitHubPluginConfig.yaml
- jenkins.unclassified.hibernationConfiguration.yaml
- jenkins.unclassified.junitTestResultStorage.yaml
- jenkins.unclassified.location.yaml
- jenkins.unclassified.mailer.yaml
- jenkins.unclassified.pollSCM.yaml
- jenkins.unclassified.scmGit.yaml
- jenkins.unclassified.usageStatisticsCloudBees.yaml
- jenkins.unclassified.validationVisualization.yaml
- jenkins.unclassified.yaml
plugins:
- plugins.yaml
items:
- items.casc-local-audit.yaml
- items.casc-local-bootstrap.yaml
- items.casc-local-direct.yaml
- items.casc-local-drift.yaml
- items.mb1.yaml
- items.mb2.yaml
```

---

# 🧩 Profiles & Configuration

> _“Look, Ma! No args!”_

Bob uses the **`bundle-profiles.yaml`**
to drive repeatable, preconfigured workflows.

---

# 🧩 Introducing `bundle-profiles.yaml`

```yaml
# yq 'explode(.)' bundle-profiles.yaml
bundles:
  tc1:
    BUNDLEUTILS_TRANSFORM_CONFIGS: >-
      transformations/remove-dynamic-stuff.yaml
      transformations/controllers-split.yaml
    BUNDLEUTILS_CI_TYPE: mm
    BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE: true
    BUNDLEUTILS_CATALOG_WARNINGS_STRATEGY: COMMENT
    BUNDLEUTILS_CI_JAVA_OPTS: >-
      -Djenkins.security.SystemReadPermission=true
      -Djenkins.security.ManagePermission=true
      -Dhudson.security.ExtendedReadPermission=true
    BUNDLEUTILS_JENKINS_URL: https://tc1.acme.org/
    BUNDLEUTILS_CI_VERSION: 2.492.1.3
```

---

# 🧩 Auto Envs (based on the CWD)

```mono
❯ cd bundles/controller-bundles/tc1

❯ bundleutils config
INFO:root:AUTOSET env: BUNDLEUTILS_FETCH_TARGET_DIR=target/fetched/tc1
INFO:root:AUTOSET env: BUNDLEUTILS_TRANSFORM_SOURCE_DIR=target/fetched/tc1
...
...
INFO:root:Evaluated configuration:
BUNDLEUTILS_TRANSFORM_SOURCE_DIR=target/fetched/tc1
BUNDLEUTILS_TRANSFORM_TARGET_DIR=bundles/controller-bundles/tc1
BUNDLEUTILS_VALIDATE_SOURCE_DIR=bundles/controller-bundles/tc1
...
...
```

---

# 😢 Bob fetched a bundle using `--args`

```mono
❯ bundleutils fetch \
  --url https://tc1.acme.org \
  --username bob \
  --password 's3cr3t!' \
  --cap \
  --target-dir target/fetched/tc1
```

---

# 😭 Then he tried with `envVars`

```mono
❯ BUNDLEUTILS_JENKINS_URL=https://tc1.acme.org \
BUNDLEUTILS_USERNAME=bob \
BUNDLEUTILS_PASSWORD='s3cr3t!' \
BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE=True \
BUNDLEUTILS_FETCH_TARGET_DIR=target/fetched/tc1 \
bundleutils fetch
```

---

# 🫠 And finally with `bundle-profiles.yaml`

```mono
❯ bundleutils fetch
```

---

# 🧪 Demo Time

🎬 Use Cases:

- Onboarding
- Drift Detection
- Managing Upgrades
- Auditing

---

# 🙌 Thanks, Bob

> Sometimes the best DevOps is knowing your limits —
> and building around them.

---
![bg height:15cm right:37%](image.png)

# 🎉 Be Like Bob

- Empower your teams
- Reduce YAML anxiety
- Use CasC Export as a safe route to GitOps

_Configuration as Code doesn’t have to be complicated._

---

# 🙏 Call for Support 🙏

- Contributions
- Real-world Testing (CasC Export)
- Documentation Cleanup
  - Examples
  - Workflows

---
![bg height:11cm right:52%](magician.png)

# 🎬 Bob the Magician

(Since we have time...)

What are...

- Partial bundles
- Merged bundles

---

# ✅ Summary & Q&A

- `bundleutils` simplifies bundle lifecycle
- Fetch, transform, test — without fear
- GitOps ready, YAML optional™

💬 **Questions?**
