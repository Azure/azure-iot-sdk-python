# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import asyncio
import inspect
from azure.iot.device.iothub.aio.async_handler_manager import AsyncHandlerManager
from azure.iot.device.iothub.sync_handler_manager import MESSAGE, METHOD, TWIN_DP_PATCH
from azure.iot.device.iothub.inbox_manager import InboxManager
from azure.iot.device.iothub.aio.async_inbox import AsyncClientInbox

pytestmark = pytest.mark.asyncio
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
def inbox_manager():
    return InboxManager(inbox_type=AsyncClientInbox)


@pytest.fixture
def handler_manager(inbox_manager):
    return AsyncHandlerManager(inbox_manager)


# ----------------------
# We have to do some unfortunate things here in order to manually mock out handlers, to test
# tha they have been called. We can't use MagicMocks because not only do they not work well
# with coroutines, but especially if we are trying to test the very fact that functions and
# coroutines both work in the HandlerManager, replacing those things (i.e. the things under test)
# with a Mock.... really doesn't help us achieve that goal.


@pytest.fixture
def handler_checker():
    class HandlerChecker(object):
        def __init__(self):
            self.handler_called = False
            self.handler_call_count = 0
            self.handler_call_arg = None

    return HandlerChecker()


@pytest.fixture(params=["Handler function", "Handler coroutine"])
def handler(request, handler_checker):
    if request.param == "Handler function":

        def some_handler_fn(arg):
            handler_checker.handler_called = True
            handler_checker.handler_call_count += 1
            handler_checker.handler_call_arg = arg

        return some_handler_fn

    else:

        async def some_handler_coro(arg):
            handler_checker.handler_called = True
            handler_checker.handler_call_count += 1
            handler_checker.handler_call_arg = arg

        return some_handler_coro


# ----------------------


@pytest.mark.describe("AsyncHandlerManager - Instantiation")
class TestInstantiation(object):
    @pytest.mark.it("Initializes handler properties to None")
    @pytest.mark.parametrize("handler_name", all_handlers)
    def test_handlers(self, inbox_manager, handler_name):
        hm = AsyncHandlerManager(inbox_manager)
        assert getattr(hm, handler_name) is None

    @pytest.mark.it("Initializes handler runner task references to None")
    @pytest.mark.parametrize("handler_name", all_internal_handlers, ids=all_handlers)
    def test_handler_runners(self, inbox_manager, handler_name):
        hm = AsyncHandlerManager(inbox_manager)
        assert hm._handler_runners[handler_name] is None


