# Explaining Transformations

The `bundleutils transform` command allows passing one of more transformation yaml files.

These yaml files contains instructions on how to manipulate the files inside the bundle.

Each yaml file can consist of 4 sections

- `patches`
  - written per file
  - contains a list of JSON patch expressions to apply
- `credentials`
  - used to replace encrypted credentials values
  - written per file
  - contains a list of entries to replace
  - credentials found but not listed will be auto-replaced according to the id and field
  - replacing any field of a credential with `PLEASE_DELETE_ME` will delete the entry completely
- `splits`
  - contains two types of split - `items` and `jcasc`
  - `items`
    - written per file
    - contains a list of pattern and target
    - `pattern` - will match the name of the item
    - `target` - the target file whereby:
      - `xxxxxxx.yaml` will save all matched items as `xxxxxxx.yaml`
      - `auto` will save each matched item in a separate file
      - `delete` will remove the item from the list
  - `jcasc`
    - written per file
    - contains a list of paths and target
    - `paths` - will match all the paths given
    - `target` - the target file whereby:
      - `xxxxxxx.yaml` will save all matched items as `xxxxxxx.yaml`
      - `auto` will save each matched item in a separate file
- `substitutions`
  - written per file
  - contains a list of regex patterns and replacement
  - can be used as a fallback if the above doesn't fit the requirements

## Example

```yaml
# Patches based upon https://jsonpatch.com/
patches:
  jenkins.yaml:
  - op: remove
    path: /license # you may want to keep this if you have a license file
  - op: remove
    path: /jenkins/labelAtoms # these labels are dynamic based on the agents available

# Replace credentials with references to variables
# Autosetting:
# - github-token-ro/password -> GITHUB_TOKEN_RO_PASSWORD
# - github-token-rw/password -> GITHUB_TOKEN_RW_PASSWORD
# Explicit:
# - id: github-token-ro
#   password: ${MY_READ_TOKEN}
#   username: ${MY_READ_TOKEN}
# - id: github-org-hooks-shared-secret
#   secret: ${MY_SHARED_ORGS_HOOKS_SECRET}
# Deleting:
# - id: my-superfluous-cred
#   password: PLEASE_DELETE_ME
credentials:
  # jenkins.yaml:
  # - id: github-token-ro
  #   password: "${MY_READ_TOKEN}"
  # - id: github-token-rw
  #   password: "${MY_WRITE_TOKEN}"
  # items.yaml:
  # - id: test-folder-cred
  #   password: "${MY_FOLDER_TOKEN}"
  jenkins.yaml: {}
  items.yaml: {}


splits:
  # Split by name on regex (auto takes each item separately)
  # items:
  #   items.yaml:
  #   - target: auto
  #     patterns: ['casc-test-.*']
  #   - target: controllers.yaml
  #     patterns: ['controller-.*']
  #   - target: delete
  #     patterns: ['test-fs']
  items: {}
  # Split by path whereby target can take 'auto', 'delete', or the specific file name:
  #   'auto' takes each item separately, replacing '/' with '.'
  #   'delete' deletes the file completely
  # jcasc:
  #   jenkins.yaml:
  #   - target: auto
  #     paths:
  #     - credentials
  #   - target: kubernetes.yaml
  #     paths:
  #     - masterprovisioning
  #     - kube
  jcasc: {}

  # Replace all instances of 'pattern' with 'value' in the yaml files
substitutions: {}
  # jenkins.yaml:
  # - pattern: cloudbees/cloudbees-core-agent:[0-9\.]+
  #   value: cloudbees/cloudbees-core-agent:${readFile:/var/jenkins_home/jenkins.install.InstallUtil.lastExecVersion}
```