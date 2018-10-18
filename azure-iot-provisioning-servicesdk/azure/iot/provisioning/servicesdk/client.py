# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

"""Redefine the generated ProvisioningServiceClient class via inheritance to allow for API
customization and authentication logic injection
"""

from .protocol import ProvisioningServiceClient as _ProvisioningServiceClient
from .auth import ConnectionStringAuthentication, HOST_NAME


class ProvisioningServiceClient(_ProvisioningServiceClient):
    """API for service operations with the Azure IoT Hub Device Provisioning Service

    :ivar config: Configuration for client.
    :vartype config: ProvisioningServiceClientConfiguration

    :param str connection_string: Connection String for your Device Provisioning Service hub.
    """

    def __init__(self, connection_string):
        cs_auth = ConnectionStringAuthentication(connection_string)
        super(ProvisioningServiceClient, self).__init__(cs_auth, "https://" + cs_auth[HOST_NAME])
