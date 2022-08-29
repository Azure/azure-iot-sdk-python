# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import asyncio
from dev_utils import test_env, ServiceHelper
import logging
import datetime
import json
import retry_async
from utils import create_client_object
from azure.iot.device.iothub.aio import IoTHubDeviceClient, IoTHubModuleClient

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.hookimpl(hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem):
    """
    pytest hook that gets called for running an individual test. We use this to store
    retry statistics for this test in the `pyfuncitem` for the test.
    """

    # Reset tests before running the test
    retry_async.reset_retry_stats()

    try:
        # Run the test. We can do this because hookwrapper=True
        yield
    finally:
        # If we actually collected any stats, store them.
        if retry_async.retry_stats:
            pyfuncitem.retry_stats = retry_async.retry_stats


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """
    pytest hook that gets called at the end of a test session. We use this to
    log stress results to stdout.
    """

    # Loop through all of our tests and print contents of `retry_stats` if it exists.
    printed_header = False
    for item in session.items:
        retry_stats = getattr(item, "retry_stats", None)
        if retry_stats:
            if not printed_header:
                print(
                    "================================ retry summary ================================="
                )
                printed_header = True
            print("Retry stats for {}".format(item.name))
            print(json.dumps(retry_stats, indent=2))
            print("-----------------------------------")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def brand_new_client(device_identity, client_kwargs, service_helper, device_id, module_id):
    service_helper.set_identity(device_id, module_id)

    # Keep this here.  It is useful to see this info inside the inside devops pipeline test failures.
    logger.info(
        "Connecting device_id={}, module_id={}, to hub={} at {} (UTC)".format(
            device_id, module_id, test_env.IOTHUB_HOSTNAME, datetime.datetime.utcnow()
        )
    )

    client = create_client_object(
        device_identity, client_kwargs, IoTHubDeviceClient, IoTHubModuleClient
    )

    yield client

    logger.info("---------------------------------------")
    logger.info("test is complete.  Shutting down client")
    logger.info("---------------------------------------")

    await client.shutdown()

    logger.info("-------------------------------------------")
    logger.info("test is complete.  client shutdown complete")
    logger.info("-------------------------------------------")


@pytest.fixture(scope="function")
async def client(brand_new_client):
    client = brand_new_client

    await client.connect()

    yield client


@pytest.fixture(scope="session")
async def service_helper(event_loop, executor):
    service_helper = ServiceHelper(
        iothub_connection_string=test_env.IOTHUB_CONNECTION_STRING,
        eventhub_connection_string=test_env.EVENTHUB_CONNECTION_STRING,
        eventhub_consumer_group=test_env.EVENTHUB_CONSUMER_GROUP,
        event_loop=event_loop,
        executor=executor,
    )
    yield service_helper

    logger.info("----------------------------")
    logger.info("shutting down service_helper")
    logger.info("----------------------------")

    await service_helper.shutdown()

    logger.info("---------------------------------")
    logger.info("service helper shut down complete")
    logger.info("---------------------------------")
