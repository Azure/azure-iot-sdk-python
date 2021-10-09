# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import functools
import time
import e2e_settings
import test_config
import logging
from utils import create_client_object
from service_helper_sync import ServiceHelperSync
from azure.iot.device.iothub import IoTHubDeviceClient, IoTHubModuleClient

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.fixture(scope="function")
def brand_new_client(device_identity, client_kwargs, service_helper, device_id, module_id):
    service_helper.start_watching(device_id, module_id)

    client = create_client_object(
        device_identity, client_kwargs, IoTHubDeviceClient, IoTHubModuleClient
    )

    yield client

    service_helper.stop_watching(device_id, module_id)

    client.shutdown()


@pytest.fixture(scope="function")
def client(brand_new_client):
    client = brand_new_client

    client.connect()

    yield client


@pytest.fixture(scope="module")
def service_helper():
    service_helper = ServiceHelperSync()
    time.sleep(3)
    yield service_helper
    service_helper.shutdown()


@pytest.fixture(scope="function")
def get_next_eventhub_arrival(service_helper):
    yield service_helper.get_next_eventhub_arrival


@pytest.fixture(scope="function")
def get_next_reported_patch_arrival(service_helper):
    yield service_helper.get_next_reported_patch_arrival
