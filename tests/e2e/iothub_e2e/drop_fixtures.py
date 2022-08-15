# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
from dev_utils import iptables, test_env

logger = logging.getLogger(__name__)

print("reconnecting mqtt")
iptables.reconnect_all("mqtt", test_env.IOTHUB_HOSTNAME)
print("reconnecting mqttws")
iptables.reconnect_all("mqttws", test_env.IOTHUB_HOSTNAME)
print("Done")


class Dropper(object):
    def __init__(self, transport):
        self.transport = transport

    def disconnect_outgoing(self, disconnect_type):
        iptables.disconnect_output_port(disconnect_type, self.transport, test_env.IOTHUB_HOSTNAME)

    def drop_outgoing(self):
        iptables.disconnect_output_port("DROP", self.transport, test_env.IOTHUB_HOSTNAME)

    def reject_outgoing(self):
        iptables.disconnect_output_port("REJECT", self.transport, test_env.IOTHUB_HOSTNAME)

    def restore_all(self):
        iptables.reconnect_all(self.transport, test_env.IOTHUB_HOSTNAME)


@pytest.fixture(scope="function")
def dropper(transport):
    dropper = Dropper(transport)
    yield dropper
    logger.info("restoring all")
    dropper.restore_all()
