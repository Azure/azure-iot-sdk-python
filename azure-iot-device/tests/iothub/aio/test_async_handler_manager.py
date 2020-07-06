# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import asyncio
from azure.iot.device.iothub.aio.async_handler_manager import AsyncHandlerManager
from azure.iot.device.iothub.aio.async_handler_manager import MESSAGE, METHOD, TWIN_DP_PATCH

pytestmark = pytest.mark.asyncio
logging.basicConfig(level=logging.DEBUG)

all_internal_handlers = [MESSAGE, METHOD, TWIN_DP_PATCH]
all_handlers = [s.lstrip("_") for s in all_internal_handlers]


@pytest.mark.describe("AsyncHandlerManager - Instantiation")
class TestInstantiation(object):
    @pytest.fixture
    def inbox_manager(self):
        return None

    @pytest.mark.it("Initializes handler properties to None")
    @pytest.mark.parametrize("handler", all_handlers)
    def test_handlers(self, inbox_manager, handler):
        hm = AsyncHandlerManager(inbox_manager)
        assert getattr(hm, handler) is None

    @pytest.mark.it("Initializes handler task references to None")
    @pytest.mark.parametrize("handler", all_internal_handlers, ids=all_handlers)
    def test_handler_tasks(self, inbox_manager, handler):
        hm = AsyncHandlerManager(inbox_manager)
        assert hm._handler_tasks[handler] is None


# class SharedPROPERTYTests(object)
