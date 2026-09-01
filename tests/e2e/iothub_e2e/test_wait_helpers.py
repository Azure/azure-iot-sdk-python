# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio

import pytest

import wait_helpers


@pytest.mark.describe("E2E wait helpers")
class TestWaitHelpers(object):
    @pytest.mark.it("Polls a synchronous condition until it becomes true")
    def test_wait_for_condition(self, mocker):
        condition = mocker.Mock(side_effect=[False, True])

        wait_helpers.wait_for_condition(condition, timeout=0.1, interval=0)

        assert condition.call_count == 2

    @pytest.mark.it("Times out waiting for a synchronous condition")
    def test_wait_for_condition_timeout(self):
        with pytest.raises(TimeoutError):
            wait_helpers.wait_for_condition(lambda: False, timeout=0.01, interval=0.001)

    @pytest.mark.it("Polls a condition without blocking the event loop")
    async def test_async_wait_for_condition(self, mocker):
        condition = mocker.Mock(side_effect=[False, True])

        await wait_helpers.async_wait_for_condition(condition, timeout=0.1, interval=0)

        assert condition.call_count == 2

    @pytest.mark.it("Times out waiting for an asynchronous condition")
    async def test_async_wait_for_condition_timeout(self):
        with pytest.raises(asyncio.TimeoutError):
            await wait_helpers.async_wait_for_condition(lambda: False, timeout=0.01, interval=0.001)
