# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import functools
import time
import e2e_settings
import logging
import datetime
from utils import create_client_object
from service_helper_sync import ServiceHelperSync
from azure.iot.device.iothub import IoTHubDeviceClient, IoTHubModuleClient

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.fixture(scope="function")
def brand_new_client(device_identity, client_kwargs, service_helper, device_id, module_id):
    service_helper.set_identity(device_id, module_id)

    # Keep this here.  It is useful to see this info inside the inside devops pipeline test failures.
    logger.info(
        "Connecting device_id={}, module_id={}, to hub={} at {} (UTC)".format(
            device_id, module_id, e2e_settings.IOTHUB_HOSTNAME, datetime.datetime.utcnow()
        )
    )

    client = create_client_object(
        device_identity, client_kwargs, IoTHubDeviceClient, IoTHubModuleClient
    )

    yield client

    logger.info("---------------------------------------")
    logger.info("test is complete.  Shutting down client")
    logger.info("---------------------------------------")

    client.shutdown()

    logger.info("-------------------------------------------")
    logger.info("test is complete.  client shutdown complete")
    logger.info("-------------------------------------------")


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

    logger.info("----------------------------")
    logger.info("shutting down service_helper")
    logger.info("----------------------------")

    service_helper.shutdown()

    logger.info("---------------------------------")
    logger.info("service helper shut down complete")
    logger.info("---------------------------------")
