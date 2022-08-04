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
from azure.iot.device.iothub import client_event
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

# NOTE ON TIMING/DELAY
# Several tests in this module have sleeps/delays in their implementation due to needing to wait
# for things to happen in other threads.

all_internal_receiver_handlers = [MESSAGE, METHOD, TWIN_DP_PATCH]
all_internal_client_event_handlers = [
    "_on_connection_state_change",
    "_on_new_sastoken_required",
    "_on_background_exception",
]
all_internal_handlers = all_internal_receiver_handlers + all_internal_client_event_handlers
all_receiver_handlers = [s.lstrip("_") for s in all_internal_receiver_handlers]
all_client_event_handlers = [s.lstrip("_") for s in all_internal_client_event_handlers]
all_handlers = all_receiver_handlers + all_client_event_handlers


class ThreadsafeMock(object):
    """This class provides (some) Mock functionality in a threadsafe manner, specifically, it
    ensures that the 'call_count' attribute will be accurate when the mock is called from another
    thread.

    It does not cover ALL mock functionality, but more features could be added to it as necessary
    """

    def __init__(self):
        self.call_count = 0
        self.lock = threading.Lock()

    def __call__(self, *args, **kwargs):
        with self.lock:
            self.call_count += 1


@pytest.fixture
def inbox_manager(mocker):
    return InboxManager(inbox_type=SyncClientInbox)


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

    @pytest.mark.it("Initializes receiver handler runner thread references to None")
    @pytest.mark.parametrize(
        "handler_name", all_internal_receiver_handlers, ids=all_receiver_handlers
    )
    def test_receiver_handler_runners(self, inbox_manager, handler_name):
        hm = SyncHandlerManager(inbox_manager)
        assert hm._receiver_handler_runners[handler_name] is None

    @pytest.mark.it("Initializes client event handler runner thread reference to None")
    def test_client_event_handler_runner(self, inbox_manager):
        hm = SyncHandlerManager(inbox_manager)
        assert hm._client_event_runner is None


@pytest.mark.describe("SyncHandlerManager - .stop()")
class TestStop(object):
    @pytest.fixture(
        params=[
            "No handlers running",
            "Some receiver handlers running",
            "Some client event handlers running",
            "Some receiver and some client event handlers running",
            "All handlers running",
        ]
    )
    def handler_manager(self, request, inbox_manager, handler):
        hm = SyncHandlerManager(inbox_manager)
        if request.param == "Some receiver handlers running":
            # Set an arbitrary receiver handler
            hm.on_message_received = handler
        elif request.param == "Some client event handlers running":
            # Set an arbitrary client event handler
            hm.on_connection_state_change = handler
        elif request.param == "Some receiver and some client event handlers running":
            # Set an arbitrary receiver and client event handler
            hm.on_message_received = handler
            hm.on_connection_state_change = handler
        elif request.param == "All handlers running":
            # NOTE: this sets all handlers to be the same fn, but this doesn't really
            # make a difference in this context
            for handler_name in all_handlers:
                setattr(hm, handler_name, handler)
        yield hm
        hm.stop()

    @pytest.mark.it("Stops all currently running handlers")
    def test_stop_all(self, handler_manager):
        handler_manager.stop()
        for handler_name in all_internal_receiver_handlers:
            assert handler_manager._receiver_handler_runners[handler_name] is None
        assert handler_manager._client_event_runner is None

    @pytest.mark.it(
        "Stops only the currently running receiver handlers if the 'receiver_handlers_only' parameter is True"
    )
    def test_stop_only_receiver_handlers(self, handler_manager):
        if handler_manager._client_event_runner is not None:
            client_event_handlers_running = True
        else:
            client_event_handlers_running = False

        handler_manager.stop(receiver_handlers_only=True)

        # All receiver handlers have stopped
        for handler_name in all_internal_receiver_handlers:
            assert handler_manager._receiver_handler_runners[handler_name] is None
        # If the client event handlers were running, they are STILL running
        if client_event_handlers_running:
            assert handler_manager._client_event_runner is not None

    @pytest.mark.it("Completes all pending handler invocations before stopping the runner(s)")
    def test_completes_pending(self, mocker, inbox_manager):
        hm = SyncHandlerManager(inbox_manager)

        # NOTE: We use two handlers arbitrarily here to show this happens for all handler runners
        mock_msg_handler = ThreadsafeMock()
        mock_mth_handler = ThreadsafeMock()
        msg_inbox = inbox_manager.get_unified_message_inbox()
        mth_inbox = inbox_manager.get_method_request_inbox()
        for _ in range(200):  # sufficiently many items so can't complete quickly
            msg_inbox.put(mocker.MagicMock())
            mth_inbox.put(mocker.MagicMock())

        hm.on_message_received = mock_msg_handler
        hm.on_method_request_received = mock_mth_handler
        assert mock_msg_handler.call_count < 200
        assert mock_mth_handler.call_count < 200
        hm.stop()
        time.sleep(0.1)
        assert mock_msg_handler.call_count == 200
        assert mock_mth_handler.call_count == 200
        assert msg_inbox.empty()
        assert mth_inbox.empty()


