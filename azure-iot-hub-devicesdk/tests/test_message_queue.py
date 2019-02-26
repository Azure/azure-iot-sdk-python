# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.devicesdk.message import Message
from azure.iot.hub.devicesdk.message_queue import MessageQueue, MessageQueueManager
from azure.iot.hub.devicesdk.transport import constant


class TestMessageQueue(object):
    @pytest.fixture
    def on_enable_stub(self, mocker):
        return mocker.stub(name="on_enable_stub")

    @pytest.fixture
    def on_disable_stub(self, mocker):
        return mocker.stub(name="on_disable_stub")

    @pytest.fixture
    def message_queue(self, on_enable_stub, on_disable_stub):
        return MessageQueue(on_enable_stub, on_disable_stub)

    def test_instantiates_unenabled(self, message_queue):
        assert message_queue.enabled is False

    def test_instantiates_with_handlers_set(self, message_queue, on_enable_stub, on_disable_stub):
        assert message_queue._on_enable is on_enable_stub
        assert message_queue._on_disable is on_disable_stub

    def test_enable_sets_enabled_status_true(self, message_queue):
        assert message_queue.enabled is False
        message_queue.enable()
        assert message_queue.enabled is True

    def test_enable_calls_on_enable_handler_if_not_enabled(self, message_queue, on_enable_stub):
        message_queue.enable()
        assert on_enable_stub.call_count == 1

    def test_enable_does_not_call_on_enable_handler_if_already_enabled(
        self, message_queue, on_enable_stub
    ):
        message_queue.enable()
        on_enable_stub.reset_mock()
        message_queue.enable()
        assert on_enable_stub.call_count == 0

    def test_disable_sets_enabled_status_false(self, message_queue):
        message_queue.enable()
        assert message_queue.enabled is True
        message_queue.disable()
        assert message_queue.enabled is False

    def test_disable_calls_on_disable_handler_if_enabled(self, message_queue, on_disable_stub):
        message_queue.enable()
        message_queue.disable()
        assert on_disable_stub.call_count == 1

    def test_disable_does_not_call_on_disable_handler_if_already_disabled(
        self, message_queue, on_disable_stub
    ):
        message_queue.disable()
        assert on_disable_stub.call_count == 0

    def test_setting_enabled_to_true_calls_enable(self, message_queue, mocker):
        mocker.spy(message_queue, "enable")
        message_queue.enabled = True
        assert message_queue.enable.call_count == 1

    def test_setting_enabled_to_false_calls_disable(self, message_queue, mocker):
        mocker.spy(message_queue, "disable")
        message_queue.enabled = False
        assert message_queue.disable.call_count == 1


