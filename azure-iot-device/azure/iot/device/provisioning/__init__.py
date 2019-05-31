"""Azure Provisioning Device Library

This library provides functionality that enables zero-touch, just-in-time provisioning to the right IoT hub without requiring
human intervention, enabling customers to provision millions of devices in a secure and scalable manner.

"""
from .sk_provisioning_device_client import SymmetricKeyProvisioningDeviceClient
from .security import SymmetricKeySecurityClient
from .models import RegistrationResult

__all__ = [
    "SymmetricKeyProvisioningDeviceClient",
    "SymmetricKeySecurityClient",
    "RegistrationResult",
]
