# Microsoft Azure IoT service SDK for Python

Build service clients that communicate with Azure IoT Hub.

## Features

Use the service SDK to:
* Manage the device identity registry (CRUD operations for devices).
* Send messages to devices (C2D messages)
* interact with Device Twins and Invoke Device Direct Methods

## How to use the Azure IoT device SDK for Python

* [Check out the simple samples provided in this repository][samples]

## Samples
Whithin the repository, you can find various types of [simple samples][samples] that can help you get started.

## Directory structure

Service SDK subfolders under **/service**:

### /samples

Sample Python applications excercising Registry Manager and Messaging features.

### /src

C Source of the Python extension module. This module wraps the IoT Hub C Service SDK as extension module for Python. The C extension interface is specific to Boost Python and it does not work on other implementations.

### /tests

Python C extension module unit tests. The unit tests exercise a mocked Python extension module to test the Python interface. 

[samples]: samples/
