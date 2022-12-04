# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import logging
import task_cleanup
import random

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.mark.stress
@pytest.mark.describe("Client object connect/disconnect stress")
class TestConnectDisconnectStress(object):
    @pytest.mark.parametrize("iteration_count", [10, 50])
    @pytest.mark.it("Can do many non-overlapped connects and disconnects")
    async def test_non_overlapped_connect_disconnect_stress(
        self, client, iteration_count, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        for _ in range(iteration_count):
            await client.connect()
            await client.disconnect()

        leak_tracker.check_for_leaks()

    @pytest.mark.parametrize("iteration_count", [20, 250])
    @pytest.mark.it("Can do many overlapped connects and disconnects")
    @pytest.mark.timeout(600)
    async def test_overlapped_connect_disconnect_stress(
        self, client, iteration_count, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        tasks = []
        for _ in range(iteration_count):
            tasks.append(asyncio.create_task(client.connect()))
            tasks.append(asyncio.create_task(client.disconnect()))

        try:
            await asyncio.gather(*tasks)
        finally:
            await task_cleanup.cleanup_tasks(tasks)

        leak_tracker.check_for_leaks()

    @pytest.mark.parametrize("iteration_count", [20, 500])
    @pytest.mark.it("Can do many overlapped random connects and disconnects")
    @pytest.mark.timeout(600)
    async def test_overlapped_random_connect_disconnect_stress(
        self, client, iteration_count, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        tasks = []
        for _ in range(iteration_count):
            if random.random() > 0.5:
                tasks.append(asyncio.create_task(client.connect()))
            else:
                tasks.append(asyncio.create_task(client.disconnect()))

        try:
            await asyncio.gather(*tasks)
        finally:
            await task_cleanup.cleanup_tasks(tasks)

        leak_tracker.check_for_leaks()
