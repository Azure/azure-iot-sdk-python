""" Azure IoT Device Library

This library provides clients and associated models for communicating with Azure IoT services
from an IoT device.
"""

from .iothub import *
from .provisioning import *
from .common import *
from . import iothub
from . import provisioning
from . import common
from . import patch
import sys

if sys.version_info > (3, 5):  # This only works for python 3.5+ at present
    # Dynamically patch the clients to add shim implementations for all the inherited methods.
    # This is necessary to generate accurate online docs.
    # It SHOULD not impact the functionality of the methods themselves in any way.
    patch.add_shims_for_inherited_methods(IoTHubDeviceClient)  # noqa: F405
    patch.add_shims_for_inherited_methods(IoTHubModuleClient)  # noqa: F405
    patch.add_shims_for_inherited_methods(ProvisioningDeviceClient)  # noqa: F405


# iothub and common subpackages are still showing up in intellisense

__all__ = iothub.__all__ + provisioning.__all__
