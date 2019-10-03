# IoTHub Python SDK Migration Guide

This guide details the migration plan to move from the IoTHub Python v1 code base to the new and improved v2 
code base.  

## Installing the IoTHub Python SDK

- v1 SDK

```Shell
pip install azure-iothub-device-client

```

- v2 SDK

```Shell
pip install azure-iot-device
```

## Creating a device client

### Symmetric Key authentication

- v1

```Python
    from iothub_client import IoTHubClient, IoTHubClientError, IoTHubTransportProvider, IoTHubClientResult
    from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError, DeviceMethodReturnValue

    client = IoTHubClient(connection_string, IoTHubTransportProvider.MQTT)
```

- v2

```Python
    from azure.iot.device.aio import IoTHubDeviceClient
    from azure.iot.device import Message

    client = IoTHubDeviceClient.create_from_connection_string(connection_string)
    await device_client.connect()
```

### x.509 authentication

- v1

```Python
    from iothub_client import IoTHubClient, IoTHubClientError, IoTHubTransportProvider, IoTHubClientResult
    from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError, DeviceMethodReturnValue

    client = IoTHubClient(connection_string, IoTHubTransportProvider.MQTT)
    # Get the x.509 certificate information
    client.set_option("x509certificate", X509_CERTIFICATE)
    client.set_option("x509privatekey", X509_PRIVATEKEY)
```

- v2

```Python
    from azure.iot.device.aio import IoTHubDeviceClient
    from azure.iot.device import Message

    # Get the x.509 certificate path from the environment
    x509 = X509(
        cert_file=os.getenv("X509_CERT_FILE"),
        key_file=os.getenv("X509_KEY_FILE"),
        pass_phrase=os.getenv("PASS_PHRASE")
    )
    client = IoTHubDeviceClient.create_from_x509_certificate(hostname=hostname, device_id=device_id, x509=x509)
    await device_client.connect()
```

## Sending Telemetry to IoTHub

- v1 SDK

```Python
    # create the device client

    message = IoTHubMessage("telemetry message")
    message.message_id = "message id"
    message.correlation_id = "correlation-id"

    prop_map = message.properties()
    prop_map.add("property", "property_value")
    client.send_event_async(message, send_confirmation_callback, user_ctx)
```

- v2

```Python
    # create the device client

    message = Message("telemetry message")
    message.message_id = "message id"
    message.correlation_id = "correlation id"

    message.custom_properties["property"] = "property_value"
    client.send_message(message)
```

## Receiving a Message from IoTHub

- v1 SDK

```Python
    # create the device client

    def receive_message_callback(message, counter):
        global RECEIVE_CALLBACKS
        message = message.get_bytearray()
        size = len(message_buffer)
        print ( "the data in the message received was : <<<%s>>> & Size=%d" % (message_buffer[:size].decode('utf-8'), size) )
        map_properties = message.properties()
        key_value_pair = map_properties.get_internals()
        print ( "custom properties are: %s" % key_value_pair )
        return IoTHubMessageDispositionResult.ACCEPTED

    client.set_message_callback(message_listener_callback, RECEIVE_CONTEXT)
```

- v2

```Python
    # create the device client

    def message_listener(client):
        while True:
            message = client.receive_message()  # blocking call
            print("the data in the message received was ")
            print(message.data)
            print("custom properties are")
            print(message.custom_properties)

    # Run a listener thread in the background
    listen_thread = threading.Thread(target=message_listener, args=(device_client,))
    listen_thread.daemon = True
    listen_thread.start()
```