@pytest.mark.describe("SyncHandlerManager - .ensure_running()")
class TestEnsureRunning(object):
    @pytest.fixture(
        params=[
            "All handlers set, all stopped",
            "All handlers set, receivers stopped, client events running",
            "All handlers set, all running",
            "Some receiver and client event handlers set, all stopped",
            "Some receiver and client event handlers set, receivers stopped, client events running",
            "Some receiver and client event handlers set, all running",
            "Some receiver handlers set, all stopped",
            "Some receiver handlers set, all running",
            "Some client event handlers set, all stopped",
            "Some client event handlers set, all running",
            "No handlers set",
        ]
    )
    def handler_manager(self, request, inbox_manager, handler):
        # NOTE: this sets all handlers to be the same fn, but this doesn't really
        # make a difference in this context
        hm = SyncHandlerManager(inbox_manager)

        if request.param == "All handlers set, all stopped":
            for handler_name in all_handlers:
                setattr(hm, handler_name, handler)
            hm.stop()
        elif request.param == "All handlers set, receivers stopped, client events running":
            for handler_name in all_handlers:
                setattr(hm, handler_name, handler)
            hm.stop(receiver_handlers_only=True)
        elif request.param == "All handlers set, all running":
            for handler_name in all_handlers:
                setattr(hm, handler_name, handler)
        elif request.param == "Some receiver and client event handlers set, all stopped":
            hm.on_message_received = handler
            hm.on_method_request_received = handler
            hm.on_connection_state_change = handler
            hm.on_new_sastoken_required = handler
            hm.stop()
        elif (
            request.param
            == "Some receiver and client event handlers set, receivers stopped, client events running"
        ):
            hm.on_message_received = handler
            hm.on_method_request_received = handler
            hm.on_connection_state_change = handler
            hm.on_new_sastoken_required = handler
            hm.stop(receiver_handlers_only=True)
        elif request.param == "Some receiver and client event handlers set, all running":
            hm.on_message_received = handler
            hm.on_method_request_received = handler
            hm.on_connection_state_change = handler
            hm.on_new_sastoken_required = handler
        elif request.param == "Some receiver handlers set, all stopped":
            hm.on_message_received = handler
            hm.on_method_request_received = handler
            hm.stop()
        elif request.param == "Some receiver handlers set, all running":
            hm.on_message_received = handler
            hm.on_method_request_received = handler
        elif request.param == "Some client event handlers set, all stopped":
            hm.on_connection_state_change = handler
            hm.on_new_sastoken_required = handler
            hm.stop()
        elif request.param == "Some client event handlers set, all running":
            hm.on_connection_state_change = handler
            hm.on_new_sastoken_required = handler

        yield hm
        hm.stop()

    @pytest.mark.it(
        "Starts handler runners for any handler that is set, but does not have a handler runner running"
    )
    def test_starts_runners_if_necessary(self, handler_manager):
        handler_manager.ensure_running()

        # Check receiver handlers
        for handler_name in all_receiver_handlers:
            if getattr(handler_manager, handler_name) is not None:
                # NOTE: this assumes the convention of internal names being the name of a handler
                # prefixed with a "_". If this ever changes, you must change this test.
                assert handler_manager._receiver_handler_runners["_" + handler_name] is not None

        # Check client event handlers
        for handler_name in all_client_event_handlers:
            if getattr(handler_manager, handler_name) is not None:
                assert handler_manager._client_event_runner is not None
                # don't need to check the rest of the handlers since they all share a runner
                break


