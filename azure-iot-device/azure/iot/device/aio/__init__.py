"""Azure IoT Device Library - Asynchronous

This library provides asynchronous clients for communicating with Azure IoT services
from an IoT device.
"""

from azure.iot.device.iothub.aio import *
from azure.iot.device.provisioning.aio import *
from . import patch_documentation

# Dynamically patch the clients to add shim implementations for all the inherited methods.
# This is necessary to generate accurate online docs.
# It SHOULD not impact the functionality of the methods themselves in any way.

# NOTE In the event of addition of new methods and generation of accurate documentation
# for those methods we have to append content to "patch_documentation.py" file.
# In order to do so please uncomment the "patch.add_shims" lines below,
# enable logging with level "DEBUG" in a python terminal and do
# "import azure.iot.device". The delta between the newly generated output
# and the existing content of "patch_documentation.py" should be appended to
# the function "execute_patch_for_sync" in "patch_documentation.py".
# Once done please again omment out the "patch.add_shims" lines below.

# patch.add_shims_for_inherited_methods(IoTHubDeviceClient)  # noqa: F405
# patch.add_shims_for_inherited_methods(IoTHubModuleClient)  # noqa: F405
# patch.add_shims_for_inherited_methods(ProvisioningDeviceClient)  # noqa: F405


patch_documentation.execute_patch_for_async()
