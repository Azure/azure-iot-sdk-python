# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import sys
import six
import abc
from azure.iot.hub.devicesdk.inbox_manager import InboxManager
from azure.iot.hub.devicesdk import Message
from azure.iot.hub.devicesdk.sync_inbox import SyncClientInbox


@six.add_metaclass(abc.ABCMeta)
class InboxManagerSharedTests(object):

    inbox_type = None  # Will be set in child tests

    @pytest.fixture
    def manager(self):
        return InboxManager(inbox_type=self.inbox_type)

    @pytest.fixture
    def message(self):
        return Message("some message")

    def test_get_c2d_message_inbox_returns_inbox(self, manager):
        c2d_inbox = manager.get_c2d_message_inbox()
        assert type(c2d_inbox) == self.inbox_type

    def test_get_c2d_message_inbox_called_multiple_times_returns_same_inbox(self, manager):
        c2d_inbox_ref1 = manager.get_c2d_message_inbox()
        c2d_inbox_ref2 = manager.get_c2d_message_inbox()
        assert c2d_inbox_ref1 is c2d_inbox_ref2

    def test_get_input_message_inbox_returns_inbox(self, manager):
        input_name = "some_input"
        input_inbox = manager.get_input_message_inbox(input_name)
        assert type(input_inbox) == self.inbox_type

    def test_get_input_message_inbox_called_multiple_times_with_same_input_name_returns_same_inbox(
        self, manager
    ):
        input_name = "some_input"
        input_inbox_ref1 = manager.get_input_message_inbox(input_name)
        input_inbox_ref2 = manager.get_input_message_inbox(input_name)
        assert input_inbox_ref1 is input_inbox_ref2

    def test_get_input_message_inbox_called_multiple_times_with_different_input_name_returns_different_inbox(
        self, manager
    ):
        input_inbox1 = manager.get_input_message_inbox("some_input")
        input_inbox2 = manager.get_input_message_inbox("some_other_input")
        assert input_inbox1 is not input_inbox2

    def test_input_message_inboxes_persist_in_manager_after_creation(self, manager):
        assert manager.input_message_inboxes == {}  # empty dict - no inboxes
        input1 = "some_input"
        input_inbox1 = manager.get_input_message_inbox(input1)
        assert input1 in manager.input_message_inboxes.keys()
        assert input_inbox1 in manager.input_message_inboxes.values()

    @pytest.mark.skip(reason="Not Implemented")
    def test_get_method_request_inbox_returns_expected_inbox(self, manager):
        pass

    @pytest.mark.skip(reason="Not Implemented")
    def test_get_method_request_inbox_called_multiple_times_with_same_method_name_returns_same_inbox(
        self, manager
    ):
        pass

    @pytest.mark.skip(reason="Not Implemented")
    def test_get_method_request_inbox_called_multiple_times_with_different_method_name_returns_different_inbox(
        self, manager
    ):
        pass

    @pytest.mark.skip(reason="Not Implemented")
    def test_clear_all_method_calls_clears_generic_method_call_inbox(self, manager):
        pass

    @pytest.mark.skip(reason="Not Implemented")
    def test_clear_all_method_calls_deletes_named_method_call_inboxes(self, manager):
        pass

    @abc.abstractmethod
    def test_route_c2d_message_adds_message_to_c2d_message_inbox(self, manager, message):
        pass

    @abc.abstractmethod
    def test_route_input_message_adds_message_to_input_message_inbox(self, manager, message):
        pass

    def test_route_input_message_drops_message_to_unknown_input(self, manager, message):
        delivered = manager.route_input_message("not_a_real_input", message)
        assert not delivered

    @abc.abstractmethod
    def test_route_method_call_with_unknown_method_adds_method_to_generic_method_inbox(
        self, manager
    ):
        pass

    @abc.abstractmethod
    def test_route_method_call_with_known_method_adds_method_to_named_method_inbox(self, manager):
        pass


class TestInboxManagerWithSyncInboxes(InboxManagerSharedTests):
    inbox_type = SyncClientInbox

    def test_route_c2d_message_adds_message_to_c2d_message_inbox(self, manager, message):
        c2d_inbox = manager.get_c2d_message_inbox()
        assert c2d_inbox.empty()
        delivered = manager.route_c2d_message(message)
        assert delivered
        assert not c2d_inbox.empty()
        assert c2d_inbox.get() is message

    def test_route_input_message_adds_message_to_input_message_inbox(self, manager, message):
        input_name = "some_input"
        input_inbox = manager.get_input_message_inbox(input_name)
        assert input_inbox.empty()
        delivered = manager.route_input_message(input_name, message)
        assert delivered
        assert not input_inbox.empty()
        assert input_inbox.get() is message

    @pytest.mark.skip(reason="Not Implemented")
    def test_route_method_call_with_unknown_method_adds_method_to_generic_method_inbox(
        self, manager
    ):
        pass

    @pytest.mark.skip(reason="Not Implemented")
    def test_route_method_call_with_known_method_adds_method_to_named_method_inbox(self, manager):
        pass

    @pytest.mark.skip(reason="Not Implemented")
    def test_route_method_call_will_route_method_to_generic_method_call_inbox_until_named_method_inbox_is_created(
        self, manager
    ):
        pass
