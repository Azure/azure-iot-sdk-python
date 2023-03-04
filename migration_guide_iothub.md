# Azure IoT Device SDK for Python Migration Guide - IoTHubDeviceClient and IoTHubModuleClient

This guide details how to update existing code that uses an `azure-iot-device` V2 release to use a V3 release instead. While the APIs remain mostly the same, there are several differences you will need to account for in your application, as some APIs have changed, and we have removed some of the implicit behaviors present in V2 in order to provide a more reliable and consistent user experience.

Note that this guide mostly refers to the `IoTHubDeviceClient`, although it's contents apply equally to the `IoTHubModuleClient`.

For changes to the `ProvisioningDeviceClient` please refer to `migration_guide_provisioning.md` in this same directory.

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
| Method Requests                 | `.on_method_request_received`                | `.start_direct_method_request_receive()`         | `.stop_direct_method_request_receive()`         |
| Twin Desired Properties Patches | `.on_twin_desired_properties_patch_received` | `.start_twin_desired_properties_patch_receive()` | `.stop_twin_desired_properties_patch_receive()` |


Finally, it should be clarified that the following receive APIs that were deprecated in V2 have been fully removed in V3:
* `.receive_message()`
* `.receive_message_on_input()`
* `.receive_method_request()`
* `.receive_twin_desired_properties_patch()`

All receives should now be done using the handlers in the table above.


## Direct Methods
For clarity, all references to direct methods are now explicit about being "direct methods", rather than the more generic (and overloaded) "method". As such, the following methods and objects have all had a name change:
* `.invoke_method()` -> `.invoke_direct_method()`
* `MethodRequest` -> `DirectMethodRequest`
* `MethodResponse` -> `DirectMethodResponse`


## Message object

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


## Shutting down
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


## Symmetric Key Authentication
Creating a client that uses a symmetric key to authenticate is now done via the new `.create()` factory method instead of `.create_from_symmetric_key()`

### V2
```python
from azure.iot.device import IoTHubDeviceClient

client = IoTHubDeviceClient.create_from_symmetric_key(
    symmetric_key="<Your Symmetric Key>",
    hostname="<Your Hostname>",
    device_id="<Your Device ID>"
)
```

### V3
```python
from azure.iot.device import IoTHubDeviceClient

client = IoTHubDeviceClient.create(
    symmetric_key="<Your Symmetric Key>",
    hostname="<Your Hostname>",
    device_id="<Your Device ID>"
)
```

## Custom SAS Token Authentication
There have been significant changes surrounding this style of authentication - it was rather complex in V2, and we have tried to simplify it for V3. It now also uses the new `.create()` method rather than `.create_from_sastoken()`. With this new style of providing a custom token via callback, you no longer
will have to manually update the SAS token via the `.on_new_sastoken_required` handler, and as such,
the handler no longer exists.

### V2
```python
from azure.iot.device import IoTHubDeviceClient

def get_new_sastoken():
    sastoken = # Do something here to create/retrieve a token
    return sastoken

sastoken = get_new_sastoken()
client = IoTHubDeviceClient.create_from_sastoken(sastoken)

def sastoken_update_handler():
    print("Updating SAS Token...")
    sastoken = get_new_sastoken()
    client.update_sastoken(sastoken)
    print("SAS Token updated")

client.on_new_sastoken_required = sastoken_update_handler
```

### V3
```python
from azure.iot.device import IoTHubDeviceClient

def get_new_sastoken():
    sastoken = # Do something here to create/retrieve a token
    return sastoken

client = IoTHubDeviceClient.create(
    hostname="<Your Hostname>",
    device_id="<Your Device ID>",
    sastoken_fn=get_new_sastoken,
)
```

## X509 Authentication
Using X509 authentication is now provided via the new `ssl_context` keyword for the `.create()` method, rather than having it's own `.create_from_x509_certificate()` method. This is to allow additional flexibility for customers who wish for more control over their TLS/SSL authorization. See "TLS/SSL customization" below for more information.