class TestMessageQueueManager(object):
    @pytest.fixture
    def enable_feature_mock(self, mocker):
        def enable_feature(feature_name, callback):
            callback()

        return mocker.MagicMock(wraps=enable_feature)

    @pytest.fixture
    def disable_feature_mock(self, mocker):
        def disable_feature(feature_name, callback):
            callback()

        return mocker.MagicMock(wraps=disable_feature)

    @pytest.fixture
    def manager(self, enable_feature_mock, disable_feature_mock):
        return MessageQueueManager(enable_feature_mock, disable_feature_mock)

    @pytest.fixture
    def message(self):
        return Message("this is a message")

    def test_instantiates_with_disabled_c2d_queue(self, manager):
        assert not manager.c2d_message_queue.enabled

    def test_instantiates_with_no_input_message_queues(self, manager):
        assert not manager.input_message_queues

    def test_get_c2d_message_queue_returns_enabled_queue(self, mocker, manager):
        mocker.spy(manager.c2d_message_queue, "enable")
        assert not manager.c2d_message_queue.enabled  # queue is disabled
        c2d_queue = manager.get_c2d_message_queue()
        assert c2d_queue is manager.c2d_message_queue
        assert c2d_queue.enabled  # queue is now enabled
        assert c2d_queue.enable.call_count == 1  # queue was enabled with the enable method

    def test_calling_get_c2d_message_queue_multiple_times_returns_the_same_queue(self, manager):
        c2d_queue_ref1 = manager.get_c2d_message_queue()
        c2d_queue_ref2 = manager.get_c2d_message_queue()
        assert c2d_queue_ref1 is c2d_queue_ref2

    def test_get_c2d_message_queue_only_enables_queue_if_disabled(self, manager, mocker):
        enable_spy = mocker.spy(manager.c2d_message_queue, "enable")
        assert not manager.c2d_message_queue.enabled  # queue is disabled
        c2d_queue = manager.get_c2d_message_queue()
        assert c2d_queue.enabled  # queue is now enabled
        assert c2d_queue.enable.call_count == 1
        enable_spy.reset_mock()
        c2d_queue = manager.get_c2d_message_queue()
        assert c2d_queue.enable.call_count == 0  # enable was not called
        c2d_queue.disable()  # queue is now disabled
        enable_spy.reset_mock()
        c2d_queue = manager.get_c2d_message_queue()
        assert c2d_queue.enable.call_count == 1

    def test_enabling_c2d_message_queue_calls_queue_manager_enable_feature_fn(
        self, manager, enable_feature_mock
    ):
        c2d_queue = manager.get_c2d_message_queue()  # implicitly enables
        assert enable_feature_mock.call_count == 1
        assert enable_feature_mock.call_args[0][0] == constant.C2D
        c2d_queue.disable()
        enable_feature_mock.reset_mock()
        c2d_queue.enable()  # explicit enable
        assert enable_feature_mock.call_count == 1
        assert enable_feature_mock.call_args[0][0] == constant.C2D

    def test_disabling_c2d_message_queue_calls_queue_manager_disable_feature_fn(
        self, manager, disable_feature_mock
    ):
        c2d_queue = manager.get_c2d_message_queue()  # implicitly enables
        c2d_queue.disable()
        assert disable_feature_mock.call_count == 1
        assert disable_feature_mock.call_args[0][0] == constant.C2D

    def test_get_input_message_queue_returns_enabled_queue(self, manager, mocker):
        input_queue = manager.get_input_message_queue("some_input")
        assert input_queue.enabled
        # expand this logic

    def test_calling_get_input_message_queue_multiple_times_with_same_input_name_returns_the_same_queue(
        self, manager
    ):
        input_queue_ref1 = manager.get_input_message_queue("some_input")
        input_queue_ref2 = manager.get_input_message_queue("some_input")
        assert input_queue_ref1 is input_queue_ref2

    def test_calling_get_input_message_queue_multiple_times_with_different_input_name_returns_different_queues(
        self, manager
    ):
        input_queue1 = manager.get_input_message_queue("some_input")
        input_queue2 = manager.get_input_message_queue("some_other_input")
        assert input_queue1 is not input_queue2

    def test_get_input_message_queue_only_enables_queue_if_disabled(self, manager, mocker):
        input_queue = manager.get_input_message_queue("some_input")  # implicitly enables
        input_queue.disable()
        assert not input_queue.enabled
        enable_spy = mocker.spy(input_queue, "enable")
        input_queue = manager.get_input_message_queue("some_input")  # implicitly enables
        assert enable_spy.call_count == 1
        enable_spy.reset_mock()
        input_queue = manager.get_input_message_queue("some_input")  # already enabled
        assert enable_spy.call_count == 0

    def test_input_message_queues_can_have_different_enabled_states(self, manager):
        input_queue1 = manager.get_input_message_queue("some_input")
        input_queue2 = manager.get_input_message_queue("some_other_input")
        assert input_queue1.enabled and input_queue2.enabled  # both enabled by default
        input_queue1.disable()
        assert not input_queue1.enabled and input_queue2.enabled

    def test_input_message_queues_persist_in_manager_after_creation(self, manager):
        assert manager.input_message_queues == {}  # empty dictionary - no queues
        input_queue1 = manager.get_input_message_queue("some_input")
        assert manager.input_message_queues == {"some_input": input_queue1}
        input_queue2 = manager.get_input_message_queue("some_other_input")
        assert manager.input_message_queues == {
            "some_input": input_queue1,
            "some_other_input": input_queue2,
        }

    def test_enabling_input_message_queue_calls_queue_manager_enable_feature_fn_if_it_is_the_only_input_queue(
        self, manager, enable_feature_mock
    ):
        input_queue = manager.get_input_message_queue("some_input")
        input_queue.disable()  # because it was enabled by default
        enable_feature_mock.reset_mock()
        input_queue.enable()
        assert enable_feature_mock.call_count == 1
        assert enable_feature_mock.call_args[0][0] == constant.INPUT

    def test_disabling_input_message_queue_calls_queue_manager_disable_feature_fn_if_it_is_the_only_input_queue(
        self, manager, disable_feature_mock
    ):
        input_queue = manager.get_input_message_queue("some_input")
        input_queue.disable()
        assert disable_feature_mock.call_count == 1
        assert disable_feature_mock.call_args[0][0] == constant.INPUT

    def test_enabling_input_message_queue_calls_queue_manager_enable_feature_fn_only_if_no_input_queues_are_already_enabled(
        self, manager, enable_feature_mock
    ):
        input_queue1 = manager.get_input_message_queue("some_input")
        input_queue2 = manager.get_input_message_queue("some_other_input")
        input_queue3 = manager.get_input_message_queue("yet_another_input")
        input_queue1.disable()
        input_queue2.disable()
        input_queue3.disable()
        enable_feature_mock.reset_mock()
        input_queue1.enable()
        assert enable_feature_mock.call_count == 1
        assert enable_feature_mock.call_args[0][0] == constant.INPUT
        enable_feature_mock.reset_mock()
        input_queue2.enable()
        assert enable_feature_mock.call_count == 0  # was not called again

    def test_disabling_input_message_queue_calls_queue_manager_disable_feature_fn_only_if_all_input_queues_are_disabled(
        self, manager, disable_feature_mock
    ):
        input_queue1 = manager.get_input_message_queue("some_input")
        input_queue2 = manager.get_input_message_queue("some_other_input")
        input_queue3 = manager.get_input_message_queue("yet_another_input")
        input_queue1.disable()
        assert disable_feature_mock.call_count == 0
        input_queue2.disable()
        assert disable_feature_mock.call_count == 0
        input_queue3.disable()
        assert disable_feature_mock.call_count == 1  # finally all queues are disabled
        assert disable_feature_mock.call_args[0][0] == constant.INPUT

    def test_route_c2d_message_adds_message_to_enabled_c2d_queue(self, manager, message):
        c2d_queue = manager.get_c2d_message_queue()
        assert c2d_queue.empty()
        delivered = manager.route_c2d_message(message)
        assert delivered
        assert not c2d_queue.empty()
        assert c2d_queue.get() is message

    def test_route_c2d_message_drops_message_to_disabled_c2d_queue(self, manager, message):
        c2d_queue = manager.get_c2d_message_queue()
        c2d_queue.disable()
        assert c2d_queue.empty()
        delivered = manager.route_c2d_message(message)
        assert not delivered
        assert c2d_queue.empty()

    def test_route_input_message_adds_message_to_enabled_input_queue(self, manager, message):
        input_queue = manager.get_input_message_queue("some_input")
        assert input_queue.empty()
        delivered = manager.route_input_message("some_input", message)
        assert delivered
        assert not input_queue.empty()
        assert input_queue.get() is message

    def test_route_input_message_drops_message_to_disabled_input_queue(self, manager, message):
        input_queue = manager.get_input_message_queue("some_input")
        input_queue.disable()
        assert input_queue.empty()
        delivered = manager.route_input_message("some_input", message)
        assert not delivered
        assert input_queue.empty()

    def test_route_input_message_drops_message_to_unknown_input(self, manager, message):
        delivered = manager.route_input_message("not_a_real_input", message)
        assert not delivered
