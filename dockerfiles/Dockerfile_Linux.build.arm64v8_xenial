FROM arm64v8/buildpack-deps:xenial-scm as build

# Update image
SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y cmake build-essential curl libcurl4-openssl-dev \
    libssl-dev uuid-dev apt-utils python python-pip python-virtualenv python3 python3-pip python3-virtualenv \
    libboost-python-dev pkg-config valgrind sudo

WORKDIR /usr/sdk

RUN python -m virtualenv --python=python3 env3
RUN source env3/bin/activate && pip install --upgrade pip && pip install -U setuptools wheel

# Copy code (this assumes the ./src folder contains the recursively cloned SDK repository (azure/azure-iot-sdk-python))
COPY ./src ./src

# Build for Python 3
RUN source env3/bin/activate && ./src/build_all/linux/setup.sh --python-version 3.5
RUN source env3/bin/activate && ./src/build_all/linux/release.sh --build-python 3.5

# Repeat for Python 2
RUN pip install --upgrade pip==10.0.1 && python -m pip install -U setuptools wheel
RUN ./src/build_all/linux/setup.sh
RUN ./src/build_all/linux/release.sh
