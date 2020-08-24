# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import threading
import time
from azure.iot.device.common import handle_exceptions
from azure.iot.device.iothub.sync_handler_manager import SyncHandlerManager, HandlerManagerException
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
        "Creates and starts a daemon Thread for the correpsonding handler runner when value is set to a function"
    )
    def test_thread_created(self, handler_name, handler_name_internal, handler_manager, handler):
        assert handler_manager._handler_runners[handler_name_internal] is None
        setattr(handler_manager, handler_name, handler)
        assert isinstance(handler_manager._handler_runners[handler_name_internal], threading.Thread)
        assert handler_manager._handler_runners[handler_name_internal].daemon is True

    @pytest.mark.it(
        "Stops the corresponding handler runner and completes any existing daemon Thread for it when the value is set back to None"
    )
    def test_thread_removed(self, handler_name, handler_name_internal, handler_manager, handler):
        # Set handler
        setattr(handler_manager, handler_name, handler)
        # Thread has been created and is alive
        t = handler_manager._handler_runners[handler_name_internal]
        assert isinstance(t, threading.Thread)
        assert t.is_alive()
        # Set the handler back to None
        setattr(handler_manager, handler_name, None)
        # Thread has finished and the manager no longer has a reference to it
        assert not t.is_alive()
        assert handler_manager._handler_runners[handler_name_internal] is None

    @pytest.mark.it(
        "Does not delete, remove, or replace the Thread for the corresponding handler runner, when the updated with a new function value"
    )
    def test_thread_unchanged_by_handler_update(
        self, handler_name, handler_name_internal, handler_manager, handler
    ):
        # Set the handler
        setattr(handler_manager, handler_name, handler)
        # Thread has been crated and is alive
        t = handler_manager._handler_runners[handler_name_internal]
        assert isinstance(t, threading.Thread)
        assert t.is_alive()

        # Set new handler
        def new_handler(arg):
            pass

        setattr(handler_manager, handler_name, new_handler)
        assert handler_manager._handler_runners[handler_name_internal] is t
        assert t.is_alive()

    @pytest.mark.it(
        "Is invoked by the runner when the Inbox corresponding to the handler receives an object, passing that object to the handler"
    )
    def test_handler_invoked(self, mocker, handler_name, handler_manager, inbox):
        # Set the handler
        mock_handler = mocker.MagicMock()
        setattr(handler_manager, handler_name, mock_handler)
        # Handler has not been called
        assert mock_handler.call_count == 0

        # Add an item to corresponding inbox, triggering the handler
        mock_obj = mocker.MagicMock()
        inbox._put(mock_obj)
        time.sleep(0.1)

        # Handler has been called with the item from the inbox
        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call(mock_obj)

    @pytest.mark.it(
        "Is invoked by the runner every time the Inbox corresponding to the handler receives an object"
    )
    def test_handler_invoked_multiple(self, mocker, handler_name, handler_manager, inbox):
        # Set the handler
        mock_handler = mocker.MagicMock()
        setattr(handler_manager, handler_name, mock_handler)
        # Handler has not been called
        assert mock_handler.call_count == 0

        # Add 5 items to the corresponding inbox, triggering the handler
        for _ in range(5):
            inbox._put(mocker.MagicMock())
        time.sleep(0.1)

        # Handler has been called 5 times
        assert mock_handler.call_count == 5

    @pytest.mark.it(
        "Is invoked for every item already in the corresponding Inbox at the moment of handler removal"
    )
    def test_handler_resolve_pending_items_before_handler_removal(
        self, mocker, handler_name, handler_manager, inbox
    ):
        # Set the handler
        mock_handler = mocker.MagicMock()
        setattr(handler_manager, handler_name, mock_handler)
        # Add 100 items to the associated inbox (enough to build up a backlog)
        for _ in range(100):
            inbox._put(mocker.MagicMock())
        # Inbox is not empty - i.e. the handler has not yet been called for every item in the inbox
        assert not inbox.empty()
        assert mock_handler.call_count != 100
        # Remove the handler
        setattr(handler_manager, handler_name, None)
        time.sleep(0.1)
        assert inbox.empty()
        assert mock_handler.call_count == 100

        # NOTE: This doesn't account for the multithreaded case where the inbox is being continually added to,
        # even after the handler has been removed. There isn't really a good way to test that because the adding is
        # continuous, and unsetting the handler is not atomic, i.e. in the time it takes to remove the handler, many
        # new things could be added to the inbox. We can never get a accurate number on inbox size to show that
        # everything prior to the unsetting of the handler during the execution of the unsetting will get resolved.
        # Just take my word for it + read the source code to see that this is true due to the sentinel pattern.
        #
        # NOTE 2: I know the above note probably doesn't make sense to anyone who hasn't tried to test this edge case.
        # Go ahead and try to test the multithread edge case, come back, read that note again, and it'll
        # probably make sense

    @pytest.mark.it(
        "Sends a HandlerManagerException to the background exception handler if any exception is raised during its invocation"
    )
    def test_exception_in_handler(
        self, mocker, handler_name, handler_manager, inbox, arbitrary_exception
    ):
        background_exc_spy = mocker.spy(handle_exceptions, "handle_background_exception")
        # Handler will raise exception when called
        mock_handler = mocker.MagicMock()
        mock_handler.side_effect = arbitrary_exception
        # Set handler
        setattr(handler_manager, handler_name, mock_handler)
        # Handler has not been called
        assert mock_handler.call_count == 0
        # Background exception handler has not been called
        assert background_exc_spy.call_count == 0
        # Add an item to corresponding inbox, triggering the handler
        inbox._put(mocker.MagicMock())
        time.sleep(0.1)
        # Handler has now been called
        assert mock_handler.call_count == 1
        # Background exception handler was called
        assert background_exc_spy.call_count == 1
        e = background_exc_spy.call_args[0][0]
        assert isinstance(e, HandlerManagerException)
        assert e.__cause__ is arbitrary_exception

    @pytest.mark.it(
        "Can be updated with a new value that the corresponding handler runner will immediately begin using for handler invocations instead"
    )
    def test_handler_update_handler(self, mocker, handler_name, handler_manager, inbox):
        def handler(arg):
            # Invoking handler replaces the set handler with a mock
            setattr(handler_manager, handler_name, mocker.MagicMock())

        setattr(handler_manager, handler_name, handler)

        inbox._put(mocker.MagicMock())
        time.sleep(0.1)
        # Handler has been replaced with a mock, but the mock has not been invoked
        assert getattr(handler_manager, handler_name) is not handler
        assert getattr(handler_manager, handler_name).call_count == 0
        # Add a new item to the inbox
        inbox._put(mocker.MagicMock())
        time.sleep(0.1)
        # The mock was now called
        assert getattr(handler_manager, handler_name).call_count == 1


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
