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


class SetSymmetricKeySecurityClientOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_provisioning.SetSymmetricKeySecurityClientOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"security_client": mocker.MagicMock(), "callback": mocker.MagicMock()}
        return kwargs


class SetSymmetricKeySecurityClientOperationInstantiationTests(
    SetSymmetricKeySecurityClientOperationTestConfig
):
    @pytest.mark.it(
        "Initializes 'security_client' attribute with the provided 'security_client' parameter"
    )
    def test_security_client(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.security_client is init_kwargs["security_client"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_provisioning.SetSymmetricKeySecurityClientOperation,
    op_test_config_class=SetSymmetricKeySecurityClientOperationTestConfig,
    extended_op_instantiation_test_class=SetSymmetricKeySecurityClientOperationInstantiationTests,
)


class SetX509SecurityClientOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_provisioning.SetX509SecurityClientOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"security_client": mocker.MagicMock(), "callback": mocker.MagicMock()}
        return kwargs


class SetX509SecurityClientOperationInstantiationTests(SetX509SecurityClientOperationTestConfig):
    @pytest.mark.it(
        "Initializes 'security_client' attribute with the provided 'security_client' parameter"
    )
    def test_security_client(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.security_client is init_kwargs["security_client"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_provisioning.SetX509SecurityClientOperation,
    op_test_config_class=SetX509SecurityClientOperationTestConfig,
    extended_op_instantiation_test_class=SetX509SecurityClientOperationInstantiationTests,
)


class SetProvisioningClientConnectionArgsOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_provisioning.SetProvisioningClientConnectionArgsOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {
            "provisioning_host": "some_provisioning_host",
            "registration_id": "some_registration_id",
            "id_scope": "some_id_scope",
            "callback": mocker.MagicMock(),
            "client_cert": "some_client_cert",
            "sas_token": "some_sas_token",
        }
        return kwargs


class SetProvisioningClientConnectionArgsOperationInstantiationTests(
    SetProvisioningClientConnectionArgsOperationTestConfig
):
    @pytest.mark.it(
        "Initializes 'provisioning_host' attribute with the provided 'provisioning_host' parameter"
    )
    def test_provisioning_host(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.provisioning_host is init_kwargs["provisioning_host"]

    @pytest.mark.it(
        "Initializes 'registration_id' attribute with the provided 'registration_id' parameter"
    )
    def test_registration_id(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.registration_id is init_kwargs["registration_id"]

    @pytest.mark.it("Initializes 'id_scope' attribute with the provided 'id_scope' parameter")
    def test_id_scope(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.id_scope is init_kwargs["id_scope"]

    @pytest.mark.it("Initializes 'client_cert' attribute with the provided 'client_cert' parameter")
    def test_client_cert(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.client_cert is init_kwargs["client_cert"]

    @pytest.mark.it(
        "Initializes 'client_cert' attribute to None if no 'client_cert' parameter is provided"
    )
    def test_client_cert_default(self, cls_type, init_kwargs):
        del init_kwargs["client_cert"]
        op = cls_type(**init_kwargs)
        assert op.client_cert is None

    @pytest.mark.it("Initializes 'sas_token' attribute with the provided 'sas_token' parameter")
    def test_sas_token(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.sas_token is init_kwargs["sas_token"]

    @pytest.mark.it(
        "Initializes 'sas_token' attribute to None if no 'sas_token' parameter is provided"
    )
    def test_sas_token_default(self, cls_type, init_kwargs):
        del init_kwargs["sas_token"]
        op = cls_type(**init_kwargs)
        assert op.sas_token is None


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_provisioning.SetProvisioningClientConnectionArgsOperation,
    op_test_config_class=SetProvisioningClientConnectionArgsOperationTestConfig,
    extended_op_instantiation_test_class=SetProvisioningClientConnectionArgsOperationInstantiationTests,
)


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
