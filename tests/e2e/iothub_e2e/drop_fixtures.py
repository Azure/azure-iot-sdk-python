# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import iptables
import logging
import e2e_settings

logger = logging.getLogger(__name__)

iptables.reconnect_all("mqtt", e2e_settings.IOTHUB_HOSTNAME)
iptables.reconnect_all("mqttws", e2e_settings.IOTHUB_HOSTNAME)


class Dropper(object):
    def __init__(self, transport):
        self.transport = transport

    def disconnect_outgoing(self, disconnect_type):
        iptables.disconnect_output_port(
            disconnect_type, self.transport, e2e_settings.IOTHUB_HOSTNAME
        )

    def drop_outgoing(self):
        iptables.disconnect_output_port("DROP", self.transport, e2e_settings.IOTHUB_HOSTNAME)

    def reject_outgoing(self):
        iptables.disconnect_output_port("REJECT", self.transport, e2e_settings.IOTHUB_HOSTNAME)

    def restore_all(self):
        iptables.reconnect_all(self.transport, e2e_settings.IOTHUB_HOSTNAME)


@pytest.fixture(scope="function")
def dropper(transport):
    dropper = Dropper(transport)
    yield dropper
    logger.info("restoring all")
    dropper.restore_all()
