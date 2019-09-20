FROM jfloff/alpine-python:latest-slim

# Copy required files
COPY requirements.txt /requirements.txt
COPY service/ /service

# waiting for https://github.com/jfloff/alpine-python/issues/6 to be fixed again
RUN chmod +x /entrypoint.sh
RUN /entrypoint.sh -P requirements.txt

# Set the environment
ENV HTTP_PORT=80

EXPOSE 80
EXPOSE 5672
CMD ["python","-u", "-m" , "service"]
