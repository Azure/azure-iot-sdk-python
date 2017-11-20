# Samples for the Azure IoT provisioning SDK for Python

This folder contains simple samples showing how to use the various features of the Microsoft Azure IoT Hub provisioning service from a device running Python.

## List of samples

* [Simple Sample](provisioning_device_client_sample.py): shows how to connect to IoT Hub and provvision a device.
* [Class Sample using AMQP](provisioning_device_client_sample_class.py): shows how to connect to IoT Hub with a ProvisioningManager class and provision a device.

## How to run the samples
In order to run the device samples you will first need the following prerequisites:
* [Setup your development environment][devbox-setup]
> Note: On Windows, it is recommended to install the **azure-iothub-provisioning-device-client** module package using pip (see link above).
* [Create an Azure IoT Hub instance][lnk-setup-iot-hub]
* [Create a provisioned device identity for your device][lnk-create-device-auth] and retreive the device ID for this device

Once you have a device identity for your sample,
* Get the sample files:
   * if you have cloned the repository, Navigate to the folder **provisioning_device_client/samples**
   * if you are using the azure-iothub-provisioning-device-client module installed with pip, download the samples folder content to your target.
* Run the sample application using the following command to run the simple sample (replacing `<id_scope>` with provisioning scope):
    ```
	provisioning_device_client_sample.py -i < id_scope > -s < TSM|X509 > -p < mqtt|http|amqp >
    ```
> You can get details on the options for the sample command line typing:
> `python provisioning_device_client_sample.py -h`
> `python provisioning_device_client_sample_class.py -h`

[lnk-setup-iot-hub]: https://aka.ms/howtocreateazureiothub
[lnk-create-device-auth]: ../../device/samples/readme.md
[devbox-setup]: ../../doc/python-devbox-setup.md