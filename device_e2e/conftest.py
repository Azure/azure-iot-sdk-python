# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import concurrent.futures
import test_config
import device_identity_helper
import const
import sys
import leak_tracker
from utils import get_random_message, get_random_dict, is_windows

# noqa: F401 defined in .flake8 file in root of repo

from drop_fixtures import dropper
from pnp_fixtures import (
    pnp_model_id,
    pnp_command_name,
    pnp_component_name,
    pnp_command_response_status,
    pnp_writable_property_name,
    pnp_read_only_property_name,
    pnp_ack_code,
    pnp_ack_description,
)
from client_fixtures import (
    client_kwargs,
    extra_client_kwargs,
    auto_connect,
    connection_retry,
    websockets,
    device_id,
    module_id,
    watches_events,
)

logging.basicConfig(level=logging.WARNING)
logging.getLogger("e2e").setLevel(level=logging.DEBUG)
logging.getLogger("paho").setLevel(level=logging.DEBUG)
logging.getLogger("azure.iot").setLevel(level=logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.fixture(scope="module")
def transport():
    return test_config.config.transport


@pytest.fixture(scope="module")
def executor():
    return concurrent.futures.ThreadPoolExecutor()


@pytest.fixture(scope="function")
def random_message():
    return get_random_message()


@pytest.fixture(scope="function")
def random_reported_props():
    return {const.TEST_CONTENT: get_random_dict()}


@pytest.fixture(scope="session")
def device_identity():

    if test_config.config.auth == test_config.AUTH_CONNECTION_STRING:
        device_identity = device_identity_helper.create_device_with_symmetric_key()
        logger.info(
            "Created connection string device with deviceId = {}".format(device_identity.device_id)
        )
    elif test_config.config.auth == test_config.AUTH_SYMMETRIC_KEY:
        device_identity = device_identity_helper.create_device_with_symmetric_key()
        logger.info(
            "Created symmetric key device with deviceId = {}".format(device_identity.device_id)
        )
    elif test_config.config.auth == test_config.AUTH_SAS_TOKEN:
        device_identity = device_identity_helper.create_device_with_sas()
        logger.info("Created sas token device with deviceId = {}".format(device_identity.device_id))
    elif test_config.config.auth in test_config.AUTH_CHOICES:
        # need to implement
        raise Exception("{} Auth not yet implemented".format(test_config.config.auth))
    else:
        raise Exception("config.auth invalid")

    yield device_identity

    logger.info("Deleting device with deviceId = {}".format(device_identity.device_id))
    device_identity_helper.delete_device(device_identity.device_id)


def pytest_addoption(parser):
    parser.addoption(
        "--transport",
        help="Transport to use for tests",
        type=str,
        choices=test_config.TRANSPORT_CHOICES,
        default=test_config.TRANSPORT_MQTT,
    )
    parser.addoption(
        "--auth",
        help="Auth to use for tests",
        type=str,
        choices=test_config.AUTH_CHOICES,
        default=test_config.AUTH_CONNECTION_STRING,
    )
    parser.addoption(
        "--identity",
        help="Identity (client type) to use for tests",
        type=str,
        choices=test_config.IDENTITY_CHOICES,
        default=test_config.IDENTITY_DEVICE,
    )


def pytest_configure(config):
    test_config.config.transport = config.getoption("transport")
    test_config.config.auth = config.getoption("auth")
    test_config.config.identity = config.getoption("identity")


def pytest_runtest_setup(item):
    # tests that use iptables need to be skipped on Windows
    if is_windows():
        for x in item.iter_markers("uses_iptables"):
            pytest.skip("test uses iptables")
            return
        for x in item.iter_markers("dropped_connection"):
            pytest.skip("test uses iptables")
            return

    item.leak_tracker = leak_tracker.LeakTracker()
    item.leak_tracker.add_tracked_module("azure.iot.device")
    item.leak_tracker.set_baseline()


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item, nextitem):
    print("CHECKING FOR LEAKS")
    if hasattr(item, "leak_tracker"):
        # Get rid of our fixtures so they don't cause leaks.
        # These 2 lines copied from `runtestprotocol` in pytest's `runner.py`
        item._request = False
        item.funcargs = None
        item.leak_tracker.check_for_new_leaks()
        del item.leak_tracker


collect_ignore = ["test_settings.py"]

# Ignore Async tests if below Python 3.5
if sys.version_info < (3, 5):
    collect_ignore.append("aio")
