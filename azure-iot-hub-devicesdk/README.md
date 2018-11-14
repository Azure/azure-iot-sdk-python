
Azure IoT Device SDK Installation
====================================

# Install

The wheel file distribution should be named like `azure_iot_hub_devicesdk-0.0.1-py2.py3-none-any.whl`
To install the file with extension `.whl` file please run the following command in a terminal `pip install <filename>`

For the purpose of writing the samples for device and module it should be known that the top level package is `azure`

More details for discovering the top level package can be found [below](#finding-the-top-level-package)

# Samples

## Device Sample


In this sample we can create a device client. This device client will enable sending telemetry to the IoT Hub. 

* Create an authentication provider. Authentication provider can be created currently in 2 ways.

  * supplying the device specific connection string
    *  if an IoT device has been created, the connection string can be retrieved from the Azure Portal by going to the device properties.
  * supplying the shared access signature

* Create a device client using the authentication provider and a transport protocol. Currently the SDK only supports `mqtt`.
* Connect the device client.
* Send event from the device client. Send event can be invoked after

  * Verifying that the device client has been connected with a handler for `on_connection_state`. This is the preferred method.
  * Or sleeping for a little while to let the device client be connected.

### Code snippet

##### Connection state handler
```python


    from azure.iot.hub.devicesdk.device_client import DeviceClient
    from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_connection_string

    conn_str = "<IOTHUB_DEVICE_CONNECTION_STRING>"
    auth_provider = from_connection_string(conn_str)
    simple_device = DeviceClient.from_authentication_provider(auth_provider, "mqtt")


    def connection_state_callback(status):
        print("connection status: " + status)
            if status == "connected":
                simple_device.send_event("caput draconis")

    simple_device.on_connection_state = connection_state_callback
    simple_device.connect()
```

##### Sleep after connection
```python


    from azure.iot.hub.devicesdk.device_client import DeviceClient
    from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_connection_string
    import time

    conn_str = "<IOTHUB_DEVICE_CONNECTION_STRING>"
    auth_provider = from_connection_string(conn_str)
    simple_device = DeviceClient.from_authentication_provider(auth_provider, "mqtt")
    simple_device.connect()
    
    time.sleep(30)
```

## Module Sample

This is very similar to the device client. All the steps above remains same except that now we create a module client.

### Code snippet


Below code shows a different way of creating an authentication provider from a shared access signature and then using a module client. 

```python


    from azure.iot.hub.devicesdk.module_client import ModuleClient
    from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_shared_access_signature

    sas_token_string = "<IOTHUB_DEVICE_SAS_STRING>"

    auth_provider = from_shared_access_signature(sas_token_string)
    simple_module = ModuleClient.from_authentication_provider(auth_provider, "mqtt")

    def connection_state_callback(status):
        print("connection status: " + status)
            if status == "connected":
                simple_module.send_event("payload from module")

    simple_module.on_connection_state = connection_state_callback
    simple_module.connect()
```


### Finding the top level package

These steps can offer guidance after the wheel has been installed

Running the command `pip list` on a terminal would list out all the packages installed. A package would be found in the list of installed packages which should be named like
`azure_iot_hub_devicesdk` with a certain version like `0.0.1`.

The python interpreter can be invoked by running the command `python` on the terminal.
In the python interpreter, please run command `help()` to know more regarding available options.
Once inside the help session, running the command `modules` would list all the available modules.

It should list a module named `azure`.Type `azure` in the prompt to get help on this package and discover the packages underneath `azure`. 
For example the `azure` package has an `iot` package underneath it, to discover the packages underneath `iot` type the command `azure.iot` on the terminal.
