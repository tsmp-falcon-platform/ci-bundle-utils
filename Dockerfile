# Use an official Python runtime as a parent image
FROM eclipse-temurin:17.0.11_9-jdk-jammy

# TODO: make multi-stage build
# COPY --from=builder /opt/venv /opt/venv

# Install any needed packages specified in setup.py
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim-tiny \
    git \
    make \
    skopeo \
    python3 \
    python3-venv \
    python3-pip \
    zip \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /opt/bundleutils/.cache /opt/bundleutils/.app /opt/bundleutils/work \
    && chmod -R 777 /opt/bundleutils/.cache /opt/bundleutils/work

# Create a virtual environment
RUN python3 -m venv /opt/bundleutils/.venv
ENV PATH="/opt/bundleutils/.venv/bin:$PATH" BUNDLEUTILS_CACHE_DIR="/opt/bundleutils/.cache"

# Install any needed packages specified in setup.py
RUN pip install --upgrade pip \
    && pip install wheel

# Add the current directory contents into the container at /app
ADD bundleutilspkg /opt/bundleutils/.app/bundleutilspkg
ADD examples /opt/bundleutils/work/examples
ADD README.md /opt/bundleutils/work/README.md

# Install any needed packages specified in setup.py
RUN pip install /opt/bundleutils/.app/bundleutilspkg

# Install any needed packages specified in setup.py
RUN useradd -m -u 1000 bundle-user

# Set the working directory in the container to /home/bundle-user
WORKDIR /opt/bundleutils/work
USER bundle-user

# Run main.py when the container launches
ENTRYPOINT [ "bundleutils"]