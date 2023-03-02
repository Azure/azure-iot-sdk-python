# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""Define Azure IoT domain exceptions to be shared across modules"""


class IoTHubError(Exception):
    """Represents a failure reported by IoT Hub"""

    pass


class IoTEdgeError(Exception):
    """Represents a failure reported by IoT Edge"""

    pass


class IoTEdgeEnvironmentError(Exception):
    """Represents a failure retrieving data from the IoT Edge environment"""


class IoTHubClientError(Exception):
    """Represents a failure from the IoTHub Client"""

    pass
