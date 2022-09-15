# Prepare your development environment

This document describes how to prepare your development environment to work with the Microsoft Azure IoT Device SDK for Python

## End User
If you are simply using the Microsoft Azure IoT SDK for Python as an end user and do not need to modify the code itself, you can simply install the package via `pip` as follows:

```
pip install azure-iot-device
```

## IoT Device SDK developer
If you are going to be modifying the codebase (likely because you are working as a developer on the Microsoft Azure IoT Device SDK for Python) you will need a few extras. Thankfully, you can prepare your development environment simply by running the following command **from the root**:

```
python scripts/env_setup.py
```

This will install not only relevant development and test dependencies, but also an editable install of the source code, which can then have any code changes immediately reflected in the install.

It is recommended to use [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/install.html) for Unix-based platforms or [virtualenvwrapper-win](https://github.com/davidmarble/virtualenvwrapper-win) for Windows, in order to easily manage custom environments and switch Python versions, however this is optional.

## Sample Environment Variables (Optional)

If you wish to follow the samples exactly as written, you will need to set some environment variables on your system. These are not required however - if you wish to use different environment variables, or no environment variables at all, simply change the samples to retrieve these values from elsewhere. Additionally, different samples use different variables, so you would only need the ones relevant to samples you intend to use.

### Connection String Device Authentication
* **IOTHUB_DEVICE_CONNECTION_STRING**: The connection string for your IoTHub Device, which can be found in the Azure Portal

### X509 Authentication
* **X509_CERT_FILE**: The path to the X509 certificate
* **X509_KEY_FILE**: The path to the X509 key
* **X509_PASS_PHRASE**: The pass phrase for the X509 key (Only necessary if cert has a password)

**This is an incomplete list of environment variables**


## E2E Testing Setup (Optional - SDK Developer)

If you wish to run end to end tests locally, you'll need to configure some additional environment variables:

* **IOTHUB_CONNECTION_STRING**: The connection string for your IoTHub (ideally iothubowner permissions)
* **EVENTHUB_CONNECTION_STRING**: The built-in Event Hub compatible endpoint of the above IoTHub

**NOTE**: if you wish to use dedicated E2E resources, you may also prefix the above variables with `IOTHUB_E2E_`

Additionally, you will need to add a messaging route with the following settings to the IoTHub in order for all tests to run correctly:
* Name: twin
* Endpoint: events
* Data Source: Device Twin Change Events
