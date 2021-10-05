# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import asyncio
import functools
import time
import e2e_settings
import test_config
from service_helper import ServiceHelper
from azure.iot.device.iothub.aio import IoTHubDeviceClient, IoTHubModuleClient


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def brand_new_client(client_kwargs):
    client = None

    if test_config.config.identity == test_config.IDENTITY_DEVICE_CLIENT:
        ClientClass = IoTHubDeviceClient
    elif test_config.config.identity == test_config.IDENTITY_MODULE_CLIENT:
        ClientClass = IoTHubModuleClient
    else:
        raise Exception("config.identity invalid")

    if test_config.config.transport not in test_config.TRANSPORT_CHOICES:
        raise Exception("config.transport invalid")
    websockets = test_config.config.transport == test_config.TRANSPORT_MQTT_WS
    if test_config.config.auth == test_config.AUTH_CONNECTION_STRING:
        # TODO: This is currently using a connection string stored in _e2e_settings.xml.  This will move to be a dynamically created identity similar to the way node's device_identity_helper.js works.
        client = ClientClass.create_from_connection_string(
            e2e_settings.DEVICE_CONNECTION_STRING, websockets=websockets, **client_kwargs
        )
    elif test_config.config.auth == test_config.X509:
        # need to implement
        raise Exception("X509 Auth not yet implemented")
    else:
        raise Exception("config.auth invalid")

    yield client

    await client.shutdown()


@pytest.fixture(scope="function")
async def client(brand_new_client):
    client = brand_new_client

    await client.connect()

    yield client


@pytest.fixture(scope="module")
async def service_helper(event_loop, executor):
    service_helper = ServiceHelper(event_loop, executor)
    time.sleep(1)
    yield service_helper
    print("shutting down")
    await service_helper.shutdown()


@pytest.fixture(scope="function")
def get_next_eventhub_arrival(
    event_loop, executor, service_helper, device_id, module_id, watches_events  # noqa: F811
):
    yield functools.partial(service_helper.get_next_eventhub_arrival, device_id, module_id)


@pytest.fixture(scope="function")
def get_next_reported_patch_arrival(
    event_loop, executor, service_helper, device_id, module_id, watches_events  # noqa: F811
):
    yield functools.partial(service_helper.get_next_reported_patch_arrival, device_id, module_id)
