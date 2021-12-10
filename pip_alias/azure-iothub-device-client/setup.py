# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from setuptools import setup
import os


VERSION = "2.0.0"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="azure-iothub-device-client",
    description="azure-iothub-device-client is now azure-iot-device",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    version=VERSION,
    author="Microsoft Corporation",
    author_email="opensource@microsoft.com",
    license="MIT License",
    license_files=("LICENSE",),
    classifiers=["Development Status :: 7 - Inactive"],
    install_requires=["azure-iot-device"],
)
