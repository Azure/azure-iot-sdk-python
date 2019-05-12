# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import sys
import six
import abc
from azure.iot.device.iothub.inbox_manager import InboxManager
from azure.iot.device.iothub.models import Message, MethodRequest

inbox_type_list = []

# Create a list of Inbox types to test with the manager
try:
    from azure.iot.device.iothub.aio.async_inbox import AsyncClientInbox

    inbox_type_list.append(AsyncClientInbox)
except SyntaxError:
    # AsyncClientInbox not available if Python < 3.5
    pass
finally:
    from azure.iot.device.iothub.sync_inbox import SyncClientInbox

    inbox_type_list.append(SyncClientInbox)


class TestInboxManager(object):
    @pytest.fixture(params=inbox_type_list)
    def inbox_type(self, request):
        return request.param

    @pytest.fixture
    def manager(self, inbox_type):
        return InboxManager(inbox_type=inbox_type)

    @pytest.fixture
    def message(self):
        return Message("some message")

    @pytest.fixture
    def method_request(self):
        return MethodRequest(request_id="1", name="some_method", payload="{'key': 'value'}")

    def test_get_c2d_message_inbox_returns_inbox(self, manager, inbox_type):
        c2d_inbox = manager.get_c2d_message_inbox()
        assert isinstance(c2d_inbox, inbox_type)

    def test_get_c2d_message_inbox_called_multiple_times_returns_same_inbox(self, manager):
        c2d_inbox_ref1 = manager.get_c2d_message_inbox()
        c2d_inbox_ref2 = manager.get_c2d_message_inbox()
        assert c2d_inbox_ref1 is c2d_inbox_ref2

    def test_get_input_message_inbox_returns_inbox(self, manager, inbox_type):
        input_name = "some_input"
        input_inbox = manager.get_input_message_inbox(input_name)
        assert isinstance(input_inbox, inbox_type)

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

    @pytest.mark.parametrize(
        "method_name",
        [
            pytest.param("some_method", id="Called with a method name"),
            pytest.param(None, id="Called with no method name"),
        ],
    )
    def test_get_method_request_inbox_returns_inbox(self, manager, method_name, inbox_type):
        method_request_inbox = manager.get_method_request_inbox(method_name)
        assert isinstance(method_request_inbox, inbox_type)

    @pytest.mark.parametrize(
        "method_name",
        [
            pytest.param("some_method", id="Called with a method name"),
            pytest.param(None, id="Called with no method name"),
        ],
    )
    def test_get_method_request_inbox_called_multiple_times_with_same_method_name_returns_same_inbox(
        self, manager, method_name
    ):
        message_request_inbox1 = manager.get_method_request_inbox(method_name)
        message_request_inbox2 = manager.get_method_request_inbox(method_name)
        assert message_request_inbox1 is message_request_inbox2

    def test_get_method_request_inbox_called_multiple_times_with_different_method_name_returns_different_inbox(
        self, manager
    ):
        message_request_inbox1 = manager.get_method_request_inbox("some_method")
        message_request_inbox2 = manager.get_method_request_inbox("some_other_method")
        message_request_inbox3 = manager.get_method_request_inbox()
        assert message_request_inbox1 is not message_request_inbox2
        assert message_request_inbox1 is not message_request_inbox3
        assert message_request_inbox2 is not message_request_inbox3

    def test_clear_all_method_requests_clears_generic_method_request_inbox(self, manager):
        generic_method_request_inbox = manager.get_method_request_inbox()
        assert generic_method_request_inbox.empty()
        manager.route_method_request(MethodRequest("id", "unrecognized_method_name", "payload"))
        assert not generic_method_request_inbox.empty()

        manager.clear_all_method_requests()
        assert generic_method_request_inbox.empty()

    def test_clear_all_method_requests_clears_named_method_request_inboxes(self, manager):
        method_request_inbox1 = manager.get_method_request_inbox("some_method")
        method_request_inbox2 = manager.get_method_request_inbox("some_other_method")
        assert method_request_inbox1.empty()
        assert method_request_inbox2.empty()
        manager.route_method_request(MethodRequest("id1", "some_method", "payload"))
        manager.route_method_request(MethodRequest("id2", "some_other_method", "payload"))
        assert not method_request_inbox1.empty()
        assert not method_request_inbox2.empty()

        manager.clear_all_method_requests()
        assert method_request_inbox1.empty()
        assert method_request_inbox2.empty()

    def test_route_c2d_message_adds_message_to_c2d_message_inbox(self, manager, message):
        c2d_inbox = manager.get_c2d_message_inbox()
        assert c2d_inbox.empty()
        delivered = manager.route_c2d_message(message)
        assert delivered
        assert not c2d_inbox.empty()
        assert message in c2d_inbox

    def test_route_input_message_adds_message_to_input_message_inbox(self, manager, message):
        input_name = "some_input"
        input_inbox = manager.get_input_message_inbox(input_name)
        assert input_inbox.empty()
        delivered = manager.route_input_message(input_name, message)
        assert delivered
        assert not input_inbox.empty()
        assert message in input_inbox

    def test_route_input_message_drops_message_to_unknown_input(self, manager, message):
        delivered = manager.route_input_message("not_a_real_input", message)
        assert not delivered

    def test_route_method_request_with_known_method_adds_method_to_named_method_inbox(
        self, manager, method_request
    ):
        # Establish an inbox with the corresponding method name
        named_method_inbox = manager.get_method_request_inbox(method_request.name)
        generic_method_inbox = manager.get_method_request_inbox()
        assert named_method_inbox.empty()
        assert generic_method_inbox.empty()

        delivered = manager.route_method_request(method_request)
        assert delivered

        # Method Request was delivered to the method inbox with the corresponding name
        assert not named_method_inbox.empty()
        assert method_request in named_method_inbox

        # Method Request was NOT delivered to the generic method inbox
        assert generic_method_inbox.empty()

    def test_route_method_request_with_unknown_method_adds_method_to_generic_method_inbox(
        self, manager, method_request
    ):
        # Do NOT get a specific named inbox - just the generic one
        generic_method_inbox = manager.get_method_request_inbox()
        assert generic_method_inbox.empty()

        delivered = manager.route_method_request(method_request)
        assert delivered

        # Method Request was delivered to the generic method inbox since method name was unknown
        assert not generic_method_inbox.empty()
        assert method_request in generic_method_inbox

    def test_route_method_request_will_route_method_to_generic_method_request_inbox_until_named_method_inbox_is_created(
        self, manager
    ):
        # Two MethodRequests for the SAME method name
        method_name = "some_method"
        method_request1 = MethodRequest(
            request_id="1", name=method_name, payload="{'key': 'value'}"
        )
        method_request2 = MethodRequest(
            request_id="2", name=method_name, payload="{'key': 'value'}"
        )

        # Do NOT get a specific named inbox - just the generic one
        generic_method_inbox = manager.get_method_request_inbox()
        assert generic_method_inbox.empty()

        # Route the first method request
        delivered_request1 = manager.route_method_request(method_request1)
        assert delivered_request1

        # Method Request 1 was delivered to the generic method inbox since the method name was unknown
        assert method_request1 in generic_method_inbox

        # Get an inbox for the specific method name
        named_method_inbox = manager.get_method_request_inbox(method_name)
        assert named_method_inbox.empty()

        # Route the second method request
        delivered_request2 = manager.route_method_request(method_request2)
        assert delivered_request2

        # Method Request 2 was delivered to its corresponding named inbox since the method name is known
        assert method_request2 in named_method_inbox
        assert method_request2 not in generic_method_inbox
