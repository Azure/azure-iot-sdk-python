# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import functools
import time
import e2e_settings
from service_inproc import ServiceInproc
from azure.iot.device.iothub import IoTHubDeviceClient


@pytest.fixture(scope="function")
def brand_new_client(client_kwargs):
    return IoTHubDeviceClient.create_from_connection_string(
        e2e_settings.DEVICE_CONNECTION_STRING, **client_kwargs
    )


@pytest.fixture(scope="function")
def client(brand_new_client):
    client = brand_new_client

    client.connect()

    yield client

    client.shutdown()


@pytest.fixture(scope="module")
def service_client():
    service_client = ServiceInproc()
    time.sleep(1)
    yield service_client
    service_client.shutdown()


@pytest.fixture(scope="function")
def get_next_eventhub_arrival(service_client, device_id, module_id, watches_events):
    yield functools.partial(service_client.get_next_eventhub_arrival, device_id, module_id)


@pytest.fixture(scope="function")
def get_next_reported_patch_arrival(executor, service_client, device_id, module_id, watches_events):
    yield functools.partial(service_client.get_next_reported_patch_arrival, device_id, module_id)
