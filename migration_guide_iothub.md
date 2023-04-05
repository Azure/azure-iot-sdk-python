# Azure IoT Device SDK for Python Migration Guide - IoTHubDeviceClient/IoTHubModuleClient -> IoTHubSession

This guide details how to update existing code for IoT Hub that uses an `azure-iot-device` V2 release to use a V3 release instead.

**Note that currently V3 only presents an async set of APIs. This guide will be updated when that changes**

For changes when using the Device Provisioning Service, please refer to `migration_guide_provisioning.md` in this same directory.

The design goals for V3 were to make a more stripped back, simple API surface that allows for a greater flexibility for the end user, as well as improved reliability and clarity. We have attempted to remove as much implicit behavior as possible in order to give full control of functionality to the end user. Additionally, we have attempted to make the experience of using the API simpler to address common pitfalls, and make applications easier to write.

## Connection Management
The most significant change in V3 is the removal of manual connection/disconnection. Connections are now managed automatically by a context manager.

#### V2
```python
from azure.iot.device.aio import IoTHubDeviceClient

async def main():
    client = IoTHubDeviceClient.create_from_connection_string("<Your Connection String>")
    await client.connect()
    # <do things>
    await client.disconnect()
```

#### V3
```python
from azure.iot.device import IoTHubSession

async def main():
    async with IoTHubSession.from_connection_string("<Your Connection String>") as session:
        # <do things>
```

When the context manager is entered, a connection will be established before running the block of code inside the context manager. After the block is done executing, a disconnection will occur upon context manager exit. You can consider that all code within the block is written with the expectation of a connection, as the context manager
represents a connection to the IoT Hub.


## Outgoing Operations
Initiating an operation works similarly to before, but now must be done within the block of the Session context manager. APIs will fail during invocation if they are not called from within the context manager. In the following example, we send a telemetry message, but the structure applies to any kind of operation

#### V2
```python
from azure.iot.device.aio import IoTHubDeviceClient

async def main():
    client = IoTHubDeviceClient.create_from_connection_string("<Your Connection String>")
    await client.connect()

    await client.send_message("hello world")

    await client.disconnect()
```

#### V3
```python
from azure.iot.device import IoTHubSession

async def main():
    async with IoTHubSession.from_connection_string("<Your Connection String>") as session:
        await session.send_message("hello world")
```

Some of the APIs for operations have been changed. The following table illustrates how to use each operation from the V2 SDK in V3.

| Operation Type              | IoTHubDeviceClient API (V2)         | IoTHubModuleClient API (V2)         | IoTHubSession API (V3)           |
|-----------------------------|-------------------------------------|-------------------------------------|----------------------------------|
| Send Telemetry Message      | `.send_message()`                   | `.send_message()`                   | `.send_message()`                |
| Send Routed Message         | **N/A**                             | `.send_message_to_output()`         | **NOT YET AVAILABLE**            |
| Send Direct Method Response | `.send_method_response()`           | `.send_method_response()`           | `.send_direct_method_response()` |
| Update Reported Properties  | `.patch_twin_reported_properties()` | `.patch_twin_reported_properties()` | `.update_reported_properties()`  |
| Get Twin                    | `.get_twin()`                       | `.get_twin()`                       | `.get_twin()`                    |
| Get Blob Storage Info       | `.get_storage_info_for_blob()`      | **N/A**                             | **NOT YET AVAILABLE**            |
| Notify Blob Upload Status   | `.notify_blob_upload_status()`      | **N/A**                             | **NOT YET AVAILABLE**            |
| Invoke Direct Method        | **N/A**                             | `.invoke_method()`                  | **NOT YET AVAILABLE**            |


## Incoming Data
Incoming data receives are now implemented with a context manager and asynchronous iterator rather than using callbacks. In the following example we use incoming IoT Hub messages, but the syntax applies to any kind of received data.

