# Advanced IoT Edge Scenario Samples for the Azure IoT Hub Device SDK

This directory contains samples showing how to use the various features of Azure IoT Hub Device SDK with Azure IoT Edge.

**Please note** that IoT Edge solutions are scoped to Linux containers and devices, documented [here](https://docs.microsoft.com/en-us/azure/iot-edge/tutorial-python-module#solution-scope). Please see [this blog post](https://techcommunity.microsoft.com/t5/internet-of-things/linux-modules-with-azure-iot-edge-on-windows-10-iot-enterprise/ba-p/1407066) to learn more about using Linux containers for IoT Edge on Windows devices. 


In order to use these samples, they **must** be run from inside an Edge container.

## Included Samples
* [receive_data.py](receive_data.py) - Receive messages, twin patches, and method requests sent to an Edge module.
* [send_message.py](send_message.py) - Send multiple telmetry messages in parallel from an Edge module to the Azure IoT Hub or Azure IoT Edge.
* [send_message_to_output.py](send_message_to_output.py) - Send multiple messages in parallel from an Edge module to a specific output
* [send_message_downstream.py](send_message_downstream.py) - Send messages from a downstream or 'leaf' device to IoT Edge
