# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from azure.iot.device.iothub.transport import pipeline_events_iothub

fake_message = "__fake_messsage__"
fake_input_name = "__fake_input_name__"


@pytest.mark.describe("C2DMessage object")
class TestC2DMessage(object):
    @pytest.mark.it("Sets arguments correctly")
    def test_default_arguments(self):
        obj = pipeline_events_iothub.C2DMessage(message=fake_message)
        assert obj.name is obj.__class__.__name__
        assert obj.message is fake_message


@pytest.mark.describe("InputMessage object")
class TestInputMessage(object):
    @pytest.mark.it("Sets arguments correctly")
    def test_default_arguments(self):
        obj = pipeline_events_iothub.InputMessage(message=fake_message, input_name=fake_input_name)
        assert obj.name is obj.__class__.__name__
        assert obj.message is fake_message
        assert obj.input_name is fake_input_name