#### V2
```python
from azure.iot.device.aio import IoTHubDeviceClient

async def main():
    client = IoTHubDeviceClient.create_from_connection_string("<Your Connection String>")

    # define behavior for receiving a message
    def message_handler(message):
        print("the data in the message received was ")
        print(message.data)
        print("custom properties are")
        print(message.custom_properties)

    # set the message handler on the client
    client.on_message_received = message_handler

    await client.connect()

    # Loop until program is terminated
    while True:
        await asyncio.sleep(1)
```

#### V3
```python
from azure.iot.device import IoTHubSession

async def main():
    async def main():
    async with IoTHubSession.from_connection_string("<Your Connection String>") as session:
        async with session.messages() as messages:
            async for message in messages:
                print("the data in the message received was ")
                print(message.payload)
                print("custom properties are")
                print(message.custom_properties)
```

Similar to managing a the connection with a context manager, in this example the `session.messages()` context manager will enable receiving IoT Hub messages upon entry, and disable receiving them upon exit, ensuring you are only receiving data when you wish to. If the outer `IoTHubSession` context manager represents the duration of a connection to an IoT Hub, then this `session.messages()` context manager represents the duration of receiving a specific data type from an IoT Hub.

The context manager returns `messages` in this example, an asynchronous iterator, which can be iterated over as messages are received, asynchronously suspending iteration until one arrives. You can think of the code inside this loop as being the same as the code that would have previously been put inside a callback in V2.

The following table indicates how use the various data receives from the V2 SDK in V3, as not only is the programming model different, but some of the names have changed.

| Incoming Data Type       |  IoTHubDeviceClient Callback (V2)            | IoTHubModuleClient Callback (V2)             | IoTHubSession Context Manager (V3) |
|--------------------------|----------------------------------------------|----------------------------------------------|------------------------------------|
| C2D Messages             | `.on_message_received`                       | **N/A**                                      | `.messages()`                      |
| Input Messages           | **N/A**                                      | `.on_message_received`                       | **NOT YET AVAILABLE**              |
| Direct Method Requests   | `.on_method_request_received`                | `.on_method_request_received`                | `.direct_method_requests()`        |
| Desired Property Updates | `.on_twin_desired_properties_patch_received` | `.on_twin_desired_properties_patch_received` | `.desired_property_updates()`      |

Note that some of the data objects themselves have also been slightly changed for V3. Refer to the sections on Message Objects and Direct Method Objects for more information.

## Responding to Network Failure

In the V2 IoTHubDeviceClient and IoTHubModuleClient, the default behavior was to try and re-establish connections that failed. In the V3 `IoTHubSession`, not only is this not the default behavior, but this behavior is not supported at all. In order to provide flexibility surrounding reconnect scenarios, we have changed the design to put control in the hands of the end user. No longer will there be any confusion as to the connection state - it will be directly and clearly reported. No longer are there implicit reconnect attempts that happen without user knowledge.

To reconnect after a connection drop, simply wrap your `IoTHubSession` usage in a try/except block. All outgoing operation APIs, as well incoming data generators will raise `MQTTError` upon a lost connection, so you can catch that, and respond with a reconnect attempt

Additionally, in the case where you cannot connect, the `IoTHubSession` context manager itself will raise `MQTTConnectionFailedError`, which you can catch and respond to with a reconnect attempt.

In the following example, we attempt to connect and wait for incoming C2D messages. If we are connected and the connection is dropped, a reconnect attempt will be made after 5 seconds. If we attempt to reconnect and fail doing so, we will try again after 10 seconds.

#### V3
```python
from azure.iot.device import IoTHubSession, MQTTError, MQTTConnectionFailedError

async def main():
    while True:
        try:
            async with IoTHubSession.from_connection_string("<Your Connection String>") as session:
                async with session.messages() as messages:
                    async for message in messages:
                        print(message.payload)
        except MQTTError:
            print("Connection was lost. Trying again in 5 seconds")
            await asyncio.sleep(5)
        except MQTTConnectionFailedError:
            print("Could not connect. Trying again in 10 seconds")
            await asyncio.sleep(10)
```

