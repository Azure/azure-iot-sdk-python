# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from azure.iot.device.common.transport.mqtt import pipeline_ops_mqtt

fake_callback = "__fake_callback__"
fake_client_id = "__fake_client_id__"
fake_hostname = "__fake_hostname__"
fake_username = "__fake_username__"
fake_ca_cert = "__fake_ca_cert__"
fake_topic = "__fake_topic__"
fake_payload = "__fake_payload__"


def assert_all_base_defaults(obj):
    assert obj.name is obj.__class__.__name__
    assert obj.needs_connection is False
    assert obj.error is None


@pytest.mark.describe("SetConnectionArgs object")
class TestSetConnectionArgs(object):
    @pytest.mark.it("Sets required and default arguments correctly")
    def test_required_arguments(self):
        obj = pipeline_ops_mqtt.SetConnectionArgs(
            client_id=fake_client_id, hostname=fake_hostname, username=fake_username
        )
        assert_all_base_defaults(obj)
        assert obj.client_id is fake_client_id
        assert obj.hostname is fake_hostname
        assert obj.username is fake_username
        assert obj.ca_cert is None
        assert obj.callback is None

    @pytest.mark.it("Sets optional arguments correctly")
    def test_optional_arguments(self):
        obj = pipeline_ops_mqtt.SetConnectionArgs(
            client_id=fake_client_id,
            hostname=fake_hostname,
            username=fake_username,
            ca_cert=fake_ca_cert,
            callback=fake_callback,
        )
        assert_all_base_defaults(obj)
        assert obj.client_id is fake_client_id
        assert obj.hostname is fake_hostname
        assert obj.username is fake_username
        assert obj.ca_cert is fake_ca_cert
        assert obj.callback is fake_callback


@pytest.mark.describe("Publish object")
class TestPublish(object):
    @pytest.mark.it("Sets required and default arguments correctly")
    def test_required_arguments(self):
        obj = pipeline_ops_mqtt.Publish(topic=fake_topic, payload=fake_payload)
        assert_all_base_defaults(obj)
        assert obj.topic is fake_topic
        assert obj.payload is fake_payload
        assert obj.callback is None

    @pytest.mark.it("Sets optional arguments correctly")
    def test_optional_arguments(self):
        obj = pipeline_ops_mqtt.Publish(
            topic=fake_topic, payload=fake_payload, callback=fake_callback
        )
        assert_all_base_defaults(obj)
        assert obj.topic is fake_topic
        assert obj.payload is fake_payload
        assert obj.callback is fake_callback


@pytest.mark.describe("Subscribe object")
class TestSubscribe(object):
    @pytest.mark.it("Sets required and default arguments correctly")
    def test_required_arguments(self):
        obj = pipeline_ops_mqtt.Subscribe(topic=fake_topic)
        assert_all_base_defaults(obj)
        assert obj.topic is fake_topic
        assert obj.callback is None

    @pytest.mark.it("Sets optional arguments correctly")
    def test_optional_arguments(self):
        obj = pipeline_ops_mqtt.Subscribe(topic=fake_topic, callback=fake_callback)
        assert_all_base_defaults(obj)
        assert obj.topic is fake_topic
        assert obj.callback is fake_callback


@pytest.mark.describe("Unsubscribe object")
class TestUnsubscribe(object):
    @pytest.mark.it("Sets required and default arguments correctly")
    def test_required_arguments(self):
        obj = pipeline_ops_mqtt.Unsubscribe(topic=fake_topic)
        assert_all_base_defaults(obj)
        assert obj.topic is fake_topic
        assert obj.callback is None

    @pytest.mark.it("Sets optional arguments correctly")
    def test_optional_arguments(self):
        obj = pipeline_ops_mqtt.Unsubscribe(topic=fake_topic, callback=fake_callback)
        assert_all_base_defaults(obj)
        assert obj.topic is fake_topic
        assert obj.callback is fake_callback
