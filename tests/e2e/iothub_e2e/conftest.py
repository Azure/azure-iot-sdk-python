# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import concurrent.futures
import test_config
import device_identity_helper
import const
import dev_utils.leak_tracker as leak_tracker_module
from dev_utils import test_env, get_random_message, get_random_dict, iptables
from utils import is_windows

from drop_fixtures import dropper  # noqa: F401
from client_fixtures import (  # noqa: F401
    client_kwargs,
    auto_connect,
    connection_retry,
    websockets,
    device_id,
    module_id,
    sastoken_ttl,
    keep_alive,
)  # noqa: F401

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(module)s:%(funcName)s:%(message)s",
    level=logging.WARNING,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("e2e").setLevel(level=logging.DEBUG)
logging.getLogger("paho").setLevel(level=logging.DEBUG)
logging.getLogger("azure.iot").setLevel(level=logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.fixture(scope="module")
def transport():
    return test_config.config.transport


@pytest.fixture(scope="session")
def executor():
    return concurrent.futures.ThreadPoolExecutor()


@pytest.fixture(scope="function")
def random_message():
    return get_random_message()


@pytest.fixture(scope="function")
def random_reported_props():
    return {const.TEST_CONTENT: get_random_dict()}


# define what objects are allowed to leak.
# `all_objects_can_leak` lists types which are allowed to leak an arbitrary number of objects.
# `one_object_can_leak` lists types where a single object is allowed to leak.
#    These are typically cases where an object that is in the initial object list gets replaced
#    during the run, such as a new `Alarm` being set to replace a previous `Alarm` object. Without
#    this suppression, the replacement object might otherwise show up as a leak.
all_objects_can_leak = []
one_object_can_leak = [
    "<class 'azure.iot.device.common.alarm.Alarm'>",
    "<class 'paho.mqtt.client.WebsocketWrapper'>",
]


def leak_tracker_filter(leaks):
    """
    Function to filter false positives out of a leak list.  Returns a new list after filtering
    is complete
    """
    for allowed_leak in all_objects_can_leak:
        # Remove all objects of a given type from the leak list.  This is useful for
        # suppressing known leaks until a bug can be fixed.
        new_list = []
        for leak in leaks:
            if str(leak.object_type) not in all_objects_can_leak:
                new_list.append(leak)
        leaks = new_list

    for allowed_leak in one_object_can_leak:
        # Remove a single object from the leak list.  This is useful in cases where
        # a new object gets allocated to replace an old object (like a new Alert replacing
        # an expired Alert).
        for i in range(len(leaks)):
            if str(leaks[i].object_type) == allowed_leak:
                del leaks[i]
                break

    return leaks


@pytest.fixture(scope="function")
def leak_tracker():
    tracker = leak_tracker_module.LeakTracker()
    tracker.track_module("azure.iot.device")
    tracker.track_module("paho")
    tracker.filter_callback = leak_tracker_filter
    return tracker


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
    This hook runs for every test (after parametrizing), as part of the test setup.

    If a single function has parameters that make it run 8 times with different options,
    then this function will be called 8 times.

    We use this to skip tests based on command line args and to take our leak-check
    snapshot.
    """

    # reconnect in case a previously interrupted test run left our network disconnected
    iptables.reconnect_all(test_config.config.transport, test_env.IOTHUB_HOSTNAME)

    # tests that use iptables need to be skipped on Windows
    if is_windows():
        for x in item.iter_markers("uses_iptables"):
            pytest.skip("test uses iptables")
            return
        for x in item.iter_markers("dropped_connection"):
            pytest.skip("test uses iptables")
            return

    # We have 2 leak trackers.
    #
    # 1. The `outer_leak_tracker` object attached to tests is called after `disconnect` or
    #    `shutdown` is called. This means it can only detect objects that survive `shutdown`.
    #
    # 2. The `leak_tracker` fixture is used within tests and needs to be manually invoked.
    #    This means it gets called before `shutdown`, so it can detect leaks that might otherwise
    #    get cleaned up.
    #
    # Of these 2, the `leak_tracker` fixture is more useful, but it does require manual steps.
    #
    item.outer_leak_tracker = leak_tracker_module.LeakTracker()
    item.outer_leak_tracker.track_module("azure.iot.device")
    item.outer_leak_tracker.track_module("paho")
    item.outer_leak_tracker.filter_callback = leak_tracker_filter
    item.outer_leak_tracker.set_initial_object_list()


@pytest.hookimpl(hookwrapper=True)
def pytest_exception_interact(node, call, report):
    e = call.excinfo.value
    logger.error("------------------------------------------------------")
    logger.error("EXCEPTION RAISED in {} phase: {}".format(report.when, str(e) or type(e)))
    logger.error("------------------------------------------------------")

    if hasattr(node, "outer_leak_tracker"):
        logger.info("Skipping leak tracking because of Exception {}".format(str(e) or type(e)))
        del node.outer_leak_tracker

    yield


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item, nextitem):
    """
    This hook runs after the test is done tearing down.

    We use this to check for leaks.
    """
    if hasattr(item, "outer_leak_tracker"):
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

        # now that fixtures are gone, we can check for leaks.  `check_for_leaks` will
        # call into the garbage collector to make sure everything is cleaned up before
        # we check.
        item.outer_leak_tracker.check_for_leaks()
        del item.outer_leak_tracker
        logger.info("DONE CHECKING FOR LEAKS")


collect_ignore = ["test_settings.py"]
