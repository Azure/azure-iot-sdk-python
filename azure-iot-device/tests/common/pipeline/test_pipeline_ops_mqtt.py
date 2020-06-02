# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import sys
import logging
from azure.iot.device.common.pipeline import pipeline_ops_mqtt
from tests.common.pipeline import pipeline_ops_test

logging.basicConfig(level=logging.DEBUG)
this_module = sys.modules[__name__]
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")


class MQTTPublishOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_mqtt.MQTTPublishOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"topic": "some_topic", "payload": "some_payload", "callback": mocker.MagicMock()}
        return kwargs


class MQTTPublishOperationInstantiationTests(MQTTPublishOperationTestConfig):
    @pytest.mark.it("Initializes 'topic' attribute with the provided 'topic' parameter")
    def test_topic(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.topic == init_kwargs["topic"]

    @pytest.mark.it("Initializes 'payload' attribute with the provided 'payload' parameter")
    def test_payload(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.payload == init_kwargs["payload"]

    @pytest.mark.it("Initializes 'needs_connection' attribute as True")
    def test_needs_connection(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.needs_connection is True


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_mqtt.MQTTPublishOperation,
    op_test_config_class=MQTTPublishOperationTestConfig,
    extended_op_instantiation_test_class=MQTTPublishOperationInstantiationTests,
)


class MQTTSubscribeOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_mqtt.MQTTSubscribeOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"topic": "some_topic", "callback": mocker.MagicMock()}
        return kwargs


class MQTTSubscribeOperationInstantiationTests(MQTTSubscribeOperationTestConfig):
    @pytest.mark.it("Initializes 'topic' attribute with the provided 'topic' parameter")
    def test_topic(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.topic == init_kwargs["topic"]

    @pytest.mark.it("Initializes 'needs_connection' attribute as True")
    def test_needs_connection(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.needs_connection is True

    @pytest.mark.it("Initializes 'timeout_timer' attribute as None")
    def test_timeout_timer(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.timeout_timer is None

    @pytest.mark.it("Initializes 'retry_timer' attribute as None")
    def test_retry_timer(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.retry_timer is None


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_mqtt.MQTTSubscribeOperation,
    op_test_config_class=MQTTSubscribeOperationTestConfig,
    extended_op_instantiation_test_class=MQTTSubscribeOperationInstantiationTests,
)


class MQTTUnsubscribeOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_mqtt.MQTTUnsubscribeOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"topic": "some_topic", "callback": mocker.MagicMock()}
        return kwargs


class MQTTUnsubscribeOperationInstantiationTests(MQTTUnsubscribeOperationTestConfig):
    @pytest.mark.it("Initializes 'topic' attribute with the provided 'topic' parameter")
    def test_topic(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.topic == init_kwargs["topic"]

    @pytest.mark.it("Initializes 'needs_connection' attribute as True")
    def test_needs_connection(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.needs_connection is True

    @pytest.mark.it("Initializes 'timeout_timer' attribute as None")
    def test_timeout_timer(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.timeout_timer is None

    @pytest.mark.it("Initializes 'retry_timer' attribute as None")
    def test_retry_timer(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.retry_timer is None


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_mqtt.MQTTUnsubscribeOperation,
    op_test_config_class=MQTTUnsubscribeOperationTestConfig,
    extended_op_instantiation_test_class=MQTTUnsubscribeOperationInstantiationTests,
)
