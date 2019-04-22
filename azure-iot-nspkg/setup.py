# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
from setuptools import setup

# azure v0.x is not compatible with this package
# azure v0.x used to have a __version__ attribute (newer versions don't)
try:
    import azure

    try:
        ver = azure.__version__
        raise Exception(
            "This package is incompatible with azure=={}. ".format(ver)
            + 'Uninstall it with "pip uninstall azure".'
        )
    except AttributeError:
        pass
except ImportError:
    pass


with open("README.md", "r") as fh:
    _long_description = fh.read()


PACKAGES = []
# Do an empty package on Python 3 and not python_requires, since not everybody is ready
# https://github.com/Azure/azure-sdk-for-python/issues/3447
# https://github.com/Azure/azure-sdk-for-python/issues/3481
if sys.version_info[0] < 3:
    PACKAGES = ["azure.iot"]


setup(
    name="azure-iot-nspkg",
    version="1.0.1",
    description="Microsoft Azure IoT Namespace Package [Internal]",
    long_description=_long_description,
    long_description_content_type="text/markdown",
    license="MIT License",
    author="Microsoft Corporation",
    author_email="opensource@microsoft.com",
    url="https://github.com/Azure/azure-iot-sdk-python-preview",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    install_requires=["azure-nspkg>=3.0.0"],
    packages=PACKAGES,
    zip_safe=False,
)
