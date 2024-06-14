# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container to /app
WORKDIR /app

# Install any needed packages specified in setup.py
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    make \
    zip \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 bundle-user

# Add the current directory contents into the container at /app
ADD bundleutilspkg bundleutilspkg
ADD setup.py ./

# Install any needed packages specified in setup.py
RUN pip install .

# Set the working directory in the container to /home/bundle-user
USER bundle-user
WORKDIR /home/bundle-user

# Add the current directory contents into the container at /app
ADD examples examples
ADD README.md ./

ENV PATH="/app/bin:/home/bundle-user/bin:$PATH"

# Run main.py when the container launches
ENTRYPOINT [ "bundleutils"]