# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.
from service_helper_sync import ServiceHelperSync


class ServiceHelper:
    def __init__(self, event_loop, executor):
        self.event_loop = event_loop
        self.executor = executor
        self.inner_object = ServiceHelperSync()

    def start_watching(self, device_id, module_id):
        return self.inner_object.start_watching(device_id, module_id)

    def stop_watching(self, device_id, module_id):
        return self.inner_object.stop_watching(device_id, module_id)

    async def set_desired_properties(self, desired_props, device_id=None, module_id=None):
        return await self.event_loop.run_in_executor(
            self.executor,
            self.inner_object.set_desired_properties,
            desired_props,
            device_id,
            module_id,
        )

    async def invoke_method(
        self,
        method_name,
        payload,
        device_id=None,
        module_id=None,
        connect_timeout_in_seconds=None,
        response_timeout_in_seconds=None,
    ):
        return await self.event_loop.run_in_executor(
            self.executor,
            self.inner_object.invoke_method,
            method_name,
            payload,
            device_id,
            module_id,
            connect_timeout_in_seconds,
            response_timeout_in_seconds,
        )

    async def invoke_pnp_command(
        self,
        component_name,
        command_name,
        payload,
        device_id=None,
        module_id=None,
        connect_timeout_in_seconds=None,
        response_timeout_in_seconds=None,
    ):
        return await self.event_loop.run_in_executor(
            self.executor,
            self.inner_object.invoke_pnp_command,
            component_name,
            command_name,
            payload,
            device_id,
            module_id,
            connect_timeout_in_seconds,
            response_timeout_in_seconds,
        )

    async def get_pnp_properties(self, device_id=None, module_id=None):
        return await self.event_loop.run_in_executor(
            self.executor, self.inner_object.get_pnp_properties, device_id, module_id
        )

    async def update_pnp_properties(self, properties, device_id=None, module_id=None):
        return await self.event_loop.run_in_executor(
            self.executor,
            self.inner_object.update_pnp_properties,
            properties,
            device_id,
            module_id,
        )

    async def send_c2d(
        self,
        payload,
        properties,
        device_id=None,
        module_id=None,
    ):
        return await self.event_loop.run_in_executor(
            self.executor, self.inner_object.send_c2d, payload, properties, device_id, module_id
        )

    async def get_next_eventhub_arrival(
        self, device_id=None, module_id=None, block=True, timeout=20
    ):
        return await self.event_loop.run_in_executor(
            self.executor,
            self.inner_object.get_next_eventhub_arrival,
            device_id,
            module_id,
            block,
            timeout,
        )

    async def get_next_reported_patch_arrival(
        self, device_id=None, module_id=None, block=True, timeout=20
    ):
        return await self.event_loop.run_in_executor(
            self.executor,
            self.inner_object.get_next_reported_patch_arrival,
            device_id,
            module_id,
            block,
            timeout,
        )

    async def shutdown(self):
        return await self.event_loop.run_in_executor(self.executor, self.inner_object.shutdown)
