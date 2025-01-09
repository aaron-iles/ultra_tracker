# Use a base image with Python
FROM python:3.13

# Set the working directory in the container
WORKDIR /app

# Set up a directory to be mounted from the host machine
VOLUME /app

COPY requirements.txt /app/

RUN useradd -ms /bin/bash uwsgi

RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Set the entry point and default command for the container
CMD ["./docker-entrypoint.sh"]
