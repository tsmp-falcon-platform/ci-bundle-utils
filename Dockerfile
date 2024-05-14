# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Add the current directory contents into the container at /app
ADD examples /app/examples
ADD bundle_utils /app/bundle_utils
ADD setup.py README.md /app/

# Set the working directory in the container to /app
WORKDIR /app

# Install any needed packages specified in setup.py
RUN pip install . \
    && groupadd -g 1000 bundle-user && useradd -u 1000 -g bundle-user -s /bin/bash -m bundle-user \
    && mkdir -p /home/bundle-user/bin && chown -R bundle-user:bundle-user /home/bundle-user/bin /app

ENV PATH="/home/bundle-user/bin:$PATH"

# Run main.py when the container launches
CMD ["bundle_utils"]