# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import time


def wait_for_condition(condition, *, timeout, interval=0.1):
    deadline = time.monotonic() + timeout
    while not condition():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Timed out waiting for condition")
        time.sleep(min(interval, remaining))


async def async_wait_for_condition(condition, *, timeout, interval=0.1):
    async def poll_condition():
        while not condition():
            await asyncio.sleep(interval)

    await asyncio.wait_for(poll_condition(), timeout=timeout)