This does result in a slight increase in complexity over V2 where all of this logic was hidden internally in the clients, but we feel as though this will end up being simpler to use, as connection loss will always result in a thrown exception, immediately identifying the problem. Furthermore, this will eliminate any clashes between user-initiated connects, and implicit reconnection attempts by making the end user the authority on controlling the connection in all respects.

## SAS (Shared Access Signature) Authentication

Several types of IoT Hub authentication use SAS (Shared Access Signature) tokens. In V2 these all had their own factory methods. In V3 this has been changed. Additionally, significant changes have been made regarding credential expiration.

### Connection String
Connection string based SAS authentication functions the same as it did before, although the factory method has been renamed. Use `.from_connection_string()` with V3 instead of the old `.create_from_connection_string()` method.

### Shared Access Key / Symmetric Key
Creating a client that uses a shared access key to authenticate is now done via the `IoTHubSession` constructor directly, instead of the old `.create_from_symmetric_key()` method.

#### V2
```python
from azure.iot.device.aio import IoTHubDeviceClient

client = IoTHubDeviceClient.create_from_symmetric_key(
    symmetric_key="<Your Shared Access Key>",
    hostname="<Your Hostname>",
    device_id="<Your Device ID>"
)
```

#### V3
```python
from azure.iot.device import IoTHubSession

session = IoTHubSession(
    hostname="<Your Hostname>",
    device_id="<Your Device ID>",
    shared_access_key="<Your Shared Access Key>",
)
```

### Custom SAS Token
This feature is currently not yet fully supported on V3. It will be soon.

### SAS Token expiration

In the past, the V2 SDKs engaged in "SAS Token renewal", when using SAS authentication types. What this meant, was that when a SAS token being used as a credential was about to expire, the client would either generate a new one, or ask for a new one, depending on the specific type of SAS auth. Then, the client would implicitly disconnect from the IoTHub and then connect once more with the new credential.

This was somewhat problematic, as it once again introduced implicit behavior that affected the connection, and in the case where something went wrong, there was no easy way to report it. Furthermore, even if the user had specified they wanted to manage the connection themselves, turning off both auto-connect, and auto-reconnect behaviors, these implicit reconnects still would need to occur.

For V3 we have decided to simply not do this. When a SAS token expires, the connection will be dropped. This brings the behavior in line with how X509 certificates behave - when they expire, the connection will be dropped (raising `MQTTError`, same as any other connection loss), and you should re-instantiate the `IoTHubSession` object, just the same as you would respond to any other connection loss.

As a result, the example from the "Network Failure" section above also handles SAS expiration.

You can still customize the lifespan of generated SAS tokens by providing the optional `sastoken_ttl` keyword argument when instantiating an `IoTHubSession` object, either directly with the constructor, or with a factory method.


## X509 Certificate Authentication
Using X509 authentication is now provided via the new `ssl_context` keyword for the `IoTHubSession` constructor, rather than having it's own `.create_from_x509_certificate()` method. This is to allow additional flexibility for customers who wish for more control over their TLS/SSL authorization. See "TLS/SSL customization" below for more information.

#### V2
```python
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import X509

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

#### V3
```python
from azure.iot.device import IoTHubSession
import ssl

ssl_context = ssl.SSLContext.create_default_context()
ssl_context.load_cert_chain(
    certfile="<Your X509 Cert File Path>",
    keyfile="<Your X509 Key File>",
    password="<Your X509 Pass Phrase>",
)

client = IoTHubSession(
    hostname="<Your IoTHub Hostname>",
    device_id="<Your Device ID>",
    ssl_context=ssl_context,
)
```

Note that SSLContexts can be used with the  `.from_connection_string()` factory method as well, so V3 now fully supports X509 connection strings.

#### V3
```python
from azure.iot.device import IoTHubSession
import ssl

ssl_context = ssl.SSLContext.create_default_context()
ssl_context.load_cert_chain(
    certfile="<Your X509 Cert File Path>",
    keyfile="<Your X509 Key File>",
    password="<Your X509 Pass Phrase>",
)

