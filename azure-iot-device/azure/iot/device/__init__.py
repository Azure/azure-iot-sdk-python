""" Azure IoT Device Library

This library provides clients and associated models for communicating with Azure IoT services
from an IoT device.
"""

from .iothub import *
from .iothub import auth  # Consider moving this to common after DPS added
from . import iothub

# iothub and common subpackages are still showing up in intellisense


__all__ = iothub.__all__  # + provisioning.__all__ etc.