# ##############
# # PROPERTIES #
# ##############


class SharedHandlerPropertyTests(object):
    @pytest.fixture
    def handler_manager(self, inbox_manager):
        hm = SyncHandlerManager(inbox_manager)
        yield hm
        hm.stop()

    # NOTE: We use setattr() and getattr() in these tests so they're generic to all properties.
    # This is functionally identical to doing explicit assignment to a property, it just
    # doesn't read quite as well.

    @pytest.mark.it("Can be both read and written to")
    def test_read_write(self, handler_name, handler_manager, handler):
        assert getattr(handler_manager, handler_name) is None
        setattr(handler_manager, handler_name, handler)
        assert getattr(handler_manager, handler_name) is handler
        setattr(handler_manager, handler_name, None)
        assert getattr(handler_manager, handler_name) is None


class SharedReceiverHandlerPropertyTests(SharedHandlerPropertyTests):
    # NOTE: If there is ever any deviation in the convention of what the internal names of handlers
    # are other than just a prefixed "_", we'll have to move this fixture to the child classes so
    # it can be unique to each handler
    @pytest.fixture
    def handler_name_internal(self, handler_name):
        return "_" + handler_name

    @pytest.mark.it(
        "Creates and starts a daemon Thread for the corresponding handler runner when value is set to a function"
    )
    def test_thread_created(self, handler_name, handler_name_internal, handler_manager, handler):
        assert handler_manager._receiver_handler_runners[handler_name_internal] is None
        setattr(handler_manager, handler_name, handler)
        assert isinstance(
            handler_manager._receiver_handler_runners[handler_name_internal], threading.Thread
        )
        assert handler_manager._receiver_handler_runners[handler_name_internal].daemon is True

    @pytest.mark.it(
        "Stops the corresponding handler runner and completes any existing daemon Thread for it when the value is set back to None"
    )
    def test_thread_removed(self, handler_name, handler_name_internal, handler_manager, handler):
        # Set handler
        setattr(handler_manager, handler_name, handler)
        # Thread has been created and is alive
        t = handler_manager._receiver_handler_runners[handler_name_internal]
        assert isinstance(t, threading.Thread)
        assert t.is_alive()
        # Set the handler back to None
        setattr(handler_manager, handler_name, None)
        # Thread has finished and the manager no longer has a reference to it
        assert not t.is_alive()
        assert handler_manager._receiver_handler_runners[handler_name_internal] is None

    @pytest.mark.it(
        "Does not delete, remove, or replace the Thread for the corresponding handler runner, when updated with a new function value"
    )
    def test_thread_unchanged_by_handler_update(
        self, handler_name, handler_name_internal, handler_manager, handler
    ):
        # Set the handler
        setattr(handler_manager, handler_name, handler)
        # Thread has been crated and is alive
        t = handler_manager._receiver_handler_runners[handler_name_internal]
        assert isinstance(t, threading.Thread)
        assert t.is_alive()

        # Set new handler
        def new_handler(arg):
            pass

        setattr(handler_manager, handler_name, new_handler)
        assert handler_manager._receiver_handler_runners[handler_name_internal] is t
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
        inbox.put(mock_obj)
        time.sleep(0.1)

        # Handler has been called with the item from the inbox
        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call(mock_obj)

    @pytest.mark.it(
        "Is invoked by the runner every time the Inbox corresponding to the handler receives an object"
    )
    def test_handler_invoked_multiple(self, mocker, handler_name, handler_manager, inbox):
        # Set the handler
        mock_handler = ThreadsafeMock()
        setattr(handler_manager, handler_name, mock_handler)
        # Handler has not been called
        assert mock_handler.call_count == 0

        # Add 5 items to the corresponding inbox, triggering the handler
        for _ in range(5):
            inbox.put(mocker.MagicMock())
        time.sleep(0.2)

        # Handler has been called 5 times
        assert mock_handler.call_count == 5

    @pytest.mark.it(
        "Is invoked for every item already in the corresponding Inbox at the moment of handler removal"
    )
    def test_handler_resolve_pending_items_before_handler_removal(
        self, mocker, handler_name, handler_manager, inbox
    ):
        # Use a threadsafe mock to ensure accurate counts
        mock_handler = ThreadsafeMock()
        assert inbox.empty()
        # Queue up a bunch of items in the inbox
        for _ in range(100):
            inbox.put(mocker.MagicMock())
        # The handler has not yet been called
        assert mock_handler.call_count == 0
        # Items are still in the inbox
        assert not inbox.empty()
        # Set the handler
        setattr(handler_manager, handler_name, mock_handler)
        # The handler has not yet been called for everything that was in the inbox
        # NOTE: I'd really like to show that the handler call count is also > 0 here, but
        # it's pretty difficult to make the timing work
        assert mock_handler.call_count < 100

        # Immediately remove the handler
        setattr(handler_manager, handler_name, None)
        # Wait to give a chance for the handler runner to finish calling everything
        time.sleep(0.2)
        # Despite removal, handler has been called for everything that was in the inbox at the
        # time of the removal
        assert mock_handler.call_count == 100
        assert inbox.empty()

        # Add some more items
        for _ in range(100):
            inbox.put(mocker.MagicMock())
        # Wait to give a chance for the handler to be called (it won't)
        time.sleep(0.2)
        # Despite more items added to inbox, no further handler calls have been made beyond the
        # initial calls that were made when the original items were added
        assert mock_handler.call_count == 100

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
        inbox.put(mocker.MagicMock())
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

        inbox.put(mocker.MagicMock())
        time.sleep(0.1)
        # Handler has been replaced with a mock, but the mock has not been invoked
        assert getattr(handler_manager, handler_name) is not handler
        assert getattr(handler_manager, handler_name).call_count == 0
        # Add a new item to the inbox
        inbox.put(mocker.MagicMock())
        time.sleep(0.1)
        # The mock was now called
        assert getattr(handler_manager, handler_name).call_count == 1


