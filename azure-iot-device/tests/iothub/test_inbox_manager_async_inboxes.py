# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This test module extends test_inbox_manager and is separate to prevent SyntaxErrors
"""

import pytest
import sys
from .test_inbox_manager import InboxManagerSharedTests
from azure.iot.device.iothub.aio.async_inbox import AsyncClientInbox


@pytest.mark.skipif(sys.version_info < (3, 5), reason="Requires Python 3.5+")
class TestInboxManagerWithAsyncInboxes(InboxManagerSharedTests):
    inbox_type = AsyncClientInbox

    @pytest.mark.asyncio
    async def test_route_c2d_message_adds_message_to_c2d_message_inbox(self, manager, message):
        c2d_inbox = manager.get_c2d_message_inbox()
        assert c2d_inbox.empty()
        delivered = manager.route_c2d_message(message)
        assert delivered
        assert not c2d_inbox.empty()
        assert await c2d_inbox.get() is message

    @pytest.mark.asyncio
    async def test_route_input_message_adds_message_to_input_message_inbox(self, manager, message):
        input_name = "some_input"
        input_inbox = manager.get_input_message_inbox(input_name)
        assert input_inbox.empty()
        delivered = manager.route_input_message(
            input_name, message
        )  # oddly this adds a runtime warning, but route_c2d doesn't
        assert delivered
        assert not input_inbox.empty()
        assert await input_inbox.get() is message

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Not Implemented")
    async def test_route_method_call_with_unknown_method_adds_method_to_generic_method_inbox(
        self, manager
    ):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Not Implemented")
    async def test_route_method_call_with_known_method_adds_method_to_named_method_inbox(
        self, manager
    ):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Not Implemented")
    async def test_route_method_call_will_route_method_to_generic_method_call_inbox_until_named_method_inbox_is_created(
        self, manager
    ):
        pass
