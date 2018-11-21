# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import os
import logging
from .base_renewable_token_authentication_provider import BaseRenewableTokenAuthenticationProvider
from .iotedge_hsm import IotEdgeHsm

logger = logging.getLogger(__name__)


class IotEdgeAuthenticationProvider(BaseRenewableTokenAuthenticationProvider):
    """
    An Azure IoT Edge Authentication Provider. This provider creates the Shared Access Signature that would be needed to connenct to the IoT Edge runtime
    """

    def __init__(self):
        """
        Constructor for IoT Edge Authentication Provider
        """
        hostname = os.environ["IOTEDGE_IOTHUBHOSTNAME"]
        device_id = os.environ["IOTEDGE_DEVICEID"]
        module_id = os.environ["IOTEDGE_MODULEID"]

        logger.info("Using IoTEdge authentication for {%s, %s, %s}", hostname, device_id, module_id)

        BaseRenewableTokenAuthenticationProvider.__init__(self, hostname, device_id, module_id)

        self.hsm = IotEdgeHsm()
        self.gateway_hostname = os.environ["IOTEDGE_GATEWAYHOSTNAME"]
        self.ca_cert = self.hsm.get_trust_bundle()

    @staticmethod
    def parse(connection_string):
        pass

    def _sign(self, quoted_resource_uri, expiry):
        """
        Creates the signature to be inserted in the SAS token
        :param resource_uri: the resource URI to encode into the token
        :param expiry: an integer value representing the number of seconds since the epoch 00:00:00 UTC on 1 January 1970 at which the token will expire.
        :return: The signature portion of the Sas Token.
        """
        string_to_sign = quoted_resource_uri + "\n" + str(expiry)
        return self.hsm.sign(string_to_sign)
