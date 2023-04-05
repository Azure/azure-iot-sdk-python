# Azure IoT Device SDK for Python Migration Guide (Async) - IoTHubDeviceClient/IoTHubModuleClient -> IoTHubSession

This guide details how to update existing code for IoT Hub that uses an `azure-iot-device` V2 release to use a V3 release instead.

Note that currently V3 only presents an async set of APIs.

For changes when using the Device Provisioning Service, please refer to `migration_guide_provisioning.md` in this same directory.

The design goals for V3 were to make a more stripped back, simple API surface that allows for a greater flexibility for the end user, as well as improved reliability and clarity. We have attempted to remove as much implicit behavior as possible,

## Connection Management
The most significant change in V3 is the removal of manual connection/disconnection. Connections are now managed automatically by a context manager.

### V2
```python
from azure.iot.device import IoTHubDeviceClient

async def main():
    await client = IoTHubDeviceClient.create_from_connection_string("<Your Connection String>")
    await client.connect()
    # <do things>
    await client.disconnect()
```

### V3
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

### V2
```python
from azure.iot.device import IoTHubDeviceClient

async def main():
    await client = IoTHubDeviceClient.create_from_connection_string("<Your Connection String>")
    await client.connect()

    await client.send_message("hello world")

    await client.disconnect()
```

### V3
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

### V2
```python
from azure.iot.device import IoTHubDeviceClient

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

### V3
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


## Responding to Network Failure

In the V2 IoTHubDeviceClient and IoTHubModuleClient, the default behavior was to try and re-establish connections that failed. In the V3 `IoTHubSession`, not only is this not the default behavior, but this behavior is not supported at all. In order to provide flexibility surrounding reconnect scenarios, we have changed the design to put control in the hands of the end user. No longer will there be any confusion as to the connection state - it will be directly and clearly reported. No longer are there implicit reconnect attempts that happen without user knowledge.

To reconnect after a connection drop, simply wrap your `IoTHubSession` usage in a try/except block. All outgoing operation APIs, as well incoming data generators will raise `MQTTError` upon a lost connection, so you can catch that, and respond with a reconnect attempt

Additionally, in the case where you cannot connect, the `IoTHubSession` context manager itself will raise `MQTTConnectionFailedError`, which you can catch and respond to with a reconnect attempt.

In the following example, we attempt to connect and wait for incoming C2D messages. If we are connected and the connection is dropped, a reconnect attempt will be made after 5 seconds. If we attempt to reconnect and fail doing so, we will try again after 10 seconds.

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