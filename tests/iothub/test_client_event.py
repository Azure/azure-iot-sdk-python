# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from azure.iot.device.iothub.client_event import (
    ClientEvent,
    CONNECTION_STATE_CHANGE,
    NEW_SASTOKEN_REQUIRED,
    BACKGROUND_EXCEPTION,
)

logging.basicConfig(level=logging.DEBUG)

all_client_events = [CONNECTION_STATE_CHANGE, NEW_SASTOKEN_REQUIRED, BACKGROUND_EXCEPTION]


@pytest.mark.describe("ClientEvent")
class TestClientEvent(object):
    @pytest.mark.it("Instantiates with the 'name' attribute set to the provided 'name' parameter")
    @pytest.mark.parametrize("name", all_client_events)
    def test_name(self, name):
        event = ClientEvent(name)
        assert event.name == name

    @pytest.mark.it(
        "Instantiates with the 'args_for_user' attribute set to a variable-length list of all other provided parameters"
    )
    @pytest.mark.parametrize(
        "user_args",
        [
            pytest.param((), id="0 args"),
            pytest.param(("1",), id="1 arg"),
            pytest.param(("1", "2"), id="2 args"),
            pytest.param(("1", "2", "3", "4", "5"), id="5 args"),
        ],
    )
    def test_args_for_user(self, user_args):
        event = ClientEvent("some_event", *user_args)
        assert event.args_for_user == user_args
