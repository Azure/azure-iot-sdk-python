# Downstream (leaf) scenarios involving using the Azure IoT Hub Device SDK

This directory contains samples showing how to use the various features of Azure IoT Hub Device SDK in a device that is 'downsteam' (or is a 'leaf' device) behind an IoT Edge gateway.

**These samples are written to run in Python 3.7+**, but can be made to work with Python 3.5 and 3.6 with a slight modification as noted in each sample:

```python
if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
```

## Prerequisites
* your connection string must contain the optional GatewayHostName parameter (or modified HostName parameter) that points to your IoT Edge gateway as described [here](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-authenticate-downstream-device#retrieve-and-modify-connection-string)
* your IoT Edge gateway **must** be set up as a [transparent gateway](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-create-transparent-gateway)
* the root ca certificate (public) used to set up your IoT Edge device must be available on your downstream device in PEM format
  * if you used our '[convenience scripts](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-create-test-certificates)', this will be the azure-iot-test-only.root.ca.cert.pem file

## Running the samples

It is not recommended to have connection strings and other secrets hardcoded in an application.  For simplicity, these samples accept their configuration parameters in environment variables

To run the samples, you need to set two environment variables:
* IOTHUB_DEVICE_CONNECTION_STRING  -  the connection string for your downstream IoT Device from IoT Hub (including the Gateway information)
* IOTEDGE_ROOT_CA_CERT_PATH - the file path to the root ca certificate pem file mentioned above

For example, on Linux you can run:

```bash

export IOTHUB_DEVICE_CONNECTION_STRING="<your connection string here>"
export IOTEDGE_ROOT_CA_CERT_PATH="<path to your root ca pem file>"

python3 <path to sample *.py file>

```

For Windows, replace 'export' with 'set' in the commands above

## Included Samples
* [send_message_downstream.py](send_message_downstream.py) - Send multiple messages in parallel from an Edge module to a specific output
