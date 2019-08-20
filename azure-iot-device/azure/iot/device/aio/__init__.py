"""Azure IoT Device Library - Asynchronous

This library provides asynchronous clients for communicating with Azure IoT services
from an IoT device.
"""

from azure.iot.device.iothub.aio import *
from azure.iot.device.provisioning.aio import *
from azure.iot.device import patch

# Dynamically patch the clients to add shim implementations for all the inherited methods.
# This is necessary to generate accurate online docs.
# It SHOULD not impact the functionality of the methods themselves in any way.
patch.add_shims_for_inherited_methods(IoTHubDeviceClient)  # noqa: F405
patch.add_shims_for_inherited_methods(IoTHubModuleClient)  # noqa: F405
patch.add_shims_for_inherited_methods(ProvisioningDeviceClient)  # noqa: F405
