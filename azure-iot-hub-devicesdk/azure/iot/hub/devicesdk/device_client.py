# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from .internal_client import InternalClient
import logging

logger = logging.getLogger(__name__)


class DeviceClient(InternalClient):
    def __init__(self, auth_provider, transport):
        InternalClient.__init__(self, auth_provider, transport)
        self._transport.on_transport_c2d_message_received = self._handle_c2d_message_received

    def _handle_c2d_message_received(self, message_received):
        if self.on_c2d_message:
            self.on_c2d_message(message_received)
        else:
            logger.warn("No handler defined for receiving c2d message")
