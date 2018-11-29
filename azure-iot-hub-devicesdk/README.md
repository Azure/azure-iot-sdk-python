
Azure IoT Hub Device SDK
========================

## Install

We currently do not provide a binary distribution of our package, which means you'll have to clone the repository.
Once you've cloned the repository, please run the `dev_setup.py` script to setup the environment and to be able to run
the samples.

## Quick start

The Device SDK provides client that let devices connect to an Azure IoT Hub instance. These clients needs to authenticate with IoT Hub,
and the easiest way to do that is using a device connection string which can be obtained from your Azure IoT Hub page in the [Azure Portal](https://portal.azure.com)

The Azure IoT Hub detailed docs that explain how to set up an Azure IoT hub and how to get keys can be found here:

[Azure IoT Hub Documentation](https://docs.microsoft.com/en-us/azure/iot-hub/)

## Samples

Sample code showing how to use the client can be find in the `samples` folder as well in this readme.
Our samples rely on having a connection string for the device set in an environment variable called `IOTHUB_DEVICE_CONNECTION_STRING`.

### Handling connectivity changes
```python
import os
from azure.iot.hub.devicesdk.device_client import DeviceClient
from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_connection_string

# The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")

# The "Authentication Provider" is the object in charge of creating authentication "tokens" for the device client.
auth_provider = from_connection_string(conn_str)

# For now, the SDK only supports MQTT as a protocol. the client object is used to interact with your Azure IoT hub.
# It needs an Authentication Provider to secure the communication with the hub, using either tokens or x509 certificates
device_client = DeviceClient.from_authentication_provider(auth_provider, "mqtt")

# The DeviceClient object will call its `on_connection_state` property every time the state of the client connection changes.
def connection_state_callback(status):
    print("connection status: " + status)
    if (status == 'connected'):
      device_client.disconnect()


device_client.on_connection_state = connection_state_callback
device_client.connect()

input("Press Enter at any time to quit...\n\n")

# This will print the following on the command line:
# connection status: connected
# connection status: disconnected
```

### Sending telemetry messages on a regular interval
```python
import os
from threading import Timer
from azure.iot.hub.devicesdk.device_client import DeviceClient
from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_connection_string

# The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
# The "Authentication Provider" is the object in charge of creating authentication "tokens" for the device client.
auth_provider = from_connection_string(conn_str)
# For now, the SDK only supports MQTT as a protocol. the client object is used to interact with your Azure IoT hub.
# It needs an Authentication Provider to secure the communication with the hub, using either tokens or x509 certificates
device_client = DeviceClient.from_authentication_provider(auth_provider, "mqtt")


# This function will be called by a timer on a regular basis, once connected
def send_payload():
  print("sending!")
  device_client.send_event("test_payload")
  start_sender()

def start_sender():
  # This defines a timer that fires after 5 seconds
  global event_sender
  event_sender = Timer(5.0, send_payload)
  event_sender.start()

def cancel_sender():
  event_sender.cancel()

# The connection state callback allows us to detect when the client is connected and disconnected:
def connection_state_callback(status):
    print("connection status: " + status)
    if (status == "connected"):
      start_sender()
    elif (status == "disconnected"):
      cancel_sender()

# Register the connection state callback with the client...
device_client.on_connection_state = connection_state_callback
# ... and connect the client. The timer will start when the client reaches the connected state.
device_client.connect()

input("Press Enter to exit at any time...\n\n")
cancel_sender()
```

### Getting help and finding API docs

Our SDK makes use of docstrings which means you can find our help directly from the Python Command Line Interface:

From your terminal/shell:
```
$ python
```

Within the Python CLI:
```
>>> help()
```

Then within the help CLI itself, type the name of the module or class for which you'd like to see the docs, eg:
```
help> azure.iot.hub.devicesdk.device_client
```