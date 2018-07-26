# Microsoft Azure IoT device SDK for Python

The Azure IoT device SDK for Python allows to build devices that communicate with Azure IoT Hub.

## Features

Use the device SDK to:
* Send event data to Azure IoT Hub.
* Receive messages from IoT Hub.
* Communicate with the service via AMQP, MQTT or HTTP.
* Synchronize an Azure IoT Hub device Twin with Azure IoT Hub from a device
* Implement Azure IoT Hub Direct Device Methods on devices
* Implement Azure IoT Device Mangement features on devices

## How to use the Azure IoT device SDK for Python

* [Check out the simple samples provided in this repository][samples]

## Samples
Whithin the repository, you can find various types of [simple samples][samples] that can help you get started.

## Directory structure

Device SDK subfolders under **device**:

### /iothub_client_python

C Source of the Python extension module. This module wraps the IoT Hub C SDK as extension module for Python. The C extension interface is specific to Boost Python and it does not work on other implementations.

### /samples

Sample Python applications excercising basic features using AMQP, MQTT and HTTP.

### /tests

Python C extension module unit tests. The unit tests exercise a mocked Python extension module to test the Python interface. 

[samples]: samples/
