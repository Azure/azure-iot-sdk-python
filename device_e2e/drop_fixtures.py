# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import drop
import logging

logger = logging.getLogger(__name__)

drop.reconnect_all("mqtt")


class Dropper(object):
    def __init__(self, transport):
        self.transport = transport

    def drop_outgoing(self):
        drop.disconnect_port("DROP", self.transport)

    def reject_outgoing(self):
        drop.disconnect_port("REJECT", self.transport)

    def restore_all(self):
        drop.reconnect_all(self.transport)


@pytest.fixture(scope="function")
def dropper(transport):
    dropper = Dropper(transport)
    yield dropper
    logger.info("restoring all")
    dropper.restore_all()
