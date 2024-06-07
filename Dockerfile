# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container to /app
WORKDIR /app

# Add the current directory contents into the container at /app
ADD bundleutilspkg bundleutilspkg
ADD setup.py ./

# Install any needed packages specified in setup.py
RUN pip install . \
    && groupadd -g 1000 bundle-user && useradd -u 1000 -g bundle-user -s /bin/bash -m bundle-user

USER bundle-user

# Set the working directory in the container to /home/bundle-user
WORKDIR /home/bundle-user

# Add the current directory contents into the container at /app
ADD examples examples
ADD README.md ./

ENV PATH="/app/bin:/home/bundle-user/bin:$PATH"

# Run main.py when the container launches
ENTRYPOINT [ "bundleutils"]