# Running in Kubernetes

To deploy to kubernetes directly, simply run...

```sh
kubectl run bundleutils --image=ghcr.io/tsmp-falcon-platform/ci-bundle-utils:latest --restart=Never
```

Alternatively passing environment variables, e.g.

```sh
kubectl run bundleutils --image=ghcr.io/tsmp-falcon-platform/ci-bundle-utils:latest \
  --env=BUNDLEUTILS_USERNAME="${BUNDLEUTILS_USERNAME:-}" \
  --env=BUNDLEUTILS_PASSWORD="${BUNDLEUTILS_PASSWORD:-}" \
  --env=CASC_VALIDATION_LICENSE_KEY_B64="${CASC_VALIDATION_LICENSE_KEY_B64:-}" \
  --env=CASC_VALIDATION_LICENSE_CERT_B64="${CASC_VALIDATION_LICENSE_CERT_B64:-}" \
  --restart=Never
```
