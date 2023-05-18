# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""Define Azure IoT domain user-facing exceptions to be shared across package"""
from .mqtt_client import (  # noqa: F401 (Importing directly to re-export)
    MQTTError,
    MQTTConnectionFailedError,
    MQTTConnectionDroppedError,
)


# Client/Session Exceptions
# TODO: Should this be here? Only if HTTP stack still exists. If not, move to specific file
# TODO: Should this just be a generic ClientError that could be used across clients?
class IoTHubClientError(Exception):
    """Represents a failure from the IoTHub Client"""

    pass


class SessionError(Exception):
    """Represents a failure from the Session object"""

    pass


class CredentialError(Exception):
    """Represents a failure from an invalid auth credential"""

    pass


# Service Exceptions
class IoTHubError(Exception):
    """Represents a failure reported by IoT Hub"""

    pass


class IoTEdgeError(Exception):
    """Represents a failure reported by IoT Edge"""

    pass


class ProvisioningServiceError(Exception):
    """Represents a failure reported by Provisioning Service"""

    pass


class IoTEdgeEnvironmentError(Exception):
    """Represents a failure retrieving data from the IoT Edge environment"""

    pass
