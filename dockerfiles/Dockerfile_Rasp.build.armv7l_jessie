FROM resin/raspberrypi3-python:2.7.13

ENV INITSYSTEM=on

# Update image
SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y sudo cmake build-essential curl libcurl4-openssl-dev \
    libssl-dev uuid-dev python python-pip apt-utils python-virtualenv python3 python3-pip

WORKDIR /usr/sdk

# Copy code (this assumes the ./src folder contains the recursively cloned SDK repository (azure/azure-iot-sdk-python))
COPY ./src ./src

RUN python -m virtualenv --python=python3.4 env34
RUN source env34/bin/activate && pip install --upgrade pip && pip install -U setuptools wheel

# Build for Python 3
RUN source env34/bin/activate && ./src/build_all/linux/setup.sh --python-version 3.4
RUN source env34/bin/activate && ./src/build_all/linux/release.sh --build-python 3.4

# Repeat for Python 2
RUN pip install --upgrade pip && pip install -U setuptools wheel

RUN ./src/build_all/linux/setup.sh
RUN ./src/build_all/linux/release.sh
