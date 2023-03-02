# Azure IoT Device SDK for Python Migration Guide - ProvisioningDeviceClient

This guide details how to update existing code that uses an `azure-iot-device` V2 release to use a V3 release instead. While the APIs remain mostly the same, there are several differences you will need to account for in your application, as changes have been made in order to provide a more reliable and consistent user experience.

Note that this guide is a work in progress.

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