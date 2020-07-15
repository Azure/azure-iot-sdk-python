# Advanced IoT Edge Scenario Samples for the Azure IoT Hub Device SDK

This directory contains samples showing how to use the various features of Azure IoT Hub Device SDK with Azure IoT Edge.

**Please note** that IoT Edge solutions are scoped to Linux containers and devices, documented [here](https://docs.microsoft.com/en-us/azure/iot-edge/tutorial-python-module#solution-scope). Please see [this blog post](https://techcommunity.microsoft.com/t5/internet-of-things/linux-modules-with-azure-iot-edge-on-windows-10-iot-enterprise/ba-p/1407066) to learn more about using Linux containers for IoT Edge on Windows devices. 

**These samples are written to run in Python 3.7+**, but can be made to work with Python 3.5 and 3.6 with a slight modification as noted in each sample:

```python
if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
```

In order to use these samples, they **must** be run from inside an Edge container.

## Included Samples
* [receive_message_on_input.py](receive_message_on_input.py) - Receive messages sent to an Edge module on a specific module input.
* [send_message.py](send_message.py) - Send multiple telmetry messages in parallel from an Edge module to the Azure IoT Hub or Azure IoT Edge.
* [send_message_to_output.py](send_message_to_output.py) - Send multiple messages in parallel from an Edge module to a specific output
* [send_message_downstream.py](send_message_downstream.py) - Send messages from a downstream or 'leaf' device to IoT Edge
