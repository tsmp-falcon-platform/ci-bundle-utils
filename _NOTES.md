# Docker build

```bash
sudo docker buildx create --name multiarch-builder --driver docker-container --use
sudo docker buildx inspect --bootstrap

sudo docker buildx build   --platform linux/amd64,linux/arm64   -t caternberg/bundleutils:dev3   --push   .

#sudo docker build  -t caternberg/bundleutils:dev2 --push .
```







# Docker run 

```
#IMAGE=ghcr.io/tsmp-falcon-platform/ci-bundle-utils
IMAGE=caternberg/bundleutils:dev3 \
docker run --rm -it --name bundleutils \
-v bundleutils-cache:/opt/bundleutils/.cache \
-e BUNDLEUTILS_USERNAME="${BUNDLEUTILS_USERNAME:-}" \
-e BUNDLEUTILS_PASSWORD="${BUNDLEUTILS_PASSWORD:-}" \
-e BUNDLE_UID=$(id -u) \
-e BUNDLE_GID=$(id -u) \
-v $(pwd):/workspace \
-w /workspace \
$IMAGE \
bash
```





