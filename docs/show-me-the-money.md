# Bundles Config and Transformations

Enough docs, now show me how this works...

The following gives provides an example for one operations center and one controller.

## Create Repo

Copy the [../examples/example-bundles-repo](../examples/example-bundles-repo) to a repository of your choice.

Notice the structure:

- the `bundle-profiles.yaml` configuration file in the parent directory
- the `transformations` directory

```sh
bundles
├── bundle-profiles.yaml
├── controller-bundles
│   └── controller-bundle
│       └── bundle.yaml
├── oc-bundles
│   └── oc-bundle
│       └── bundle.yaml
└── transformations
    ├── add-local-users.yaml
    ├── controllers-common.yaml
    ├── oc-common.yaml
    └── remove-dynamic-stuff.yaml
```

Edit the configuration file, adding the values for your instances (search for `TODO`):

```sh
vim bundles/bundle-profiles.yaml
```

Commit your changes.

## Create Cloud, PodTemplate, Credentials and Jobs

Follow the instructions in [setup-cloudbees-casc.md](./setup-cloudbees-casc.md), replacing the `TODO` sections accordingly.
