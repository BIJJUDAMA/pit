# Python base image
FROM python:3.12-alpine

# Set the working directory in the container
WORKDIR /app

# Copy the local pit-project directory to the container at /app/pit-project
COPY ./pit-project /app/pit-project

# Copy tests directory
COPY ./tests /app/tests

# Install pytest for testing
RUN pip install --no-cache-dir pytest pytest-cov

# Create the pit command wrapper
RUN echo '#!/bin/sh' > /usr/local/bin/pit && \
    echo 'python3 /app/pit-project/pit.py "$@"' >> /usr/local/bin/pit && \
    chmod +x /usr/local/bin/pit

# Set a default working directory for the user
WORKDIR /workspace

# Set the default command to provide an interactive shell
CMD ["sh"]