class SharedClientEventHandlerPropertyTests(SharedHandlerPropertyTests):
    @pytest.fixture
    def inbox(self, inbox_manager):
        return inbox_manager.get_client_event_inbox()

    @pytest.mark.it(
        "Creates and starts a daemon Thread for the Client Event handler runner when value is set to a function if the Client Event handler runner does not already exist"
    )
    def test_no_client_event_runner(self, handler_name, handler_manager, handler):
        assert handler_manager._client_event_runner is None
        setattr(handler_manager, handler_name, handler)
        t = handler_manager._client_event_runner
        assert isinstance(t, threading.Thread)
        assert t.daemon is True

    @pytest.mark.it(
        "Does not modify the Client Event handler runner thread when value is set to a function if the Client Event handler runner already exists"
    )
    def test_client_event_runner_already_exists(self, handler_name, handler_manager, handler):
        # Add a fake client event runner thread
        fake_runner_thread = threading.Thread()
        fake_runner_thread.daemon = True
        fake_runner_thread.start()
        handler_manager._client_event_runner = fake_runner_thread
        # Set handler
        setattr(handler_manager, handler_name, handler)
        # Fake thread was not changed
        assert handler_manager._client_event_runner is fake_runner_thread

    @pytest.mark.it(
        "Does not delete, remove, or replace the Thread for the Client Event handler runner when value is set back to None"
    )
    def test_handler_removed(self, handler_name, handler_manager, handler):
        # Set handler
        setattr(handler_manager, handler_name, handler)
        # Thread has been created and is alive
        t = handler_manager._client_event_runner
        assert isinstance(t, threading.Thread)
        assert t.is_alive()
        # Set the handler back to None
        setattr(handler_manager, handler_name, None)
        # Thread is still maintained on the manager and alive
        assert handler_manager._client_event_runner is t
        assert t.is_alive()

    @pytest.mark.it(
        "Does not delete, remove, or replace the Thread for the Client Event handler runner when updated with a new function value"
    )
    def test_handler_update(self, handler_name, handler_manager, handler):
        # Set handler
        setattr(handler_manager, handler_name, handler)
        # Thread has been created and is alive
        t = handler_manager._client_event_runner
        assert isinstance(t, threading.Thread)
        assert t.is_alive()

        # Set new handler
        def new_handler(arg):
            pass

        setattr(handler_manager, handler_name, new_handler)

        # Thread is still maintained on the manager and alive
        assert handler_manager._client_event_runner is t
        assert t.is_alive()

    @pytest.mark.it(
        "Is invoked by the runner only when the Client Event Inbox receives a matching Client Event, passing any arguments to the handler"
    )
    def test_handler_invoked(self, mocker, handler_name, handler_manager, inbox, event):
        # Set the handler
        mock_handler = mocker.MagicMock()
        setattr(handler_manager, handler_name, mock_handler)
        # Handler has not been called
        assert mock_handler.call_count == 0

        # Add the event to the client event inbox
        inbox.put(event)
        time.sleep(0.1)

        # Handler has been called with the arguments from the event
        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call(*event.args_for_user)

        # Add non-matching event to the client event inbox
        non_matching_event = client_event.ClientEvent("NON_MATCHING_EVENT")
        inbox.put(non_matching_event)
        time.sleep(0.1)

        # Handler has not been called again
        assert mock_handler.call_count == 1

    @pytest.mark.it(
        "Is invoked by the runner every time the Client Event Inbox receives a matching Client Event"
    )
    def test_handler_invoked_multiple(self, handler_name, handler_manager, inbox, event):
        # Set the handler
        mock_handler = ThreadsafeMock()
        setattr(handler_manager, handler_name, mock_handler)
        # Handler has not been called
        assert mock_handler.call_count == 0

        # Add 5 matching events to the corresponding inbox, triggering the handler
        for _ in range(5):
            inbox.put(event)
        time.sleep(0.2)

        # Handler has been called 5 times
        assert mock_handler.call_count == 5

    @pytest.mark.it(
        "Sends a HandlerManagerException to the background exception handler if any exception is raised during its invocation"
    )
    def test_exception_in_handler(
        self, mocker, handler_name, handler_manager, inbox, event, arbitrary_exception
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
        # Add the event to the client event inbox, triggering the handler
        inbox.put(event)
        time.sleep(0.1)
        # Handler has now been called
        assert mock_handler.call_count == 1
        # Background exception handler was called
        assert background_exc_spy.call_count == 1
        e = background_exc_spy.call_args[0][0]
        assert isinstance(e, HandlerManagerException)
        assert e.__cause__ is arbitrary_exception

    @pytest.mark.it(
        "Can be updated with a new value that the Client Event handler runner will immediately begin using for handler invocations instead"
    )
    def test_updated_handler(self, mocker, handler_name, handler_manager, inbox, event):
        def handler(*args):
            # Invoking handler replaces the set handler with a mock
            setattr(handler_manager, handler_name, mocker.MagicMock())

        setattr(handler_manager, handler_name, handler)

        inbox.put(event)
        time.sleep(0.1)
        # Handler has been replaced with a mock, but the mock has not been invoked
        assert getattr(handler_manager, handler_name) is not handler
        assert getattr(handler_manager, handler_name).call_count == 0
        # Add a new event to the inbox
        inbox.put(event)
        time.sleep(0.1)
        # The mock was now called
        assert getattr(handler_manager, handler_name).call_count == 1


@pytest.mark.describe("SyncHandlerManager - PROPERTY: .on_message_received")
class TestSyncHandlerManagerPropertyOnMessageReceived(SharedReceiverHandlerPropertyTests):
    @pytest.fixture
    def handler_name(self):
        return "on_message_received"

    @pytest.fixture
    def inbox(self, inbox_manager):
        return inbox_manager.get_unified_message_inbox()


@pytest.mark.describe("SyncHandlerManager - PROPERTY: .on_method_request_received")
class TestSyncHandlerManagerPropertyOnMethodRequestReceived(SharedReceiverHandlerPropertyTests):
    @pytest.fixture
    def handler_name(self):
        return "on_method_request_received"

    @pytest.fixture
    def inbox(self, inbox_manager):
        return inbox_manager.get_method_request_inbox()


@pytest.mark.describe("SyncHandlerManager - PROPERTY: .on_twin_desired_properties_patch_received")
class TestSyncHandlerManagerPropertyOnTwinDesiredPropertiesPatchReceived(
    SharedReceiverHandlerPropertyTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_twin_desired_properties_patch_received"

    @pytest.fixture
    def inbox(self, inbox_manager):
        return inbox_manager.get_twin_patch_inbox()


@pytest.mark.describe("SyncHandlerManager - PROPERTY: .on_connection_state_change")
class TestSyncHandlerManagerPropertyOnConnectionStateChange(SharedClientEventHandlerPropertyTests):
    @pytest.fixture
    def handler_name(self):
        return "on_connection_state_change"

    @pytest.fixture
    def event(self):
        return client_event.ClientEvent(client_event.CONNECTION_STATE_CHANGE)


@pytest.mark.describe("SyncHandlerManager - PROPERTY: .on_new_sastoken_required")
class TestSyncHandlerManagerPropertyOnNewSastokenRequired(SharedClientEventHandlerPropertyTests):
    @pytest.fixture
    def handler_name(self):
        return "on_new_sastoken_required"

    @pytest.fixture
    def event(self):
        return client_event.ClientEvent(client_event.NEW_SASTOKEN_REQUIRED)


@pytest.mark.describe("SyncHandlerManager - PROPERTY: .on_background_exception")
class TestSyncHandlerManagerPropertyOnBackgroundException(SharedClientEventHandlerPropertyTests):
    @pytest.fixture
    def handler_name(self):
        return "on_background_exception"

    @pytest.fixture
    def event(self, arbitrary_exception):
        return client_event.ClientEvent(client_event.BACKGROUND_EXCEPTION, arbitrary_exception)


@pytest.mark.describe("SyncHandlerManager - PROPERTY: .handling_client_events")
class TestSyncHandlerManagerPropertyHandlingClientEvents(object):
    @pytest.fixture
    def handler_manager(self, inbox_manager):
        hm = SyncHandlerManager(inbox_manager)
        yield hm
        hm.stop()

    @pytest.mark.it("Is True if the Client Event Handler Runner is running")
    def test_client_event_runner_running(self, handler_manager):
        # Add a fake client event runner thread
        fake_runner_thread = threading.Thread()
        fake_runner_thread.daemon = True
        fake_runner_thread.start()
        handler_manager._client_event_runner = fake_runner_thread

        assert handler_manager.handling_client_events is True

    @pytest.mark.it("Is False if the Client Event Handler Runner is not running")
    def test_client_event_runner_not_running(self, handler_manager):
        assert handler_manager._client_event_runner is None
        assert handler_manager.handling_client_events is False
