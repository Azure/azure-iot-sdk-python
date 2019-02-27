# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    _long_description = fh.read()

setup(
    name="azure-iot-common",
    version="0.0.1",
    description="Microsoft Azure IoT SDK Common",
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
    install_requires=["six>=1.12.0,<2.0.0"],
    packages=find_packages(exclude=["tests"]),
)
