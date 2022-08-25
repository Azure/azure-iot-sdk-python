# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import uuid


@pytest.mark.describe("ServiceHelper object")
class TestServiceHelper(object):
    @pytest.mark.it("returns None when wait_for_event_arrival times out")
    def test_sync_wait_for_event_arrival(self, client, random_message, service_helper):

        event = service_helper.wait_for_eventhub_arrival(uuid.uuid4(), timeout=2)
        assert event is None
