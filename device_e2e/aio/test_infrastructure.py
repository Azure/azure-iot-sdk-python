# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import uuid

pytestmark = pytest.mark.asyncio


@pytest.mark.describe("ServiceHelper object")
class TestServiceHelper(object):
    @pytest.mark.it("returns None when wait_for_event_arrival times out")
    async def test_validate_wait_for_eventhub_arrival_timeout(
        self, client, random_message, service_helper
    ):
        # Because we have to support py27, we can't use `threading.Condition.wait_for`.
        # make sure our stand-in functionality behaves the same way when dealing with
        # timeouts.  The 'non-timeout' case is exercised in every test that uses
        # `service_helper.wait_for_eventhub_arrival`, so we don't need a specific test
        # for that here.
        event = await service_helper.wait_for_eventhub_arrival(uuid.uuid4(), timeout=2)
        assert event is None
