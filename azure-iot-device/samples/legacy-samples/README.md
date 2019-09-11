# Legacy Scenario Samples for the Azure IoT Hub Device SDK

This directory contains samples showing how to use the various features of Azure IoT Hub Device SDK with the Azure IoT Hub and Azure IoT Edge.

**These samples are legacy samples**, they use the sycnhronous API intended for use with Python 2.7 and 3.4, or in compatibility scenarios with later versions. We recommend you use the [asynchronous API instead](../advanced-hub-scenarios).


## IoTHub Device Samples
In order to use these samples, you **must** set your Device Connection String in the environment variable `IOTHUB_DEVICE_CONNECTION_STRING`.

* [send_message.py](send_message.py) - Send multiple telmetry messages in parallel from a device to the Azure IoT Hub.
    * You can monitor the Azure IoT Hub for messages received by using the following Azure CLI command:
        ```bash
        az iot hub monitor-events --hub-name <your IoT Hub name> --output table
        ```
* [receive_message.py](receive_message.py) - Receive Cloud-to-Device (C2D) messages sent from the Azure IoT Hub to a device.
    * In order to send a C2D message, use the following Azure CLI command:
        ```
        az iot device c2d-message send --device-id <your device id> --hub-name <your IoT Hub name> --data <your message here>
        ```
* [receive_direct_method.py](receive_direct_method.py) - Receive direct method requests on a device from the Azure IoT Hub and send responses back
    * In order to invoke a direct method, use the following Azure CLI command:
        ```
        az iot hub invoke-device-method --device-id <your device id> --hub-name <your IoT Hub name> --method-name <desired method>
        ```
* [receive_twin_desired_properties_patch](receive_twin_desired_properties_patch.py) - Receive an update patch of changes made to the device twin's desired properties
    * In order to send a update patch to a device twin's reported properties, use the following Azure CLI command:
        ```
        az iot hub device-twin update --device-id <your device id> --hub-name <your IoT Hub name> --set properties.desired.<property name>=<value>
        ```
* [update_twin_reported_properties](update_twin_reported_properties.py) - Send an update patch of changes to the device twin's reported properties
    * You can see the changes reflected in your device twin by using the following Azure CLI command:
        ```
        az iot hub device-twin show --device-id <your device id> --hub-name <yoru IoT Hub name>
        ```

## IoT Edge Module Samples
In order to use these samples, they **must** be run from inside an Edge container.

* [receive_message_on_input.py](receive_message_on_input.py) - Receive messages sent to an Edge module on a specific module input.
* [send_message_to_output.py](send_message_to_output.py) - Send multiple messages in parallel from an Edge module to a specific output

## DPS Samples

In order to use these samples, you **must** have the following environment variables :-

* PROVISIONING_HOST
* PROVISIONING_IDSCOPE
* PROVISIONING_REGISTRATION_ID

There are 2 ways that your device can get registered to the provisioning service differing in authentication mechanisms and another additional environment variable is needed to for the samples:-

* [register_symmetric_key.py](register_symmetric_key.py) - Register to provisioning service using a symmetric key. For this you must have the environment variable PROVISIONING_SYMMETRIC_KEY.
* [register_x509.py](register_x509.py) - Register to provisioning service using a symmetric key. For this you must have the environment variable X509_CERT_FILE, X509_KEY_FILE, PASS_PHRASE.
