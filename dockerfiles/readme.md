# Dockerfiles for the Azure IoT SDK for Python

The current implementation of the Python SDK is a wrapper over the Azure IoT C SDK and has external dependencies that cannot be installed with pip (Boost, libssl, curl...). The versions for these dependencies have to match exactly (because of how C linkers work).

To simplify the development process you'll find in this folder a few Dockerfiles that we know work to either run the precompiled packages available on PyPI or rebuild the SDK for your own hardware or dependency versions. If you go through the trouble of creating your own dockerfile, please don't hesitate to submit a pull-request and we'll be happy to add it here.

The *.build.* files contain scripts to build the SDK and assume the SDK repository has been cloned into the *src* folder adjacent to the Dockerfile.

The *.run.* files contain scripts to install the dependencies and the pip package and assume an *src* folder adjacent to the Dockerfile contains a Python application that makes use of the SDK and uses an *app.py* file as an entrypoint. it will not install other requirements so you may have to modify the Dockerfile if you need to run additional `pip install` commands.
