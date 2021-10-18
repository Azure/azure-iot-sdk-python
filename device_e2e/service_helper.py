# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.
from service_helper_sync import ServiceHelperSync


class ServiceHelper:
    def __init__(self, event_loop, executor):
        self.event_loop = event_loop
        self.executor = executor
        self.inner_object = ServiceHelperSync()

    def set_identity(self, device_id, module_id):
        return self.inner_object.set_identity(device_id, module_id)

    async def set_desired_properties(self, desired_props):
        return await self.event_loop.run_in_executor(
            self.executor,
            self.inner_object.set_desired_properties,
            desired_props,
        )

    async def invoke_method(
        self,
        method_name,
        payload,
        connect_timeout_in_seconds=None,
        response_timeout_in_seconds=None,
    ):
        return await self.event_loop.run_in_executor(
            self.executor,
            self.inner_object.invoke_method,
            method_name,
            payload,
            connect_timeout_in_seconds,
            response_timeout_in_seconds,
        )

    async def send_c2d(
        self,
        payload,
        properties,
    ):
        return await self.event_loop.run_in_executor(
            self.executor, self.inner_object.send_c2d, payload, properties
        )

    async def wait_for_eventhub_arrival(self, message_id, timeout=20):
        return await self.event_loop.run_in_executor(
            self.executor,
            self.inner_object.wait_for_eventhub_arrival,
            message_id,
            timeout,
        )

    async def get_next_reported_patch_arrival(self, block=True, timeout=20):
        return await self.event_loop.run_in_executor(
            self.executor,
            self.inner_object.get_next_reported_patch_arrival,
            block,
            timeout,
        )

    async def shutdown(self):
        return await self.event_loop.run_in_executor(self.executor, self.inner_object.shutdown)
