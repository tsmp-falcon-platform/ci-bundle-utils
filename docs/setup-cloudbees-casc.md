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

**NOTE:** Check the sections commented with `# TODO...`

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
              image: ghcr.io/tsmp-falcon-platform/ci-bundle-utils
              imagePullPolicy: Always
              command: ["/usr/share/jenkins/jenkins-agent"]
              volumeMounts:
              - name: pseudo-jnlp
                mountPath: /usr/share/jenkins
                # TODO - remove if not using the bundleutils-cache-pvc
              - name: bundleutils-cache
                mountPath: /opt/bundleutils/.cache
            initContainers:
            - name: copy-agent-stuff
              image: cloudbees/cloudbees-core-agent:2.452.3.2 # TODO: check for the your version of CI
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
              image: ghcr.io/tsmp-falcon-platform/ci-bundle-utils
              imagePullPolicy: Always
              command: ["/usr/share/jenkins/jenkins-agent"]
              volumeMounts:
              - name: pseudo-jnlp
                mountPath: /usr/share/jenkins
                # TODO - remove if not using the bundleutils-cache-pvc
              - name: bundleutils-cache
                mountPath: /opt/bundleutils/.cache
            initContainers:
            - name: copy-agent-stuff
              image: cloudbees/cloudbees-core-agent:2.452.3.2 # TODO: check for the your version of CI
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
  displayName: ''
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

The real world example of the snippet below can found in the [real world example](../examples/real-world-example/bundles/oc-bundles/oc-bundle/jenkins.credentials.yaml)

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

The jobs in question are in two categories.

The local generic jobs:

- `casc-local-sync-direct`
  - generic job which
    - does not rely on specific server names, etc
    - relies on the local `JENKINS_URL`
    - can be used on any operation center or controller without alterations
  - performs:
    - **checkout of the `main` branch** of the bundles repository
    - fetches the current config
    - transforms the current config
    - validates the current config
  - checks for and commits differences
  - pushes any changes **DIRECTLY TO THE MAIN BRANCH**
- `casc-local-sync-drift`
  - generic job which relies on the local `JENKINS_URL`
  - as with `casc-local-sync-direct` but checks out and rebases a drift branch
  - commits any changes **TO THE DRIFT BRANCH**

The custom jobs:

- `casc-custom-sync-direct`
  - as with `casc-local-sync-direct` but parameterized to allow running multiple bundles
- `casc-custom-sync-drift`
  - as with `casc-local-sync-drift` but parameterized to allow running multiple bundles
- `casc-custom-validate`
  - validate any bundle on any branch
- `casc-custom-deploy-cm`
  - deploy bundles as config maps FROM THE MAIN BRANCH

A real world example of the jobs below can be found in the real world example:

- [oc-bundle/items.casc-local-jobs.yaml](../examples/real-world-example/bundles/oc-bundles/oc-bundle/items.casc-local-jobs.yaml)
- [oc-bundle/items.casc-custom-jobs.yaml](../examples/real-world-example/bundles/oc-bundles/oc-bundle/items.casc-custom-jobs.yaml)
- [controller-a/items.casc-local-jobs.yaml](../examples/real-world-example/bundles/controller-bundles/controller-a/items.casc-local-jobs.yaml)

### Custom View

Here is an example snippet to create a view containing all your Bundle Management jobs.

Again, a real world example can be found in the [real world example](../examples/real-world-example/bundles/oc-bundles/oc-bundle/jenkins.views.yaml)

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
      includeRegex: (casc-custom-.*|casc-local-.*)
      name: Bundles
```
