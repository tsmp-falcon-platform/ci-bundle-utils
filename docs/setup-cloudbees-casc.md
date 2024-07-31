# Running Remotely on the Operations Center

We will need a number of components to enable running pods on the operations center.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Through the UI?](#through-the-ui)
- [Through CasC](#through-casc)
- [Kubernetes Cloud and Pod Template](#kubernetes-cloud-and-pod-template)
- [Test Job](#test-job)
- [Management Jobs](#management-jobs)
  - [Credentials](#credentials)
  - [Job Specifications](#job-specifications)
  - [Custom View](#custom-view)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Through the UI?

All the objects below can be created through the UI. e.g. In the operations center, navigate to Manage Jenkins -> Nodes and Clouds.

- Create a new cloud, e.g. `bundleutils-cloud` and fill in any details according to the configuration in the link above, etc.
- Credentials can be added as appropriate.
- Jobs can be created according to the spec below.

## Through CasC

An example cloud + pod template configuration can be found below.

## Kubernetes Cloud and Pod Template

A cloud needs to be configured on the operations center, along with a pod template to run our build container.

A full example of this configuration can be found in the provided [../template-bundles/oc-bundles/oc-bundle](../template-bundles/oc-bundles/oc-bundle)

**NOTE: Have a cloud already?** You can just add the pod template.

**NOTE (PVC):** If you have not set up a shared volume, remove the sections commented  `# TODO...`

```yaml
jenkins:
  clouds:
  - kubernetes:
      containerCap: 10
      containerCapStr: '10'
      name: bundleutils-cloud
      templates:
      - id: 75582751-5e50-403e-8c0c-961b99fd33a0
        label: bundleutils
        name: bundleutils
        serviceAccount: ''
        showRawYaml: false
        yaml: |-
          apiVersion: v1
          kind: Pod
          metadata:
            name: jenkins-agent-pod
          spec:
            containers:
            - name: jnlp
              image: ghcr.io/tsmp-falcon-platform/ci-bundle-utils:latest
              command: ["/usr/share/jenkins/jenkins-agent"]
              volumeMounts:
              - name: pseudo-jnlp
                mountPath: /usr/share/jenkins
                # TODO - remove if not using the bundleutils-cache-pvc
              - name: bundleutils-cache
                mountPath: /opt/bundleutils/.cache
            initContainers:
            - name: copy-agent-stuff
              image: cloudbees/cloudbees-core-agent:2.452.3.2
              command: ["sh", "-c", "cp /usr/share/jenkins/agent.jar /usr/local/bin/jenkins-agent  /pseudo-jnlp/"]
              volumeMounts:
              - name: pseudo-jnlp
                mountPath: /pseudo-jnlp
            volumes:
            - name: pseudo-jnlp
              emptyDir: {}
              # TODO - remove if not using the bundleutils-cache-pvc
            - name: bundleutils-cache
              persistentVolumeClaim:
                  claimName: bundleutils-cache-pvc
        yamlMergeStrategy: override
        yamls:
        - |-
          apiVersion: v1
          kind: Pod
          metadata:
            name: jenkins-agent-pod
          spec:
            containers:
            - name: jnlp
              image: ghcr.io/tsmp-falcon-platform/ci-bundle-utils:latest
              command: ["/usr/share/jenkins/jenkins-agent"]
              volumeMounts:
              - name: pseudo-jnlp
                mountPath: /usr/share/jenkins
                # TODO - remove if not using the bundleutils-cache-pvc
              - name: bundleutils-cache
                mountPath: /opt/bundleutils/.cache
            initContainers:
            - name: copy-agent-stuff
              image: cloudbees/cloudbees-core-agent:2.452.3.2
              command: ["sh", "-c", "cp /usr/share/jenkins/agent.jar /usr/local/bin/jenkins-agent  /pseudo-jnlp/"]
              volumeMounts:
              - name: pseudo-jnlp
                mountPath: /pseudo-jnlp
            volumes:
            - name: pseudo-jnlp
              emptyDir: {}
              # TODO - remove if not using the bundleutils-cache-pvc
            - name: bundleutils-cache
              persistentVolumeClaim:
                  claimName: bundleutils-cache-pvc
      webSocket: true
```

## Test Job

- create a freestyle job on the operations center
- in `Restrict where this job can run` type `bundleutils`
- add a step to run a shell command, enter `bundleutils --help`
- run the job

A CasC item example would be:

```yaml
removeStrategy:
  rbac: SYNC
  items: NONE
items:
- kind: freeStyle
  name: bundleutils-test-job
  blockBuildWhenDownstreamBuilding: false
  blockBuildWhenUpstreamBuilding: false
  builders:
  - shell:
      command: |
        bundleutils --help
  concurrentBuild: false
  description: ''
  disabled: false
  displayName: bundleutils-test-job
  label: bundleutils
  publishersList:
  - gitHubCommitStatusSetter:
      commitShaSource:
        buildDataRevisionShaSource: {}
      statusResultSource:
        defaultStatusResultSource: {}
      contextSource:
        defaultCommitContextSource: {}
      reposSource:
        anyDefinedRepositorySource: {}
      statusBackrefSource:
        buildRefBackrefSource: {}
```

If the job succeeds, congratulations! :partying_face: You can move on to the next section of adding management jobs.

## Management Jobs

Next we want to add some management jobs. The jobs rely on credentials.

### Credentials

Please configure the following credentials, either through an existing CasC bundle or the UI.

We will need:

- `github-token-rw` - used to checkout and commit bundle changes
- `casc-validation-key` - license key used to start the test validation server
- `casc-validation-cert` - license cert used to start the test validation server
- `bundleutils-creds` - jenkins user and API token used by the tool to export the bundle and plugin installation json.

**NOTE:**

- the CasC snippet below is setting credential values through [CasC secrets](https://github.com/jenkinsci/configuration-as-code-plugin/blob/master/docs/features/secrets.adoc#passing-secrets-through-variables) - please adjust accordingly.
- if you use different credential ids, these will have to be change in the job spec as well.

```yaml
credentials:
  system:
    domainCredentials:
    - credentials:
        # needed to check out and push the results back to the repository
      - usernamePassword:
          description: Github Token for autocorrecting bundles
          id: github-token-rw
          password: ${GITHUB_TOKEN_RW_PASS}
          scope: GLOBAL
          username: ${GITHUB_TOKEN_RW_USER}

        # single user wildcard license to start the test server
      - string:
          id: casc-validation-key
          scope: GLOBAL
          secret: ${CASC_VALIDATION_LICENSE_KEY}
      - string:
          id: casc-validation-cert
          scope: GLOBAL
          secret: ${CASC_VALIDATION_LICENSE_CERT}

        # username and jenkins API token to read the CasC export
      - usernamePassword:
          description: bundleutils username and token to fetch the exports
          id: bundleutils-creds
          password: ${BUNDLEUTILS_PASSWORD}
          scope: GLOBAL
          username: ${BUNDLEUTILS_USERNAME}
          usernameSecret: true
```

### Job Specifications

Below is a CasC Items snippet for the management jobs.

- Replace all occurrences of `https://git.acme.org/my-org/my-bundles-repo # TODO - replace with your bundles repository` accordingly
- Replace all credentials IDs if different to those above.

If you are not using CasC, add the jobs manually according to the spec.

The jobs in question are:

- `*-direct`
  - **checkout the `main` branch** of the bundles repository
    - fetches the current config
    - transforms the current config
    - validates the current config
  - checks for and commits differences
  - commits any changes **to the main branch**
- `*-drift`
  - **checkout the `<bundle_name>-drift` branch** of the bundles repository
  - merges with the main branch before proceeding
    - fetches the current config
    - transforms the current config
    - validates the current config
  - checks for and commits differences
  - commits any changes **to the main branch**
- `xxxxxx-direct`
  - similar to a `*-direct` job but...
    - takes a regular expression
    - runs the steps for each matching bundle
- `xxxxxx-validate`
  - similar to the `xxxxxx-direct` job but...
    - takes a regular expression
    - validates each matching bundle

```yaml
removeStrategy:
  rbac: SYNC
  items: NONE
items:
- kind: freeStyle
  name: controller-a-direct
  blockBuildWhenDownstreamBuilding: false
  blockBuildWhenUpstreamBuilding: false
  buildDiscarder:
    logRotator:
      artifactDaysToKeep: -1
      artifactNumToKeep: -1
      daysToKeep: 30
      numToKeep: 30
  buildWrappers:
  - secretBuildWrapper:
      bindings:
      - gitUsernamePassword:
          gitToolName: Default
          credentialsId: github-token-rw
      - string:
          variable: CASC_VALIDATION_LICENSE_KEY
          credentialsId: casc-validation-key
      - string:
          variable: CASC_VALIDATION_LICENSE_CERT
          credentialsId: casc-validation-cert
      - usernamePassword:
          usernameVariable: BUNDLEUTILS_USERNAME
          passwordVariable: BUNDLEUTILS_PASSWORD
          credentialsId: bundleutils-creds
  builders:
  - shell:
      command: "set -e\n\necho \"Running bundleutils --help...\"\nbundleutils --help\n
        \necho \"Running main target...\"\nexport BUNDLEUTILS_PLUGINS_JSON_ADDITIONS='roots'\n
        make bundles/controller-bundles/controller-a/all\n\necho \"Running a git diff
        to check...\"\nif ! make bundles/controller-bundles/controller-a/git-diff;
        then\n\tmake bundles/controller-bundles/controller-a/git-commit\nfi\n# everything
        should have been committed, failing if diff found\nmake git-diff\n\n#export
        -p > $WORKSPACE_TMP/ENV\n#sleep 600"
  concurrentBuild: false
  description: ''
  disabled: false
  displayName: controller-a-direct
  label: bundleutils
  publishersList:
  - gitPublisher:
      branchesToPush:
      - branchToPush:
          branchName: main
          targetRepoName: origin
          rebaseBeforePush: true
      pushMerge: false
      pushOnlyIfSuccess: true
      forcePush: false
  scm:
    scmGit:
      extensions:
      - localBranch: {}
      - cloneOption:
          reference: ''
          noTags: true
          honorRefspec: false
          shallow: false
      - userIdentity:
          name: bundleutils-bot
          email: bundleutils-bot@example.org
      userRemoteConfigs:
      - userRemoteConfig:
          credentialsId: github-token-rw
          url: https://git.acme.org/my-org/my-bundles-repo # TODO - replace with your bundles repository
      branches:
      - branchSpec:
          name: refs/heads/main
  scmCheckoutStrategy:
    standard: {}
- kind: freeStyle
  name: controller-a-drift
  blockBuildWhenDownstreamBuilding: false
  blockBuildWhenUpstreamBuilding: false
  buildDiscarder:
    logRotator:
      artifactDaysToKeep: -1
      artifactNumToKeep: -1
      daysToKeep: 30
      numToKeep: 30
  buildWrappers:
  - secretBuildWrapper:
      bindings:
      - gitUsernamePassword:
          gitToolName: Default
          credentialsId: github-token-rw
      - string:
          variable: CASC_VALIDATION_LICENSE_KEY
          credentialsId: casc-validation-key
      - string:
          variable: CASC_VALIDATION_LICENSE_CERT
          credentialsId: casc-validation-cert
      - usernamePassword:
          usernameVariable: BUNDLEUTILS_USERNAME
          passwordVariable: BUNDLEUTILS_PASSWORD
          credentialsId: bundleutils-creds
  builders:
  - shell:
      command: "set -e\n\necho \"Running bundleutils --help...\"\nbundleutils --help\n
        \necho \"Running main target...\"\nexport BUNDLEUTILS_PLUGINS_JSON_ADDITIONS='roots'\n
        make bundles/controller-bundles/controller-a/all\n\necho \"Running a git diff
        to check...\"\nif ! make bundles/controller-bundles/controller-a/git-diff;
        then\n\tmake bundles/controller-bundles/controller-a/git-commit\nfi\n# everything
        should have been committed, failing if diff found\nmake git-diff\n\n#export
        -p > $WORKSPACE_TMP/ENV\n#sleep 600"
  concurrentBuild: false
  description: ''
  disabled: false
  displayName: controller-a-drift
  label: bundleutils
  publishersList:
  - gitPublisher:
      branchesToPush:
      - branchToPush:
          branchName: controller-a-drift
          targetRepoName: origin
          rebaseBeforePush: true
      pushMerge: false
      pushOnlyIfSuccess: true
      forcePush: true
  scm:
    scmGit:
      extensions:
      - localBranch: {}
      - cloneOption:
          reference: ''
          noTags: true
          honorRefspec: false
          shallow: false
      - userIdentity:
          name: bundleutils-bot
          email: bundleutils-bot@example.org
      - preBuildMerge:
          options:
            userMergeOptions:
              mergeStrategy: DEFAULT
              fastForwardMode: FF
              mergeTarget: main
              mergeRemote: origin
      userRemoteConfigs:
      - userRemoteConfig:
          credentialsId: github-token-rw
          url: https://git.acme.org/my-org/my-bundles-repo # TODO - replace with your bundles repository
      branches:
      - branchSpec:
          name: refs/heads/controller-a-drift
  scmCheckoutStrategy:
    standard: {}
- kind: freeStyle
  name: oc-bundle-direct
  blockBuildWhenDownstreamBuilding: false
  blockBuildWhenUpstreamBuilding: false
  buildDiscarder:
    logRotator:
      artifactDaysToKeep: -1
      artifactNumToKeep: -1
      daysToKeep: 30
      numToKeep: 30
  buildWrappers:
  - secretBuildWrapper:
      bindings:
      - gitUsernamePassword:
          gitToolName: Default
          credentialsId: github-token-rw
      - string:
          variable: CASC_VALIDATION_LICENSE_KEY
          credentialsId: casc-validation-key
      - string:
          variable: CASC_VALIDATION_LICENSE_CERT
          credentialsId: casc-validation-cert
      - usernamePassword:
          usernameVariable: BUNDLEUTILS_USERNAME
          passwordVariable: BUNDLEUTILS_PASSWORD
          credentialsId: bundleutils-creds
  builders:
  - shell:
      command: "set -e\n\necho \"Running bundleutils --help...\"\nbundleutils --help\n
        \necho \"Running main target...\"\nexport BUNDLEUTILS_PLUGINS_JSON_ADDITIONS='roots'\n
        make bundles/oc-bundles/oc-bundle/all\n\necho \"Running a git diff to check...\"\
        \nif ! make bundles/oc-bundles/oc-bundle/git-diff; then\n\tmake bundles/oc-bundles/oc-bundle/git-commit\n
        fi\n# everything should have been committed, failing if diff found\nmake git-diff\n
        \n#export -p > $WORKSPACE_TMP/ENV\n#sleep 600"
  concurrentBuild: false
  description: ''
  disabled: false
  displayName: oc-bundle-direct
  label: bundleutils
  publishersList:
  - gitPublisher:
      branchesToPush:
      - branchToPush:
          branchName: main
          targetRepoName: origin
          rebaseBeforePush: true
      pushMerge: false
      pushOnlyIfSuccess: true
      forcePush: false
  scm:
    scmGit:
      extensions:
      - localBranch: {}
      - cloneOption:
          reference: ''
          noTags: true
          honorRefspec: false
          shallow: false
      - userIdentity:
          name: bundleutils-bot
          email: bundleutils-bot@example.org
      - wipeWorkspace: {}
      userRemoteConfigs:
      - userRemoteConfig:
          credentialsId: github-token-rw
          url: https://git.acme.org/my-org/my-bundles-repo # TODO - replace with your bundles repository
      branches:
      - branchSpec:
          name: refs/heads/main
  scmCheckoutStrategy:
    standard: {}
- kind: freeStyle
  name: oc-bundle-drift
  blockBuildWhenDownstreamBuilding: false
  blockBuildWhenUpstreamBuilding: false
  buildDiscarder:
    logRotator:
      artifactDaysToKeep: -1
      artifactNumToKeep: -1
      daysToKeep: 30
      numToKeep: 30
  buildWrappers:
  - secretBuildWrapper:
      bindings:
      - gitUsernamePassword:
          gitToolName: Default
          credentialsId: github-token-rw
      - string:
          variable: CASC_VALIDATION_LICENSE_KEY
          credentialsId: casc-validation-key
      - string:
          variable: CASC_VALIDATION_LICENSE_CERT
          credentialsId: casc-validation-cert
      - usernamePassword:
          usernameVariable: BUNDLEUTILS_USERNAME
          passwordVariable: BUNDLEUTILS_PASSWORD
          credentialsId: bundleutils-creds
  builders:
  - shell:
      command: "set -e\n\necho \"Running bundleutils --help...\"\nbundleutils --help\n
        \necho \"Running main target...\"\nexport BUNDLEUTILS_PLUGINS_JSON_ADDITIONS='roots'\n
        make bundles/oc-bundles/oc-bundle/all\n\necho \"Running a git diff to check...\"\
        \nif ! make bundles/oc-bundles/oc-bundle/git-diff; then\n\tmake bundles/oc-bundles/oc-bundle/git-commit\n
        fi\n# everything should have been committed, failing if diff found\nmake git-diff\n
        \n#export -p > $WORKSPACE_TMP/ENV\n#sleep 600"
  concurrentBuild: false
  description: ''
  disabled: false
  displayName: oc-bundle-drift
  label: bundleutils
  publishersList:
  - gitPublisher:
      branchesToPush:
      - branchToPush:
          branchName: oc-bundle-drift
          targetRepoName: origin
          rebaseBeforePush: true
      pushMerge: false
      pushOnlyIfSuccess: true
      forcePush: true
  scm:
    scmGit:
      extensions:
      - localBranch: {}
      - cloneOption:
          reference: ''
          noTags: true
          honorRefspec: false
          shallow: false
      - userIdentity:
          name: bundleutils-bot
          email: bundleutils-bot@example.org
      - preBuildMerge:
          options:
            userMergeOptions:
              mergeStrategy: DEFAULT
              fastForwardMode: FF
              mergeTarget: main
              mergeRemote: origin
      - wipeWorkspace: {}
      userRemoteConfigs:
      - userRemoteConfig:
          credentialsId: github-token-rw
          url: https://git.acme.org/my-org/my-bundles-repo # TODO - replace with your bundles repository
      branches:
      - branchSpec:
          name: refs/heads/oc-bundle-drift
  scmCheckoutStrategy:
    standard: {}
- kind: freeStyle
  name: xxxxxx-direct
  blockBuildWhenDownstreamBuilding: false
  blockBuildWhenUpstreamBuilding: false
  buildDiscarder:
    logRotator:
      artifactDaysToKeep: -1
      artifactNumToKeep: -1
      daysToKeep: 30
      numToKeep: 30
  buildWrappers:
  - secretBuildWrapper:
      bindings:
      - gitUsernamePassword:
          gitToolName: Default
          credentialsId: github-token-rw
      - string:
          variable: CASC_VALIDATION_LICENSE_KEY
          credentialsId: casc-validation-key
      - string:
          variable: CASC_VALIDATION_LICENSE_CERT
          credentialsId: casc-validation-cert
      - usernamePassword:
          usernameVariable: BUNDLEUTILS_USERNAME
          passwordVariable: BUNDLEUTILS_PASSWORD
          credentialsId: bundleutils-creds
  builders:
  - shell:
      command: "set -e\necho \"BUNDLE_REGEX='$BUNDLE_REGEX'\"\necho \"DRY_RUN='$DRY_RUN'\"\
        \n\nfor bundle in $(make find BP=\"$BUNDLE_REGEX\"); do\n  echo \"Running
        main target for '$bundle'...\"\n  make \"$bundle\"/all\n\n  echo \"Running
        a git diff to check...\"\n  if ! make \"$bundle\"/git-diff; then\n  \tmake
        \"$bundle\"/git-commit\n  fi\n  # everything should have been committed, failing
        if diff found\n  make git-diff\ndone\n\nif [ \"$DRY_RUN\" = \"true\" ]; then\n\
        \  echo \"DRY_RUN=true so resetting hard so as not to push anything...\"\n\
        \  make git-reset\nfi\n#export -p > $WORKSPACE_TMP/ENV\n#sleep 600"
  concurrentBuild: false
  description: ''
  disabled: false
  displayName: xxxxxx-direct
  label: bundleutils
  parameters:
  - booleanParam:
      defaultValue: true
      name: DRY_RUN
      description: Uncheck to push changes to main
  - string:
      trim: false
      defaultValue: (controller-a)
      name: BUNDLE_REGEX
      description: Regex to match bundle names. e.g. (oc-bundle|controller-a) or (controller-.*)
  publishersList:
  - gitPublisher:
      branchesToPush:
      - branchToPush:
          branchName: main
          targetRepoName: origin
          rebaseBeforePush: true
      pushMerge: false
      pushOnlyIfSuccess: true
      forcePush: false
  scm:
    scmGit:
      extensions:
      - localBranch: {}
      - cloneOption:
          reference: ''
          noTags: true
          honorRefspec: false
          shallow: false
      - userIdentity:
          name: bundleutils-bot
          email: bundleutils-bot@example.org
      userRemoteConfigs:
      - userRemoteConfig:
          credentialsId: github-token-rw
          url: https://git.acme.org/my-org/my-bundles-repo # TODO - replace with your bundles repository
      branches:
      - branchSpec:
          name: refs/heads/main
  scmCheckoutStrategy:
    standard: {}
- kind: freeStyle
  name: xxxxxx-validate
  blockBuildWhenDownstreamBuilding: false
  blockBuildWhenUpstreamBuilding: false
  buildDiscarder:
    logRotator:
      artifactDaysToKeep: -1
      artifactNumToKeep: -1
      daysToKeep: 30
      numToKeep: 30
  buildWrappers:
  - secretBuildWrapper:
      bindings:
      - gitUsernamePassword:
          gitToolName: Default
          credentialsId: github-token-rw
      - string:
          variable: CASC_VALIDATION_LICENSE_KEY
          credentialsId: casc-validation-key
      - string:
          variable: CASC_VALIDATION_LICENSE_CERT
          credentialsId: casc-validation-cert
      - usernamePassword:
          usernameVariable: BUNDLEUTILS_USERNAME
          passwordVariable: BUNDLEUTILS_PASSWORD
          credentialsId: bundleutils-creds
  builders:
  - shell:
      command: |-
        set -e
        echo "BUNDLE_REGEX='$BUNDLE_REGEX'"
        echo "DRY_RUN='$DRY_RUN'"

        for bundle in $(make find BP="$BUNDLE_REGEX"); do
          echo "Running main target for '$bundle'..."
          make "$bundle"/validate
        done
        #export -p > $WORKSPACE_TMP/ENV
        #sleep 600
  concurrentBuild: false
  description: "This job WILL NOT FETCH AND TRANSFORM bundles. It will ONLY VALIDATE
    EXISTING bundles.\r\n\r\nThis is useful for testing feature branches for changes
    not made through the UI."
  disabled: false
  displayName: xxxxxx-validate
  label: bundleutils
  parameters:
  - string:
      trim: false
      defaultValue: (oc-bundle)
      name: BUNDLE_REGEX
      description: Regex to match bundle names. e.g. (oc-bundle|controller-a) or (controller-.*)
  - string:
      trim: true
      defaultValue: main
      name: VALIDATION_BRANCH
      description: Branch to use for the bundles validation.
  scm:
    scmGit:
      extensions:
      - localBranch: {}
      - cloneOption:
          reference: ''
          noTags: true
          honorRefspec: false
          shallow: false
      - userIdentity:
          name: bundleutils-bot
          email: bundleutils-bot@example.org
      userRemoteConfigs:
      - userRemoteConfig:
          credentialsId: github-token-rw
          url: https://git.acme.org/my-org/my-bundles-repo # TODO - replace with your bundles repository
      branches:
      - branchSpec:
          name: refs/heads/${VALIDATION_BRANCH}
  scmCheckoutStrategy:
    standard: {}
```

### Custom View

Here is an example snippet to create a view containing all your Bundle Management jobs.

Add to your jenkins.yaml if required.

```yaml
jenkins:
  views:
  - list:
      columns:
      - status
      - jobName
      - lastSuccess
      - lastFailure
      - lastDuration
      - buildButton
      filterExecutors: true
      filterQueue: true
      includeRegex: (.*-drift|.*-direct|xxxxxx-.*)
      name: Bundles Jobs
```
