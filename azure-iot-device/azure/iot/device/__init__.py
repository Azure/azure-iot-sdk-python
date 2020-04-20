""" Azure IoT Device Library

This library provides clients and associated models for communicating with Azure IoT services
from an IoT device.
"""

# Import all exposed items in subpackages to expose them via this package
from .iothub import *
from .provisioning import *
from .common import *  # TODO: do we really want to do this?

# Import the subpackages themselves in order to set the __all__
from . import iothub
from . import provisioning
from . import common

# Import the module to generate missing documentation
from . import patch_documentation


# TODO: remove this chunk of commented code if we truly no longer want to take this approach

# if sys.version_info > (3, 5):  # This only works for python 3.5+ at present
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
patch_documentation.execute_patch_for_sync()


# iothub and common subpackages are still showing up in intellisense

__all__ = iothub.__all__ + provisioning.__all__ + common.__all__