client = IoTHubSession.from_connection_string(
    "<Your X509 Connection String>",
    ssl_context=ssl_context,
)
```

## TLS/SSL Customization
To allow users more flexibility, we have added the ability to inject an `SSLContext` object into the client via the optional `ssl_context` keyword argument to factory methods in order to customize the TLS/SSL encryption and authentication. As a result, some features previously handled via client APIs are now expected to have been directly set on the injected `SSLContext`.

By moving to a model that allows `SSLContext` injection we not only bring our client in line with standard practices, but we also allow for users to modify any aspect of their `SSLContext`, not just the ones we previously supported via API.

### Server Verification Certificates (CA certs)
#### V2
```python
from azure.iot.device.aio import IoTHubDeviceClient

certfile = open("<Your CA Certificate File Path>")
root_ca_cert = certfile.read()

client = IoTHubDeviceClient.create_from_connection_string(
    "<Your Connection String>",
    server_verification_cert=root_ca_cert
)
```

#### V3
```python
from azure.iot.device import IoTHubSession
import ssl

ssl_context = ssl.SSLContext.create_default_context(
    cafile="<Your CA Certificate File Path>",
)

client = IoTHubSession.from_connection_string(
    "<Your Connection String>",
    ssl_context=ssl_context,
)
```

### Cipher Suites
#### V2
```python
from azure.iot.device.aio import IoTHubDeviceClient

client = IoTHubDeviceClient.create_from_connection_string(
    "<Your Connection String>",
    cipher="<Your Cipher>"
)
```

#### V3
```python
from azure.iot.device import IoTHubSession
import ssl

ssl_context = ssl.SSLContext.create_default_context()
ssl_context.set_ciphers("<Your Cipher>")

client = IoTHubSession.from_connection_string(
    "<Your Connection String>",
    ssl_context=ssl_context,
)
```

## Data object changes

### Message Objects
Some changes have been made to the `Message` object used for sending and receiving data.
* The `.data` attribute is now called `.payload` for consistency with other objects in the API
* The `message_id` parameter is no longer part of the constructor arguments. It should be manually added as an attribute, just like all other attributes
* The payload of a received Message is now a unicode string value instead of a bytestring value.
It will be decoded according to the content encoding property sent along with the message.

#### V2
```python
from azure.iot.device import Message

payload = "this is a payload"
message_id = "1234"
m = Message(data=payload, message_id=message_id)

assert m.data == payload
assert m.message_id = message_id
```

#### V3
```python
from azure.iot.device import Message

payload = "this is a payload"
message_id = "1234"
m = Message(payload=payload)
m.message_id = message_id

assert m.payload == payload
```

### Direct Method Objects

`MethodRequest` and `MethodResponse` objects from V2 have been renamed to `DirectMethodRequest` and `DirectMethodResponse` respectively. They are otherwise identical.

## Removed Keyword Arguments

Some keyword arguments provided at client creation in V2 have been removed in V3 as they are no longer necessary.

| V2                          | V3               | Explanation                                              |
|-----------------------------|------------------|----------------------------------------------------------|
| `connection_retry`          | **REMOVED**      | No automatic reconnect                                   |
| `connection_retry_interval` | **REMOVED**      | No automatic reconnect                                   |
| `auto_connect`              | **REMOVED**      | Connection managed by `IoTHubSession` context manager    |
| `ensure_desired_properties` | **REMOVED**      | No more implicit twin updates                            |
| `gateway_hostname`          | **REMOVED**      | Supported via `hostname` parameter                       |
| `server_verification_cert`  | **REMOVED**      | Supported via SSL injection                              |
| `cipher`                    | **REMOVED**      | Supported via SSL injection                              |



## Managing Lifecycle of `IoTHubSession`
The above examples are fairly simple, but what about applications that do multiple things? And how can we handle a graceful exit?

The following example from V2 demonstrates an application that receives both C2D messages and Direct Method Requests, while also sending telemetry every 5 seconds, until a `KeyboardInterrupt`
is issued.
#### V2
```python
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import MethodResponse
import asyncio
import time

