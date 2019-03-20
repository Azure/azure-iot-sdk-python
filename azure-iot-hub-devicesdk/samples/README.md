# Samples for the Azure IoT Hub Device SDK

This directory contains simple samples showing how to use the various features of the Microsoft Azure IoT Hub service from a device running Python

## List of Samples

* Send Telemetry from a Device
* Receive Cloud-to-Device (C2D) messages on a Device
* Receive Input messages on a Module
* Send to Output from Module
* Use a variety of authentication providers to instantiate a client

## How to run the samples
Our Device samples rely on having a Device Connection String set in an environment variable called `IOTHUB_DEVICE_CONNECTION_STRING`.

Our Module samples must be run from inside an IoT Edge module in order to authenticate.