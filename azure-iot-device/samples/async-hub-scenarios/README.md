# Advanced IoT Hub Scenario Samples for the Azure IoT Hub Device SDK

This directory contains samples showing how to use the various features of Azure IoT Hub Device SDK with the Azure IoT Hub.

**These samples are written to run in Python 3.7+**, but can be made to work with Python 3.5 and 3.6 with a slight modification as noted in each sample:

```python
if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
```

## Included Samples

### IoTHub Samples

In order to use these samples, you **must** set your Device Connection String in the environment variable `IOTHUB_DEVICE_CONNECTION_STRING`.

* [send_message.py](send_message.py) - Send multiple telmetry messages in parallel from a device to the Azure IoT Hub.
  * You can monitor the Azure IoT Hub for messages received by using the following Azure CLI command:

    ```bash
    az iot hub monitor-events --hub-name <your IoT Hub name> --output table
    ```

* [receive_message.py](receive_message.py) - Receive Cloud-to-Device (C2D) messages sent from the Azure IoT Hub to a device.
  * In order to send a C2D message, use the following Azure CLI command:

    ```bash
    az iot device c2d-message send --device-id <your device id> --hub-name <your IoT Hub name> --data <your message here>
    ```

* [receive_direct_method.py](receive_direct_method.py) - Receive direct method requests on a device from the Azure IoT Hub and send responses back
  * In order to invoke a direct method, use the following Azure CLI command:

    ```bash
    az iot hub invoke-device-method --device-id <your device id> --hub-name <your IoT Hub name> --method-name <desired method>
    ```

* [receive_twin_desired_properties_patch](receive_twin_desired_properties_patch.py) - Receive an update patch of changes made to the device twin's desired properties
  * In order to send a update patch to a device twin's reported properties, use the following Azure CLI command:

    ```bash
    az iot hub device-twin update --device-id <your device id> --hub-name <your IoT Hub name> --set properties.desired.<property name>=<value>
    ```

* [update_twin_reported_properties](update_twin_reported_properties.py) - Send an update patch of changes to the device twin's reported properties
  * You can see the changes reflected in your device twin by using the following Azure CLI command:

    ```bash
    az iot hub device-twin show --device-id <your device id> --hub-name <yoru IoT Hub name>
    ```

### DPS Samples

#### Individual Enrollment

In order to use these samples, you **must** have the following environment variables :-

* PROVISIONING_HOST
* PROVISIONING_IDSCOPE
* PROVISIONING_REGISTRATION_ID

There are 2 ways that your device can get registered to the provisioning service differing in authentication mechanisms. Depending on the mechanism used additional environment variables are needed for the samples:-

* [provision_symmetric_key.py](provision_symmetric_key.py) - Provision a device to IoTHub by registering to the Device Provisioning Service using a symmetric key, then send telemetry messages to IoTHub. For this you must have the environment variable PROVISIONING_SYMMETRIC_KEY.
* [provision_symmetric_key_with_payload.py](provision_symmetric_key_with_payload.py) - Provision a device to IoTHub by registering to the Device Provisioning Service using a symmetric key while supplying a custom payload, then send telemetry messages to IoTHub. For this you must have the environment variable PROVISIONING_SYMMETRIC_KEY.
* [provision_x509.py](provision_x509.py) - Provision a device to IoTHub by registering to the Device Provisioning Service using a symmetric key, then send a telemetry message to IoTHub. For this you must have the environment variable X509_CERT_FILE, X509_KEY_FILE, PASS_PHRASE.


#### Group Enrollment

In order to use these samples, you **must** have the following environment variables :-

* PROVISIONING_HOST
* PROVISIONING_IDSCOPE

* [provision_symmetric_key_group.py](provision_symmetric_key_group.py) - Provision multiple devices to IoTHub by registering them to the Device Provisioning Service using derived symmetric keys, then send telemetry to IoTHub from these devices. For this you must have knowledge of the group symmetric key and must have the environment variables PROVISIONING_DEVICE_ID_1, PROVISIONING_DEVICE_ID_2, PROVISIONING_DEVICE_ID_3.
  * NOTE : Group symmetric key must NEVER be stored and all the device keys must be computationally derived prior to using this sample.