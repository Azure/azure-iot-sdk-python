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
import iptables
import e2e_settings
from utils import get_random_message, get_random_dict, is_windows

# noqa: F401 defined in .flake8 file in root of repo

from drop_fixtures import dropper
from client_fixtures import (
    client_kwargs,
    auto_connect,
    connection_retry,
    websockets,
    device_id,
    module_id,
    sastoken_ttl,
    keep_alive,
)

logging.basicConfig(level=logging.WARNING)
logging.getLogger("e2e").setLevel(level=logging.DEBUG)
logging.getLogger("paho").setLevel(level=logging.DEBUG)
logging.getLogger("azure.iot").setLevel(level=logging.DEBUG)

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
    """
    This hook runs before parsing command line args.
    We use this to add args.
    """
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
    """
    Ths hook runs after parsing the command line, and before collecting tests.

    We use this to save command line options because these can affect which
    tests run and which tests get skipped.
    """
    test_config.config.transport = config.getoption("transport")
    test_config.config.auth = config.getoption("auth")
    test_config.config.identity = config.getoption("identity")


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """
    This hook runs for every test (after paramratizing), as part of the test setup.

    If a single function has parameters that make it run 8 times with different options,
    then this function will be called 8 times.

    We use this to skip tests based on command line args and to take our leak-check
    snapshot.
    """

    # reconnect in case a previously interrupted test run left our network disconnected
    iptables.reconnect_all(test_config.config.transport, e2e_settings.IOTHUB_HOSTNAME)

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


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem):
    """
    This hook is where the actual test runs.  We use hookwrapper=true because we
    want this hook to be a wrapper around other hooks.

    We use this to check the result of the test and "turn off" leak checking if the
    test fails.
    """

    # this yield runs the actual test.
    outcome = yield

    try:
        # this will raise if the outcome was an exception
        outcome.get_result()
    except Exception as e:
        if hasattr(pyfuncitem, "leak_tracker"):
            logger.info("Skipping leak tracking because of Exception {}".format(str(e) or type(e)))
            del pyfuncitem.leak_tracker
        raise


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item, nextitem):
    """
    This hook runs after the test is done tearing down.

    We use this to check for leaks.
    """
    if hasattr(item, "leak_tracker"):
        logger.info("CHECKING FOR LEAKS")
        # Get rid of our fixtures so they don't cause leaks.
        #
        # We need to do this because we have fixtures like `client`, which is an
        # example of the kind of object we're tracking.  If we leave any references
        # to the client object, it will show up as a leak.  `item._request` is
        # where the fixture values are stored, so, if we set item._request to False,
        # it gives the garbage collector a chance to collect everything used by
        # our fixtures, including, in this example. `client`.
        #
        # This is a bit of a hack, but we don't have a better place to do this, and
        # these 2 fields get set immediately after this hook returns, so we're not
        # hurting anything by doing this.

        # These 2 lines copied from `runtestprotocol` in pytest's `runner.py`
        item._request = False
        item.funcargs = None

        # now that fixtures are gone, we can check for leaks.  `check_for_new_leaks` will
        # call into the garbage collector to make sure everything is cleaned up before
        # we check.
        item.leak_tracker.check_for_new_leaks()
        del item.leak_tracker
        logger.info("DONE CHECKING FOR LEAKS")


collect_ignore = ["test_settings.py"]

# Ignore Async tests if below Python 3.5
if sys.version_info < (3, 5):
    collect_ignore.append("aio")
