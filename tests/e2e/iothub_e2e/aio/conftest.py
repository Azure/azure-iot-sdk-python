# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import asyncio
from dev_utils import test_env, ServiceHelper
import logging
import datetime
from utils import create_session

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def session(device_identity, client_kwargs, service_helper, device_id, module_id):
    service_helper.set_identity(device_id, module_id)

    # Keep this here.  It is useful to see this info inside the inside devops pipeline test failures.
    logger.info(
        "Connecting device_id={}, module_id={}, to hub={} at {} (UTC)".format(
            device_id, module_id, test_env.IOTHUB_HOSTNAME, datetime.datetime.utcnow()
        )
    )

    client = create_session(device_identity, client_kwargs)

    yield client

    logger.info("---------------------------------------")
    logger.info("test is complete.")
    logger.info("---------------------------------------")


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