class SharedHandlerPropertyTests(object):
    # @pytest.fixture(autouse=True)
    # def teardown_runners(self, handler_manager):
    #     """This fixture removes all running async tasks when a test is finished"""
    #     yield
    #     for k in handler_manager._handler_runners.keys():
    #         if handler_manager._handler_runners[k] is not None:
    #             handler_manager._stop_handler_runner(k)

    # NOTE: If there is ever any deviation in the convention of what the internal names of handlers
    # are other than just a prefixed "_", we'll have to move this fixture to the child classes so
    # it can be unique to each handler
    @pytest.fixture
    def handler_name_internal(self, handler_name):
        return "_" + handler_name

    # NOTE: We use setattr() and getattr() in these tests so they're generic to all properties.
    # This is functionally identical to doing explicit assignment to a property, it just
    # doesn't read quite as well.

    @pytest.mark.it("Can be both read and written to")
    async def test_read_write(self, handler_name, handler_manager, handler):
        assert getattr(handler_manager, handler_name) is None
        setattr(handler_manager, handler_name, handler)
        assert getattr(handler_manager, handler_name) is handler
        await asyncio.sleep(1)

        # ib = handler_manager._inbox_manager.get_unified_message_inbox()
        # assert ib

        setattr(handler_manager, handler_name, None)
        await asyncio.sleep(1)
        assert getattr(handler_manager, handler_name) is None

        # await asyncio.sleep(1)
        # task = handler_manager._handler_runners["_" + handler_name]
        # assert task.result()

    # @pytest.mark.it(
    #     "Creates and stores an asyncio Task for the corresponding handler runner, when value is set to a function or coroutine handler, used for invoking the handler"
    # )
    # async def test_task_created(
    #     self, handler_name, handler_name_internal, handler_manager, handler
    # ):
    #     assert handler_manager._handler_runners[handler_name_internal] is None
    #     setattr(handler_manager, handler_name, handler)
    #     assert isinstance(handler_manager._handler_runners[handler_name_internal], asyncio.Task)

    # @pytest.mark.it(
    #     "Deletes any existing stored asyncio Task for the handler runner when the value is set back to None"
    # )
    # async def test_task_removed(
    #     self, handler_name, handler_name_internal, handler_manager, handler
    # ):
    #     # Set handler
    #     setattr(handler_manager, handler_name, handler)
    #     # Task has been created and is active
    #     task = handler_manager._handler_runners[handler_name_internal]
    #     assert isinstance(task, asyncio.Task)
    #     assert not task.cancelled()
    #     # Set the handler back to None
    #     setattr(handler_manager, handler_name, None)
    #     await asyncio.sleep(0.1)
    #     # Task has been cancelled, and the manager no longer has a reference to it
    #     assert task.cancelled()
    #     assert handler_manager._handler_runners[handler_name_internal] is None

    # @pytest.mark.it(
    #     "Does not delete, remove, or replace the asyncio Task for the handler runner, when the corresponding handler is updated with a new function or coroutine value"
    # )
    # async def test_task_unchanged_by_handler_update(
    #     self, handler_name, handler_name_internal, handler_manager, handler
    # ):
    #     # Set the handler
    #     setattr(handler_manager, handler_name, handler)
    #     # Task has been created and is active
    #     task = handler_manager._handler_runners[handler_name_internal]
    #     assert isinstance(task, asyncio.Task)
    #     assert not task.cancelled()

    #     # Set new handler
    #     def new_handler(arg):
    #         pass

    #     setattr(handler_manager, handler_name, new_handler)
    #     # Task has not been cancelled, and is still maintained by the manager
    #     assert handler_manager._handler_runners[handler_name_internal] is task
    #     assert not task.cancelled()

    # @pytest.mark.it(
    #     "Is invoked by the task when the Inbox corresponding to the handler receives an object, passing that object to the handler"
    # )
    # async def test_handler_invoked(
    #     self, mocker, handler_name, handler_manager, handler, handler_checker, inbox
    # ):
    #     # Set the handler
    #     setattr(handler_manager, handler_name, handler)
    #     # Handler has not been called
    #     assert handler_checker.handler_called is False
    #     assert handler_checker.handler_call_arg is None

    #     # Add an item to the associated inbox, triggering the handler
    #     mock_obj = mocker.MagicMock()
    #     inbox._put(mock_obj)
    #     await asyncio.sleep(0.1)

    #     # Handler has been called with the item from the inbox
    #     assert handler_checker.handler_called is True
    #     assert handler_checker.handler_call_arg is mock_obj

    # @pytest.mark.it(
    #     "Is invoked by the task every time the Inbox corresponding to the handler receives an object"
    # )
    # async def test_handler_invoked_multiple(
    #     self, mocker, handler_name, handler_manager, handler, handler_checker, inbox
    # ):
    #     # Set the handler
    #     setattr(handler_manager, handler_name, handler)
    #     # Handler has not been called
    #     assert handler_checker.handler_call_count == 0

    #     # Add 5 items to the associated inbox, triggering the handler
    #     for _ in range(5):
    #         inbox._put(mocker.MagicMock())
    #     await asyncio.sleep(0.1)

    #     # Handler has been called 5 times
    #     assert handler_checker.handler_call_count == 5

    # @pytest.mark.it(
    #     "Can be updated with a new value that the corresponding handler runner Task will immediately begin using instead"
    # )
    # async def test_handler_update_handler(self, mocker, handler_name, handler_manager, inbox):
    #     # Ideally we would also test coroutines, but honestly, it's difficult to set up.
    #     # Please add that test if you can think of a good way to do it.

    #     def handler1(arg):
    #         # Invoking handler 1 replaces the set handler with a mock
    #         setattr(handler_manager, handler_name, mocker.MagicMock())

    #     setattr(handler_manager, handler_name, handler1)

    #     inbox._put(mocker.MagicMock())
    #     await asyncio.sleep(0.1)
    #     # Handler has been replaced with a mock, but the mock has not been invoked
    #     assert getattr(handler_manager, handler_name) is not handler1
    #     assert getattr(handler_manager, handler_name).call_count == 0
    #     # Add a new item to the inbox
    #     inbox._put(mocker.MagicMock())
    #     await asyncio.sleep(0.1)
    #     # The mock was now called
    #     assert getattr(handler_manager, handler_name).call_count == 1


@pytest.mark.describe("AsyncHandlerManager - PROPERTY: .on_message_received")
class TestAsyncHandlerManagerPropertyOnMessageReceived(SharedHandlerPropertyTests):
    @pytest.fixture
    def handler_name(self):
        return "on_message_received"

    @pytest.fixture
    def inbox(self, inbox_manager):
        return inbox_manager.get_unified_message_inbox()


# @pytest.mark.describe("AsyncHandlerManager - PROPERTY: .on_method_request_received")
# class TestAsyncHandlerManagerPropertyOnMethodRequestReceived(SharedHandlerPropertyTests):
#     @pytest.fixture
#     def handler_name(self):
#         return "on_method_request_received"

#     @pytest.fixture
#     def inbox(self, inbox_manager):
#         return inbox_manager.get_method_request_inbox()


# @pytest.mark.describe("AsyncHandlerManager - PROPERTY: .on_twin_desired_properties_patch_received")
# class TestAsyncHandlerManagerPropertyOnTwinDesiredPropertiesPatchReceived(
#     SharedHandlerPropertyTests
# ):
#     @pytest.fixture
#     def handler_name(self):
#         return "on_twin_desired_properties_patch_received"

#     @pytest.fixture
#     def inbox(self, inbox_manager):
#         return inbox_manager.get_twin_patch_inbox()
