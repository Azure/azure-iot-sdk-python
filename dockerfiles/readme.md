# Dockerfiles for the Azure IoT SDK for Python

The current implementation of the Python SDK is a wrapper over the C SDK and has external dependencies that cannot be installed with pip (Boost, libssl, curl...). The versions for these dependencies have to match exactly (because of how C linkers work).

To simplify the development process you'll find in this folder a few Dockerfiles that we know work to either run the precompiled packages available on PyPI or rebuild the SDK for your own hardware or dependency versions. If you go through the trouble of creating your own dockerfile, please don't hesitate to submit a pull-request and we'll be happy to add it here.
