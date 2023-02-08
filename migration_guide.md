# IoTHub Python SDK Migration Guide

This guide details how to update existing code that uses an `azure-iot-device` V2 release to use a V3 release instead. While the APIs remain mostly the same, there are a few differences you may need to account for in your application, as we have removed some of the implicit behaviors present in V2 in order to provide a more reliable and consistent user experience.

## Connecting to IoTHub
One of the primary changes in V3 is the removal of automatic connections when invoking other APIs on the `IoTHubDeviceClient` and `IoTHubModuleClient`. You must now make an explicit manual connection before sending or receiving any data.

### V2
```python
from azure.iot.device import IoTHubDeviceClient

client = IoTHubDeviceClient.create_from_connection_string("<Your Connection String>")
client.send_message("some message")
```

### V3
```python
from azure.iot.device import IoTHubDeviceClient

client = IoTHubDeviceClient.create_from_connection_string("<Your Connection String>")
client.connect()
client.send_message("some message")
```

Note that many people using V2 may already have been doing manual connects, as for some time, this has been our recommended practice.

Note also that this change does *not* affect automatic reconnection attempts in the case of network failure. Once the manual connect has been successful, the client will (under default settings) still attempt to retain that connected state as it did in V2.


## Receiving data from IoTHub
Similarly to the above, there is an additional explicit step you must now make when trying to receive data. In addition to setting your handler, you must explicitly start/stop receiving. Note also that the above step of manually connecting must also be done before starting to receive data.

Furthermore, note that the content of the message is now referred to by the 'payload' attribute on the message, rather than the 'data' attribute (see "Message" section below)

### V2
```python
from azure.iot.device import IoTHubDeviceClient

client = IoTHubDeviceClient.create_from_connection_string("<Your Connection String>")

# define behavior for receiving a message
def message_handler(message):
    print("the data in the message received was ")
    print(message.data)
    print("custom properties are")
    print(message.custom_properties)

# set the message handler on the client
client.on_message_received = message_handler
```

### V3
```python
from azure.iot.device import IoTHubDeviceClient

client = IoTHubDeviceClient.create_from_connection_string("<Your Connection String>")

# define behavior for receiving a message
def message_handler(message):
    print("the payload of the message received was ")
    print(message.payload)
    print("custom properties are")
    print(message.custom_properties)

# set the message handler on the client
client.on_message_received = message_handler

# connect and start receiving messages
client.connect()
client.start_message_receive()
```

Note that this must be done not just for receiving messages, but receiving any data. Consult the chart below to see which APIs you will need for the type of data you are receiving.


| Data Type                       | Handler name                                 | Start Receive API                                | Stop Receive API                                |
|---------------------------------|----------------------------------------------|--------------------------------------------------|-------------------------------------------------|
| Messages                        | `.on_message_received`                       | `.start_message_receive()`                       | `.stop_message_receive()`                       |
| Method Requests                 | `.on_method_request_received`                | `.start_method_request_receive()`                | `.stop_method_request_receive()`                |
| Twin Desired Properties Patches | `.on_twin_desired_properties_patch_received` | `.start_twin_desired_properties_patch_receive()` | `.stop_twin_desired_properties_patch_receive()` |


Finally, it should be clarified that the following receive APIs that were deprecated in V2 have been fully removed in V3:
* `.receive_message()`
* `.receive_message_on_input()`
* `.receive_method_request()`
* `.receive_twin_desired_properties_patch()`

All receives should now be done using the handlers in the table above.


## Message object - IoTHubDeviceClient/IoTHubModuleClient

Some changes have been made to the `Message` object used for sending and receiving data.
* The `.data` attribute is now called `.payload` for consistency with other objects in the API
* The `message_id` parameter is no longer part of the constructor arguments. It should be manually added as an attribute, just like all other attributes
* The payload of a received Message is now a unicode string value instead of a bytestring value.
It will be decoded according to the content encoding property sent along with the message.

### V2
```python
from azure.iot.device import Message

payload = "this is a payload"
message_id = "1234"
m = Message(data=payload, message_id=message_id)

assert m.data == payload
assert m.message_id = message_id
```

### V3
```python
from azure.iot.device import Message

payload = "this is a payload"
message_id = "1234"
m = Message(payload=payload)
m.message_id = message_id

assert m.payload == payload
```

## Modified Client Options - IoTHubDeviceClient/IoTHubModuleClient

Some keyword arguments provided at client creation have changed or been removed

| V2                          | V3          | Explanation                            |
|-----------------------------|-------------|----------------------------------------|
| `auto_connect`              | **REMOVED** | Initial manual connection now required |
| `ensure_desired_properties` | **REMOVED** | No more implicit twin updates          |


## Shutting down - IoTHubDeviceClient/IoTHubModuleClient

While using the `.shutdown()` method when you are completely finished with an instance of the client has been a highly recommended practice for some time, some early versions of V2 did not require it. As of V3, in order to ensure a graceful exit, you must make an explicit shutdown.

### V2
```python
from azure.iot.device import IoTHubDeviceClient

client = IoTHubDeviceClient.create_from_connection_string("<Your Connection String>")

# ...
#<do things>
# ...
```

### V3
```python
from azure.iot.device import IoTHubDeviceClient

client = IoTHubDeviceClient.create_from_connection_string("<Your Connection String>")

# ...
#<do things>
# ...

client.shutdown()
```


## Shutting down - ProvisioningDeviceClient

As with the IoTHub clients mentioned above, the Provisioning clients now also require shutdown. This was implicit in V2, but now it must be explicit and manual to ensure graceful exit.

### V2
```python
from azure.iot.device import ProvisioningDeviceClient

client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host="<Your provisioning host>",
        registration_id="<Your registration id>",
        id_scope="<Your id scope>",
        symmetric_key="<Your symmetric key">,
    )

registration_result = client.register()

# Shutdown is implicit upon successful registration
```

### V3
```python
from azure.iot.device import ProvisioningDeviceClient

client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host="<Your provisioning host>",
        registration_id="<Your registration id>",
        id_scope="<Your id scope>",
        symmetric_key="<Your symmetric key">,
    )

registration_result = client.register()

# Manual shutdown for graceful exit
client.shutdown()
```