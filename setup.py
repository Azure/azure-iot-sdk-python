# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from setuptools import setup, find_namespace_packages
import re

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


filename = "azure-iot-device/azure/iot/device/constant.py"
version = None

with open(filename, "r") as fh:
    if not re.search("\n+VERSION", fh.read()):
        raise ValueError("VERSION  is not defined in constants.")

with open(filename, "r") as fh:
    for line in fh:
        if re.search("^VERSION", line):
            constant, value = line.strip().split("=")
            if not value:
                raise ValueError("Value for VERSION not defined in constants.")
            else:
                # Strip whitespace and quotation marks
                # Need to str convert for python 2 unicode
                version = str(value.strip(' "'))
            break

setup(
    name="azure-iot-device",
    version=version,
    description="Microsoft Azure IoT Device Library",
    license="MIT License",
    license_files=("LICENSE",),
    url="https://github.com/Azure/azure-iot-sdk-python/",
    author="Microsoft Corporation",
    author_email="opensource@microsoft.com",
    long_description=_long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    install_requires=[
        # Define sub-dependencies due to pip dependency resolution bug
        # https://github.com/pypa/pip/issues/988
        "urllib3>=2.2.2,<3.0.0",
        # Actual project dependencies
        "deprecation>=2.1.0,<3.0.0",
        "paho-mqtt>=1.6.1,<2.0.0",
        "requests>=2.32.3,<3.0.0",
        "requests-unixsocket2>=0.4.1",
        "janus",
        "PySocks",
        "typing_extensions",
    ],
    python_requires=">=3.8, <4",
    packages=find_namespace_packages(where="azure-iot-device"),
    package_data={"azure.iot.device": ["py.typed"]},
    package_dir={"": "azure-iot-device"},
    zip_safe=False,
)
