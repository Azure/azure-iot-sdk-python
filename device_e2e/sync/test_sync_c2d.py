# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import json
import threading
from utils import get_random_dict

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

# TODO: add tests for various application properties
# TODO: is there a way to call send_c2d so it arrives as an object rather than a JSON string?


@pytest.mark.describe("Client C2d")
class TestSendMessage(object):
    @pytest.mark.it("Can receive C2D")
    @pytest.mark.quicktest_suite
    def test_send_message(self, client, service_helper):
        message = json.dumps(get_random_dict())

        received = threading.Event()

        # hack needed because there is no `nonlocal` keyword in py27.
        nonlocal_py27_hack = {"received_msg": None, "received": received}

        def handle_on_message_received(message):
            logger.info("received {}".format(message))
            nonlocal_py27_hack["received_message"] = message
            nonlocal_py27_hack["received"].set()

        client.on_message_received = handle_on_message_received

        service_helper.send_c2d(message, {})

        received.wait(timeout=60)
        assert received.is_set()

        assert nonlocal_py27_hack["received_message"].data.decode("utf-8") == message
