# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
from .authentication_provider import AuthenticationProvider

logger = logging.getLogger(__name__)


class X509AuthenticationProvider(AuthenticationProvider):
    """
    An X509 Authentication Provider. This provider uses the certificate and key provided to
    authenticate a device with an Azure IoT Hub instance. X509 Authentication is only supported
    for device identities connecting directly to an Azure IoT hub.
    """

    def __init__(self, hostname, device_id, x509):
        """
        Constructor for X509 Authentication Provider
        :param hostname: The hostname of the Azure IoT hub.
        :param device_id: The device unique identifier as it exists in the Azure IoT Hub device registry.
        :param x509: The X509 object containing certificate, key and passphrase
        """
        logger.info("Using X509 authentication for {%s, %s}", hostname, device_id)
        super(X509AuthenticationProvider, self).__init__(hostname=hostname, device_id=device_id)
        self._x509 = x509

    def get_x509_certificate(self):
        """
        :return: The x509 certificate, To use the certificate the enrollment object needs to contain
         cert (either the root certificate or one of the intermediate CA certificates).
        """
        return self._x509
