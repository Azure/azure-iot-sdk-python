# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import sys
import logging
from azure.iot.device.provisioning.pipeline import pipeline_ops_provisioning
from tests.common.pipeline import pipeline_ops_test

logging.basicConfig(level=logging.DEBUG)
this_module = sys.modules[__name__]
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")


class RegisterOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_provisioning.RegisterOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {
            "request_payload": "some_request_payload",
            "registration_id": "some_registration_id",
            "callback": mocker.MagicMock(),
        }
        return kwargs


class RegisterOperationInstantiationTests(RegisterOperationTestConfig):
    @pytest.mark.it(
        "Initializes 'request_payload' attribute with the provided 'request_payload' parameter"
    )
    def test_request_payload(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.request_payload == init_kwargs["request_payload"]

    @pytest.mark.it(
        "Initializes 'registration_id' attribute with the provided 'registration_id' parameter"
    )
    def test_registration_id(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.registration_id == init_kwargs["registration_id"]

    @pytest.mark.it("Initializes 'retry_after_timer' attribute to None")
    def test_retry_after_timer(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.retry_after_timer is None

    @pytest.mark.it("Initializes 'polling_timer' attribute to None")
    def test_polling_timer(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.polling_timer is None

    @pytest.mark.it("Initializes 'provisioning_timeout_timer' attribute to None")
    def test_provisioning_timeout_timer(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.provisioning_timeout_timer is None


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_provisioning.RegisterOperation,
    op_test_config_class=RegisterOperationTestConfig,
    extended_op_instantiation_test_class=RegisterOperationInstantiationTests,
)


class PollStatusOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_provisioning.PollStatusOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {
            "operation_id": "some_operation_id",
            "request_payload": "some_request_payload",
            "callback": mocker.MagicMock(),
        }
        return kwargs


class PollStatusOperationInstantiationTests(PollStatusOperationTestConfig):
    @pytest.mark.it(
        "Initializes 'operation_id' attribute with the provided 'operation_id' parameter"
    )
    def test_operation_id(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.operation_id == init_kwargs["operation_id"]

    @pytest.mark.it(
        "Initializes 'request_payload' attribute with the provided 'request_payload' parameter"
    )
    def test_request_payload(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.request_payload == init_kwargs["request_payload"]

    @pytest.mark.it("Initializes 'retry_after_timer' attribute to None")
    def test_retry_after_timer(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.retry_after_timer is None

    @pytest.mark.it("Initializes 'polling_timer' attribute to None")
    def test_polling_timer(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.polling_timer is None

    @pytest.mark.it("Initializes 'provisioning_timeout_timer' attribute to None")
    def test_provisioning_timeout_timer(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.provisioning_timeout_timer is None


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_provisioning.PollStatusOperation,
    op_test_config_class=PollStatusOperationTestConfig,
    extended_op_instantiation_test_class=PollStatusOperationInstantiationTests,
)
