# Running Locally With Docker Compose

```sh
# start the container
docker compose up -d # add '--pull' to update to latest image

# exec into the container
# - your current directory can be found under /work
# - some examples can be found under /opt/bundleutils/work/examples
docker compose exec bundleutils bash

# ...
# ...perform your tests
# ...

# stop the container
docker compose down --remove-orphans
```
