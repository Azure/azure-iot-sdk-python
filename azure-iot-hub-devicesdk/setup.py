# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    _long_description = fh.read()

setup(
    name="azure_iot_hub_devicesdk",
    version="0.0.0a1",  # Alpha Release
    description="Microsoft Azure IoT Hub Device SDK",
    license="MIT License",
    url="https://github.com/Azure/azure-iot-sdk-python",
    author="Microsoft Corporation",
    author_email="opensource@microsoft.com",
    long_description=_long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    install_requires=[
        "azure-iot-common",
        "six>=1.12.0,<2.0.0",
        "paho-mqtt>=1.4.0,<2.0.0",
        "transitions>=0.6.8,<1.0.0",
        "requests>=2.20.0,<3.0.0",
        "requests-unixsocket>=0.1.5,<1.0.0",
        "janus>=0.4.0,<1.0.0;python_version>='3.5'",
    ],
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3*, <4",
    packages=find_packages(exclude=["tests", "samples"]),
)
