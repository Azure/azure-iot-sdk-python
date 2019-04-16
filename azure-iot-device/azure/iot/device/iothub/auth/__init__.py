"""Azure IoT Hub Device SDK Authentication

This package provides authentication-related functionality for use with the
Azure IoT Hub Device SDK.
"""

from .authentication_provider_factory import (
    from_connection_string,
    from_shared_access_signature,
    from_environment,
)

__all__ = ["from_connection_string", "from_shared_access_signature", "from_environment"]
