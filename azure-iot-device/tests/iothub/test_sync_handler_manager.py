# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import threading
from azure.iot.device.iothub.sync_handler_manager import SyncHandlerManager
from azure.iot.device.iothub.sync_handler_manager import MESSAGE, METHOD, TWIN_DP_PATCH
from azure.iot.device.iothub.inbox_manager import InboxManager
from azure.iot.device.iothub.sync_inbox import SyncClientInbox

logging.basicConfig(level=logging.DEBUG)

# NOTE ON TEST IMPLEMENTATION:
# Despite having significant shared implementation between the sync and async handler managers,
# there are not shared tests. This is because while both have the same set of requirements and
# APIs, the internal implementation is different to an extent that it simply isn't really possible
# to test them to an appropriate degree of correctness with a shared set of tests.
# This means we must be very careful to always change both test modules when a change is made to
# shared behavior, or when shared features are added.

all_internal_handlers = [MESSAGE, METHOD, TWIN_DP_PATCH]
all_handlers = [s.lstrip("_") for s in all_internal_handlers]


@pytest.fixture
def inbox_manager(mocker):
    return InboxManager(inbox_type=SyncClientInbox)


@pytest.fixture
def handler_manager(inbox_manager):
    return SyncHandlerManager(inbox_manager)


@pytest.fixture
def handler():
    def some_handler_fn(arg):
        pass

    return some_handler_fn


@pytest.mark.describe("SyncHandlerManager - Instantiation")
class TestInstantiation(object):
    @pytest.mark.it("Initializes handler properties to None")
    @pytest.mark.parametrize("handler_name", all_handlers)
    def test_handlers(self, inbox_manager, handler_name):
        hm = SyncHandlerManager(inbox_manager)
        assert getattr(hm, handler_name) is None

    @pytest.mark.it("Initializes handler runner thread references to None")
    @pytest.mark.parametrize("handler_name", all_internal_handlers, ids=all_handlers)
    def test_handler_runners(self, inbox_manager, handler_name):
        hm = SyncHandlerManager(inbox_manager)
        assert hm._handler_runners[handler_name] is None


class SharedHandlerPropertyTests(object):

    # NOTE: If there is ever any deviation in the convention of what the internal names of handlers
    # are other than just a prefixed "_", we'll have to move this fixture to the child classes so
    # it can be unique to each handler
    @pytest.fixture
    def handler_name_internal(self, handler_name):
        return "_" + handler_name

    @pytest.mark.it("Can be both read and written to")
    def test_read_write(self, handler_name, handler_manager, handler):
        assert getattr(handler_manager, handler_name) is None
        setattr(handler_manager, handler_name, handler)
        assert getattr(handler_manager, handler_name) is handler
        setattr(handler_manager, handler_name, None)
        assert getattr(handler_manager, handler_name) is None

    @pytest.mark.it(
        "Creates and starts a Thread for the correpsonding handler runner when value is set to a function"
    )
    def test_thread_created(self, handler_name, handler_name_internal, handler_manager, handler):
        assert handler_manager._handler_runners[handler_name_internal] is None
        setattr(handler_manager, handler_name, handler)
        assert isinstance(handler_manager._handler_runners[handler_name_internal], threading.Thread)


@pytest.mark.describe("SyncHandlerManager - PROPERTY: .on_message_received")
class TestSyncHandlerManagerPropertyOnMessageReceived(SharedHandlerPropertyTests):
    @pytest.fixture
    def handler_name(self):
        return "on_message_received"

    @pytest.fixture
    def inbox(self, inbox_manager):
        return inbox_manager.get_unified_message_inbox()


@pytest.mark.describe("SyncHandlerManager - PROPERTY: .on_method_request_received")
class TestSyncHandlerManagerPropertyOnMethodRequestReceived(SharedHandlerPropertyTests):
    @pytest.fixture
    def handler_name(self):
        return "on_method_request_received"

    @pytest.fixture
    def inbox(self, inbox_manager):
        return inbox_manager.get_method_request_inbox()


@pytest.mark.describe("SyncHandlerManager - PROPERTY: .on_twin_desired_properties_patch_received")
class TestSyncHandlerManagerPropertyOnTwinDesiredPropertiesPatchReceived(
    SharedHandlerPropertyTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_twin_desired_properties_patch_received"

    @pytest.fixture
    def inbox(self, inbox_manager):
        return inbox_manager.get_twin_patch_inbox()
