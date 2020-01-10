# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging

logger = logging.getLogger(__name__)


class BasePipelineConfig(object):
    """A base class for storing all configurations/options shared across the Azure IoT Python Device Client Library.
    More specific configurations such as those that only apply to the IoT Hub Client will be found in the respective
    config files.
    """

    def __init__(self, websockets=False, cipher=""):
        """Initializer for BasePipelineConfig

        :param bool websockets: Enabling/disabling websockets in MQTT. This feature is relevant if a firewall blocks port 8883 from use.
        :param str cipher: Optional cipher suite(s) for TLS/SSL. In "OpenSSL cipher list format"
        """
        self.websockets = websockets
        self.cipher = cipher
