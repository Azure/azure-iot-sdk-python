# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import json
import threading
from dev_utils import get_random_dict

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

# TODO: add tests for various application properties
# TODO: is there a way to call send_c2d so it arrives as an object rather than a JSON string?


@pytest.mark.describe("Client C2d")
class TestReceiveC2d(object):
    @pytest.mark.it("Can receive C2D")
    @pytest.mark.quicktest_suite
    def test_sync_receive_c2d(self, client, service_helper, leak_tracker):
        leak_tracker.set_initial_object_list()

        message = json.dumps(get_random_dict())

        received_message = None
        received = threading.Event()

        def handle_on_message_received(message):
            nonlocal received_message, received
            logger.info("received {}".format(message))
            received_message = message
            received.set()

        client.on_message_received = handle_on_message_received

        service_helper.send_c2d(message, {})

        received.wait(timeout=60)
        assert received.is_set()

        assert received_message.data.decode("utf-8") == message

        received_message = None  # so this isn't tagged as a leak
        leak_tracker.check_for_leaks()
