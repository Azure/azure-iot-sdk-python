FROM ubuntu:16.04

# Update image
SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends libcurl4-openssl-dev python3-pip python3 libboost-python-dev python3-dev

WORKDIR /usr/sdk

RUN pip3 install --upgrade pip
RUN pip install azure-iothub-device-client

# Copy code (this assumes the ./src folder contains the code using the SDK and that the entrypoint is app.py)
COPY ./src ./src

CMD ["python3", "-u", "./src/app.py"]