# Microsoft Azure IoT service SDK for Python

Build service clients that communicate with Azure IoT Hub.

## Features

Use the service SDK to:
* Managing the device identity registry (CRUD operations for devices).
* Sending messages to devices (C2D messages)

## Application development guides
For more information on how to use this library refer to the documents below:
- [Prepare your Python development environment](../doc/get_started/python-devbox-setup.md)
- [Setup IoT Hub](../doc/setup_iothub.md)
- [Provision devices](../doc/manage_iot_hub.md)
- [Run a Python sample application](../doc/get_started/python-run-sample.md)

## Directory structure

Service SDK subfolders under **/service**:

### /samples

Sample Python applications excercising Registry Manager and Messaging features.

### /src

C Source of the Python extension module. This module wraps the IoT Hub C Service SDK as extension module for Python. The C extension interface is specific to Boost Python and it does not work on other implementations.

### /tests

Python C extension module unit tests. The unit tests exercise a mocked Python extension module to test the Python interface. 
