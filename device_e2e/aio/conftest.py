# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import asyncio
import functools
import e2e_settings
import test_config
import logging
from utils import create_client_object
from service_helper import ServiceHelper
from azure.iot.device.iothub.aio import IoTHubDeviceClient, IoTHubModuleClient

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def brand_new_client(device_identity, client_kwargs, service_helper, device_id, module_id):
    service_helper.start_watching(device_id, module_id)

    client = create_client_object(
        device_identity, client_kwargs, IoTHubDeviceClient, IoTHubModuleClient
    )

    yield client

    service_helper.stop_watching(device_id, module_id)

    await client.shutdown()


@pytest.fixture(scope="function")
async def client(brand_new_client):
    client = brand_new_client

    await client.connect()

    yield client


@pytest.fixture(scope="module")
async def service_helper(event_loop, executor):
    service_helper = ServiceHelper(event_loop, executor)
    await asyncio.sleep(3)
    yield service_helper
    print("shutting down")
    await service_helper.shutdown()
