# Microsoft Azure IoT Libraries for Python

This is the Microsoft IoT namespace package.

This package is not intended to be installed directly by the end user.

Since Python 3.0, this is a Python 2.x package **only**, Python 3.x libraries will use [PEP420](https://www.python.org/dev/peps/pep-0420/) as a namespace package strategy. To avoid issues package servers that do not support `python_requires`, a Python 3.x package is installed, but is empty.

It provides the necessary files for other packages to extend the `azure.iot` namespace.