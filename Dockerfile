FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the local pit-project directory to the container at /app/pit-project
COPY ./pit-project /app/pit-project

# Make the pit.py script executable
RUN chmod +x /app/pit-project/pit.py

# Create a symbolic link to make 'pit' a global command
RUN ln -s /app/pit-project/pit.py /usr/local/bin/pit

# Set a default working directory for the user
WORKDIR /workspace

# Set the default command to provide an interactive shell
CMD ["/bin/bash"]