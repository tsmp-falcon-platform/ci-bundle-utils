# Use an official Python runtime as a parent image
FROM eclipse-temurin:17.0.11_9-jdk-jammy

# TODO: Add the maintainer label
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
    && useradd -m -u 1000 bundle-user

# Set the working directory in the container to /home/bundle-user
WORKDIR /home/bundle-user
USER bundle-user

# Create a virtual environment
RUN python3 -m venv /home/bundle-user/venv
ENV PATH="/home/bundle-user/venv/bin:$PATH"

# Add the current directory contents into the container at /app
ADD --chown=bundle-user:bundle-user bundleutilspkg bundleutilspkg

# Install any needed packages specified in setup.py
RUN pip install --upgrade pip \
    && pip install wheel \
    && pip install ./bundleutilspkg \
    && mkdir -p ./bundleutils/cache

# Add the current directory contents into the container
ADD --chown=bundle-user:bundle-user examples examples
ADD --chown=bundle-user:bundle-user README.md ./

# Run main.py when the container launches
ENTRYPOINT [ "bundleutils"]