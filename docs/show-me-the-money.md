# Bundles Config and Transformations

Enough docs, now show me how this works...

The following gives provides an example for one operations center and one controller.

## Create Repo

Copy the [../examples/example-bundles-repo](../examples/example-bundles-repo) to a repository of your choice.

**NOTE:** You can also use the template repository at https://github.com/tsmp-falcon-platform/example-bundles-drift

Notice the structure and the `env.<bundle_name>.yaml` configuration file in the parent directory.

```sh
oc-bundles
├── oc-bundle
│   └── bundle.yaml
└── env.oc-bundle.yaml
```

```sh
controller-bundles/
├── controller-bundle
│   └── bundle.yaml
└── env.controller-bundle.yaml
```

Edit the configuration files, adding the values for your instances (search for `TODO`):

```sh
vim bundles/oc-bundles/env.oc-bundle.yaml
vim bundles/controller-bundles/env.controller-bundle.yaml
```

Commit your changes.

## Create Cloud, PodTemplate, Credentials and Jobs

Follow the instructions in [setup-cloudbees-casc.md](./setup-cloudbees-casc.md), replacing the `TODO` sections accordingly.
