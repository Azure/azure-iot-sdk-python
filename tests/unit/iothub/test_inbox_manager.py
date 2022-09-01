# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from azure.iot.device.iothub.inbox_manager import InboxManager
from azure.iot.device.iothub.models import MethodRequest
from azure.iot.device.iothub.aio.async_inbox import AsyncClientInbox
from azure.iot.device.iothub.sync_inbox import SyncClientInbox

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture(
    params=[AsyncClientInbox, SyncClientInbox],
    ids=["Configured with AsyncClientInboxes", "Configured with SyncClientInboxes"],
)
def inbox_type(request):
    return request.param


@pytest.fixture
def manager(inbox_type):
    return InboxManager(inbox_type=inbox_type)


@pytest.fixture
def method_request():
    return MethodRequest(request_id="1", name="some_method", payload="{'key': 'value'}")


@pytest.mark.describe("InboxManager")
class TestInboxManager(object):
    @pytest.mark.it("Instantiates with an empty message inbox")
    def test_instantiates_with_empty_message_inbox(self, manager):
        assert manager.message_inbox.empty()

    @pytest.mark.it("Instantiates with an empty method request inbox")
    def test_instantiates_with_empty_generic_method_inbox(self, manager):
        assert manager.method_request_inbox.empty()

    @pytest.mark.it("Instantiates with an empty twin patch inbox")
    def test_instantiates_with_empty_twin_patch_inbox(self, manager):
        assert manager.twin_patch_inbox.empty()

    @pytest.mark.it("Instantiates with an empty client event inbox")
    def test_instantiates_with_empty_client_event_inbox(self, manager):
        assert manager.client_event_inbox.empty()


@pytest.mark.describe("InboxManager - .get_message_inbox()")
class TestInboxManagerGetMessageInbox(object):
    @pytest.mark.it("Returns an inbox")
    def test_returns_inbox(self, manager, inbox_type):
        message_inbox = manager.get_message_inbox()
        assert isinstance(message_inbox, inbox_type)

    @pytest.mark.it("Returns the same inbox when called multiple times")
    def test_called_multiple_times_returns_same_inbox(self, manager):
        message_inbox_ref1 = manager.get_message_inbox()
        message_inbox_ref2 = manager.get_message_inbox()
        assert message_inbox_ref1 is message_inbox_ref2


@pytest.mark.describe("InboxManager - .get_method_request_inbox()")
class TestInboxManagerGetMethodRequestInbox(object):
    @pytest.mark.it("Returns an inbox")
    def test_get_method_request_inbox_returns_inbox(self, manager, inbox_type):
        method_request_inbox = manager.get_method_request_inbox()
        assert isinstance(method_request_inbox, inbox_type)

    @pytest.mark.it("Returns the same inbox when called multiple times")
    def test_get_method_request_inbox_called_multiple_times_returns_same_inbox(
        self,
        manager,
    ):
        message_request_inbox1 = manager.get_method_request_inbox()
        message_request_inbox2 = manager.get_method_request_inbox()
        assert message_request_inbox1 is message_request_inbox2


@pytest.mark.describe("InboxManager - .get_twin_patch_inbox()")
class TestInboxManagerGetTwinPatchInbox(object):
    @pytest.mark.it("Returns an inbox")
    def test_returns_inbox(self, manager, inbox_type):
        tp_inbox = manager.get_twin_patch_inbox()
        assert isinstance(tp_inbox, inbox_type)

    @pytest.mark.it("Returns the same inbox when called multiple times")
    def test_called_multiple_times_returns_same_inbox(self, manager):
        tp_inbox_ref1 = manager.get_twin_patch_inbox()
        tp_inbox_ref2 = manager.get_twin_patch_inbox()
        assert tp_inbox_ref1 is tp_inbox_ref2


@pytest.mark.describe("InboxManager - .get_client_event_inbox()")
class TestInboxManagerGetClientEventInbox(object):
    @pytest.mark.it("Returns an inbox")
    def test_returns_inbox(self, manager, inbox_type):
        ce_inbox = manager.get_client_event_inbox()
        assert isinstance(ce_inbox, inbox_type)

    @pytest.mark.it("Returns the same inbox when called multiple times")
    def test_called_multiple_times_returns_same_inbox(self, manager):
        ce_inbox_ref1 = manager.get_client_event_inbox()
        ce_inbox_ref2 = manager.get_client_event_inbox()
        assert ce_inbox_ref1 is ce_inbox_ref2


@pytest.mark.describe("InboxManager - .clear_all_method_requests()")
class TestInboxManagerClearAllMethodRequests(object):
    @pytest.mark.it("Clears the generic method request inbox")
    def test_clears_generic_method_request_inbox(self, manager):
        generic_method_request_inbox = manager.get_method_request_inbox()
        assert generic_method_request_inbox.empty()
        manager.route_method_request(MethodRequest("id", "unrecognized_method_name", "payload"))
        assert not generic_method_request_inbox.empty()

        manager.clear_all_method_requests()
        assert generic_method_request_inbox.empty()


@pytest.mark.describe("InboxManager - .route_c2d_message()")
class TestInboxManagerRouteC2DMessage(object):
    @pytest.mark.it("Adds Message to the message inbox")
    def test_adds_message_to_message_inbox(self, manager, message):
        message_inbox = manager.get_message_inbox()
        assert message_inbox.empty()
        delivered = manager.route_c2d_message(message)
        assert delivered
        assert not message_inbox.empty()
        assert message in message_inbox


@pytest.mark.describe("InboxManager - .route_input_message()")
class TestInboxManagerRouteInputMessage(object):
    @pytest.mark.it("Adds Message to the message inbox")
    def test_adds_message_to_message_inbox(self, manager, message):
        message.input_name = "some_input"
        message_inbox = manager.get_message_inbox()
        assert message_inbox.empty()
        delivered = manager.route_input_message(message)
        assert delivered
        assert not message_inbox.empty()
        assert message in message_inbox


@pytest.mark.describe("InboxManager - .route_method_request()")
class TestInboxManagerRouteMethodRequest(object):
    @pytest.mark.it("Adds MethodRequest to the method request inbox")
    def test_calling_with_unknown_method_adds_method_to_method_inbox(self, manager, method_request):
        method_inbox = manager.get_method_request_inbox()
        assert method_inbox.empty()

        delivered = manager.route_method_request(method_request)
        assert delivered

        # Method Request was delivered to the method inbox
        assert not method_inbox.empty()
        assert method_request in method_inbox
