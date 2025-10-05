# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the local pit-project directory to the container at /app/pit-project
COPY ./pit-project /app/pit-project

# Remove the old symbolic link and create a new wrapper script.
# This is a more robust way to ensure the script is executed with Python.
RUN rm -f /usr/local/bin/pit && \
    echo '#!/bin/sh' > /usr/local/bin/pit && \
    echo 'python3 /app/pit-project/pit.py "$@"' >> /usr/local/bin/pit && \
    chmod +x /usr/local/bin/pit

# Set a default working directory for the user
WORKDIR /workspace

# Set the default command to provide an interactive shell
CMD ["/bin/bash"]

