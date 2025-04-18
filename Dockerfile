# Use an official Python runtime as a parent image
FROM eclipse-temurin:17.0.11_9-jdk-jammy

# Build arguments
ARG BUNDLEUTILS_RELEASE_VERSION
ARG BUNDLEUTILS_RELEASE_HASH

# TODO: make multi-stage build
# COPY --from=builder /opt/venv /opt/venv

# Install any needed packages specified in setup.py
RUN apt-get update && apt-get install -y --no-install-recommends \
    less \
    vim \
    git \
    make \
    skopeo \
    python3 \
    python3-venv \
    python3-pip \
    zip \
    unzip \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /opt/bundleutils/.cache /opt/bundleutils/.app /opt/bundleutils/work /workspace \
    && chmod -R 777 /opt/bundleutils/.cache /opt/bundleutils/work /workspace

# Install Java 11 from Adoptium
# Needed for CloudBees CI version 2.426.3.3 and earlier
RUN wget -q -O /tmp/temurin-11.tar.gz https://github.com/adoptium/temurin11-binaries/releases/download/jdk-11.0.20.1+1/OpenJDK11U-jdk_x64_linux_hotspot_11.0.20.1_1.tar.gz \
    && mkdir -p /usr/lib/jvm/temurin-11-jdk-amd64 \
    && tar -xf /tmp/temurin-11.tar.gz -C /usr/lib/jvm/temurin-11-jdk-amd64 --strip-components=1 \
    && rm /tmp/temurin-11.tar.gz

# Set environment variables to use Java 11 by default
ENV JAVA_HOME_11=/usr/lib/jvm/temurin-11-jdk-amd64

# Example to make Java 11 the default Java version
# ENV JAVA_HOME=$JAVA_HOME_11
# ENV PATH=$JAVA_HOME/bin:$PATH

# Create a virtual environment
RUN python3 -m venv /opt/bundleutils/.venv
ENV PATH="/opt/bundleutils/.venv/bin:$PATH" BUNDLEUTILS_CACHE_DIR="/opt/bundleutils/.cache"

# Install any needed packages specified in setup.py
RUN pip install --upgrade pip \
    && pip install wheel pyinstaller

# Set environment variables for runtime access
ENV BUNDLEUTILS_RELEASE_VERSION=$BUNDLEUTILS_RELEASE_VERSION
ENV BUNDLEUTILS_RELEASE_HASH=$BUNDLEUTILS_RELEASE_HASH

# Add the current directory contents into the container at /app
ADD bundleutilspkg /opt/bundleutils/.app/bundleutilspkg
ADD examples /opt/bundleutils/work/examples
ADD README.md /opt/bundleutils/work/README.md

# Install any needed packages specified in setup.py
RUN cd /opt/bundleutils/.app/bundleutilspkg \
    && pip install ".[dev]" \
    && pyinstaller --noconfirm --clean --onedir \
	--add-data "src/bundleutilspkg/data/configs:data/configs" \
	--copy-metadata bundleutilspkg \
	src/bundleutilspkg/bundleutils.py

# Install any needed packages specified in setup.py
RUN useradd -m -u 1000 bundle-user

# Set the working directory in the container to /home/bundle-user
WORKDIR /opt/bundleutils/work
USER bundle-user

# Run main.py when the container launches
ENTRYPOINT [ "bundleutils"]