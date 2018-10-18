# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from setuptools import setup, find_packages

with open("doc/package-readme.md", "r") as fh:
    _long_description = fh.read()

setup(
    name="azure-iot-hub-devicesdk",
    version="0.0.1",
    description="Microsoft Azure IoT Hub Device SDK",
    license="MIT License",
    url="https://github.com/Azure/azure-iot-sdk-python",
    author="Microsoft Corporation",
    long_description=_long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT Software License",
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
        "six",
        "paho-mqtt==1.4.0",
        "transitions==0.6.8",
        "enum34==1.1.6",
    ],
    packages=find_packages(exclude=["tests"]),
)