### V2
```python
from azure.iot.device import IoTHubDeviceClient, X509

x509 = X509(
    cert_file="<Your X509 Cert File Path>",
    key_file="<Your X509 Key File>",
    pass_phrase="<Your X509 Pass Phrase>",
)

client = IoTHubDeviceClient.create_from_x509_certificate(
    hostname="<Your IoTHub Hostname>",
    device_id="<Your Device ID>",
    x509=x509,
)
```

### V3
```python
from azure.iot.device import IoTHubDeviceClient
import ssl

ssl_context = ssl.SSLContext.create_default_context()
ssl_context.load_cert_chain(
    certfile="<Your X509 Cert File Path>",
    keyfile="<Your X509 Key File>",
    password="<Your X509 Pass Phrase>",
)

client = IoTHubDeviceClient.create(
    hostname="<Your IoTHub Hostname>",
    device_id="<Your Device ID>",
    ssl_context=ssl_context,
)
```

Note that SSLContexts can be used with the  `.create_from_connection_string()` factory method as well, so V3 now fully supports X509 connection strings.
### V3
```python
from azure.iot.device import IoTHubDeviceClient
import ssl

ssl_context = ssl.SSLContext.create_default_context()
ssl_context.load_cert_chain(
    certfile="<Your X509 Cert File Path>",
    keyfile="<Your X509 Key File>",
    password="<Your X509 Pass Phrase>",
)

client = IoTHubDeviceClient.create_from_connection_string(
    "<Your X509 Connection String>",
    ssl_context=ssl_context,
)
```

## TLS/SSL Customization
To allow users more flexibility, we have added the ability to inject an `SSLContext` object into the client via the optional `ssl_context` keyword argument to factory methods in order to customize the TLS/SSL encryption and authentication. As a result, some features previously handled via client APIs are now expected to have been directly set on the injected `SSLContext`.

By moving to a model that allows `SSLContext` injection we not only bring our client in line with standard practices, but we also allow for users to modify any aspect of their `SSLContext`, not just the ones we previously supported via API.

### **Server Verification Certificates (CA certs)**
### V2
```python
from azure.iot.device import IoTHubDeviceClient

certfile = open("<Your CA Certificate File Path>")
root_ca_cert = certfile.read()

client = IoTHubDeviceClient.create_from_connection_string(
    "<Your Connection String>",
    server_verification_cert=root_ca_cert
)
```

### V3
```python
from azure.iot.device import IoTHubDeviceClient
import ssl

ssl_context = ssl.SSLContext.create_default_context(
    cafile="<Your CA Certificate File Path>",
)

client = IoTHubDeviceClient.create_from_connection_string(
    "<Your Connection String>",
    ssl_context=ssl_context,
)
```

### **Cipher Suites**
### V2
```python
from azure.iot.device import IoTHubDeviceClient

client = IoTHubDeviceClient.create_from_connection_string(
    "<Your Connection String>",
    cipher="<Your Cipher>"
)
```

### V3
```python
from azure.iot.device import IoTHubDeviceClient
import ssl

ssl_context = ssl.SSLContext.create_default_context()
ssl_context.set_ciphers("<Your Cipher>")

client = IoTHubDeviceClient.create_from_connection_string(
    "<Your Connection String>",
    ssl_context=ssl_context,
)
```

## Modified Client Options

Some keyword arguments provided at client creation have changed or been removed

| V2                          | V3               | Explanation                                              |
|-----------------------------|------------------|----------------------------------------------------------|
| `connection_retry`          | `auto_reconnect` | Improved clarity                                         |
| `connection_retry_interval` | **REMOVED**      | Automatic reconnect no longer uses a static interval     |
| `auto_connect`              | **REMOVED**      | Initial manual connection now required                   |
| `ensure_desired_properties` | **REMOVED**      | No more implicit twin updates                            |
| `sastoken_ttl`              | **REMOVED**      | Unnecessary, but open to re-adding if a use case emerges |
| `gateway_hostname`          | **REMOVED**      | Supported via `hostname` parameter                       |
| `server_verification_cert`  | **REMOVED**      | Supported via SSL injection                              |
| `cipher`                    | **REMOVED**      | Supported via SSL injection                              |
