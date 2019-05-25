# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from azure.iot.device.common.pipeline import pipeline_events_mqtt

fake_topic = "__fake_topic__"
fake_payload = "__fake_payload__"


@pytest.mark.describe("IncomingMessage object")
class TestIncomingMessage(object):
    @pytest.mark.it("Sets name attribute on instantiation")
    @pytest.mark.it("Sets topic attribute on instantiation")
    @pytest.mark.it("Sets payload attribute on instantiation")
    def test_default_arguments(self):
        obj = pipeline_events_mqtt.IncomingMessage(topic=fake_topic, payload=fake_payload)
        assert obj.name is obj.__class__.__name__
        assert obj.topic is fake_topic
        assert obj.payload is fake_payload
