# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import functools
import time
import e2e_settings
import test_config
import logging
from service_helper_sync import ServiceHelperSync
from azure.iot.device.iothub import IoTHubDeviceClient, IoTHubModuleClient

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.fixture(scope="function")
def brand_new_client(client_kwargs):
    client = None

    if test_config.config.identity == test_config.IDENTITY_DEVICE_CLIENT:
        ClientClass = IoTHubDeviceClient
    elif test_config.config.identity == test_config.IDENTITY_MODULE_CLIENT:
        ClientClass = IoTHubModuleClient
    else:
        raise Exception("config.identity invalid")

    if test_config.config.auth == test_config.AUTH_CONNECTION_STRING:
        # TODO: This is currently using a connection string stored in _e2e_settings.xml.  This will move to be a dynamically created identity similar to the way node's device_identity_helper.js works.
        logger.info(
            "Creating {} using create_from_connection_string with kwargs={}".format(
                ClientClass, client_kwargs
            )
        )
        client = ClientClass.create_from_connection_string(
            e2e_settings.DEVICE_CONNECTION_STRING, **client_kwargs
        )
    elif test_config.config.auth == test_config.X509:
        # need to implement
        raise Exception("X509 Auth not yet implemented")
    else:
        raise Exception("config.auth invalid")

    yield client

    client.shutdown()


@pytest.fixture(scope="function")
def client(brand_new_client):
    client = brand_new_client

    client.connect()

    yield client


@pytest.fixture(scope="module")
def service_helper():
    service_helper = ServiceHelperSync()
    time.sleep(1)
    yield service_helper
    service_helper.shutdown()


@pytest.fixture(scope="function")
def get_next_eventhub_arrival(service_helper, device_id, module_id, watches_events):
    yield functools.partial(service_helper.get_next_eventhub_arrival, device_id, module_id)


@pytest.fixture(scope="function")
def get_next_reported_patch_arrival(executor, service_helper, device_id, module_id, watches_events):
    yield functools.partial(service_helper.get_next_reported_patch_arrival, device_id, module_id)