def create_client():
    client = IoTHubDeviceClient.create_from_connection_string("<Your Connection String>")

    # define behavior for receiving a message
    def message_handler(message):
        print("the data in the message received was ")
        print(message.data)

    # define behavior for receiving direct methods
    async def method_handler(method_request):
        if method_request.name == "foo":
            result = do_foo()
            payload = {"result": result}
            status = 200
            print("Completed foo")
        else:
            payload = {}
            status = 400
            print("Unknown direct method request")
        method_response = MethodResponse.create_from_method_request(method_request, status, payload)
        await client.send_method_response(method_response)

    # set the incoming data handlers on the client
    client.on_message_received = message_handler
    client.on_method_request_received = method_handler

    return client

async def send_telemetry(client):
    while True:
        # Send the current time every 5 seconds
        curr_time = time.time()
        print("Sending Telemetry...")
        try:
            await client.send_message(str(curr_time))
        except Exception:
            print("Sending telemetry failed")
        await asyncio.sleep(5)

async def main():
    client = create_client()

    await client.connect()

    try:
        await send_telemetry(client)
    except KeyboardInterrupt:
        print("User exit!")
    except Exception:
        print("Unexpected error")
    finally:
        # Shut down for graceful exit
        await client.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

Here is the same application, this time written for the V3 `IoTHubSession`.

#### V3
```python
from azure.iot.device import IoTHubSession, DirectMethodResponse, MQTTError, MQTTConnectionFailedError
import asyncio
import time

async def recurring_telemetry(session):
    while True:
        # Send the current time every 5 seconds
        curr_time = time.time()
        print("Sending Telemetry...")
        await session.send_message(str(curr_time))
        await asyncio.sleep(5)

async def receive_c2d_messages(session):
    async with session.messages() as messages:
        async for message in messages:
            print("the data in the message received was ")
            print(message.payload)

async def receive_direct_method_requests(session):
    async with session.direct_method_requests() as method_requests:
        async for method_request in method_requests:
            if method_request.name == "foo":
                result = do_foo()
                payload = {"result": result}
                status = 200
                print("Completed foo")
            else:
                payload = {}
                status = 400
                print("Unknown direct method request")
            method_response = DirectMethodResponse.create_from_method_request(method_request, status, payload)
            await session.send_direct_method_response(method_response)

async def main():
    while True:
        try:
            async with IoTHubSession.from_connection_string("<Your Connection String>") as session:
                await asyncio.gather(
                    recurring_telemetry(session),
                    receive_c2d_messages(session),
                    receive_direct_method_requests(session),
                )
        except KeyboardInterrupt:
            print("User exit!")
            raise
        except MQTTError:
            print("Connection was lost. Trying again in 5 seconds")
            await asyncio.sleep(5)
        except MQTTConnectionFailedError:
            print("Could not connect. Trying again in 10 seconds")
            await asyncio.sleep(10)
        except Exception:
            print("Unexpected error")


if __name__ == "__main__":
    asyncio.run(main())
```
Some implementation notes on this V3 sample:

* Unlike in the V2 sample, there is no need for a `.shutdown()` method as all cleanup is handled by the `IoTHubSession` context manager.
* Reconnection logic must be directly implemented in the V3 sample, in contrast to it being automatically done in the background in V2 (as explained in the "Responding to Network Failure" section above). This will also allow for handling SAS token expiration, which was also done implicitly in V2 (as explained in the "SAS Token Expiration" section)
* Within the `IoTHubSession` context manager, the session object is passed around to various coroutines that can be run together with `asyncio.gather`.. There are other ways this could be implemented as well, the point here is to run all your logic from the block of code inside the context manager.
* When a `KeyboardInterrupt` is issued by the user, the application breaks out of the context manager, triggering cleanup.