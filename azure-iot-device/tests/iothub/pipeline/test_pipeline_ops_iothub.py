# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import sys
import logging
from azure.iot.device.iothub.pipeline import pipeline_ops_iothub
from tests.common.pipeline import pipeline_ops_test

logging.basicConfig(level=logging.DEBUG)
this_module = sys.modules[__name__]
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")


class SetAuthProviderOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub.SetAuthProviderOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"auth_provider": mocker.MagicMock(), "callback": mocker.MagicMock()}
        return kwargs


class SetAuthProviderOperationInstantiationTests(SetAuthProviderOperationTestConfig):
    @pytest.mark.it(
        "Initializes 'auth_provider' attribute with the provided 'auth_provider' parameter"
    )
    def test_auth_provider(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.auth_provider is init_kwargs["auth_provider"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub.SetAuthProviderOperation,
    op_test_config_class=SetAuthProviderOperationTestConfig,
    extended_op_instantiation_test_class=SetAuthProviderOperationInstantiationTests,
)


class SetX509AuthProviderOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub.SetX509AuthProviderOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"auth_provider": mocker.MagicMock(), "callback": mocker.MagicMock()}
        return kwargs


class SetX509AuthProviderOperationInstantiationTests(SetX509AuthProviderOperationTestConfig):
    @pytest.mark.it(
        "Initializes 'auth_provider' attribute with the provided 'auth_provider' parameter"
    )
    def test_auth_provider(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.auth_provider is init_kwargs["auth_provider"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub.SetX509AuthProviderOperation,
    op_test_config_class=SetX509AuthProviderOperationTestConfig,
    extended_op_instantiation_test_class=SetX509AuthProviderOperationInstantiationTests,
)


class SetIoTHubConnectionArgsOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub.SetIoTHubConnectionArgsOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {
            "device_id": "some_device_id",
            "hostname": "some_hostname",
            "callback": mocker.MagicMock(),
            "module_id": "some_module_id",
            "gateway_hostname": "some_gateway_hostname",
            "server_verification_cert": "some_server_verification_cert",
            "client_cert": "some_client_cert",
            "sas_token": "some_sas_token",
        }
        return kwargs


class SetIoTHubConnectionArgsOperationInstantiationTests(
    SetIoTHubConnectionArgsOperationTestConfig
):
    @pytest.mark.it("Initializes 'device_id' attribute with the provided 'device_id' parameter")
    def test_device_id(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.device_id == init_kwargs["device_id"]

    @pytest.mark.it("Initializes 'hostname' attribute with the provided 'hostname' parameter")
    def test_hostname(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.hostname == init_kwargs["hostname"]

    @pytest.mark.it("Initializes 'module_id' attribute with the provided 'module_id' parameter")
    def test_module_id(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.module_id == init_kwargs["module_id"]

    @pytest.mark.it(
        "Initializes 'module_id' attribute to None if no 'module_id' parameter is provided"
    )
    def test_module_id_default(self, cls_type, init_kwargs):
        del init_kwargs["module_id"]
        op = cls_type(**init_kwargs)
        assert op.module_id is None

    @pytest.mark.it(
        "Initializes 'gateway_hostname' attribute with the provided 'gateway_hostname' parameter"
    )
    def test_gateway_hostname(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.gateway_hostname == init_kwargs["gateway_hostname"]

    @pytest.mark.it(
        "Initializes 'gateway_hostname' attribute to None if no 'gateway_hostname' parameter is provided"
    )
    def test_gateway_hostname_default(self, cls_type, init_kwargs):
        del init_kwargs["gateway_hostname"]
        op = cls_type(**init_kwargs)
        assert op.gateway_hostname is None

    @pytest.mark.it(
        "Initializes 'server_verification_cert' attribute with the provided 'server_verification_cert' parameter"
    )
    def test_server_verification_cert(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.server_verification_cert == init_kwargs["server_verification_cert"]

    @pytest.mark.it(
        "Initializes 'server_verification_cert' attribute to None if no 'server_verification_cert' parameter is provided"
    )
    def test_server_verification_cert_default(self, cls_type, init_kwargs):
        del init_kwargs["server_verification_cert"]
        op = cls_type(**init_kwargs)
        assert op.server_verification_cert is None

    @pytest.mark.it("Initializes 'client_cert' attribute with the provided 'client_cert' parameter")
    def test_client_cert(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.client_cert == init_kwargs["client_cert"]

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
        assert op.sas_token == init_kwargs["sas_token"]

    @pytest.mark.it(
        "Initializes 'sas_token' attribute to None if no 'sas_token' parameter is provided"
    )
    def test_sas_token_default(self, cls_type, init_kwargs):
        del init_kwargs["sas_token"]
        op = cls_type(**init_kwargs)
        assert op.sas_token is None


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub.SetIoTHubConnectionArgsOperation,
    op_test_config_class=SetIoTHubConnectionArgsOperationTestConfig,
    extended_op_instantiation_test_class=SetIoTHubConnectionArgsOperationInstantiationTests,
)


class SendD2CMessageOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub.SendD2CMessageOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"message": mocker.MagicMock(), "callback": mocker.MagicMock()}
        return kwargs


class SendD2CMessageOperationInstantiationTests(SendD2CMessageOperationTestConfig):
    @pytest.mark.it("Initializes 'message' attribute with the provided 'message' parameter")
    def test_message(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.message is init_kwargs["message"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub.SendD2CMessageOperation,
    op_test_config_class=SendD2CMessageOperationTestConfig,
    extended_op_instantiation_test_class=SendD2CMessageOperationInstantiationTests,
)


class SendOutputEventOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub.SendOutputEventOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"message": mocker.MagicMock(), "callback": mocker.MagicMock()}
        return kwargs


class SendOutputEventOperationInstantiationTests(SendOutputEventOperationTestConfig):
    @pytest.mark.it("Initializes 'message' attribute with the provided 'message' parameter")
    def test_message(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.message is init_kwargs["message"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub.SendOutputEventOperation,
    op_test_config_class=SendOutputEventOperationTestConfig,
    extended_op_instantiation_test_class=SendOutputEventOperationInstantiationTests,
)


class SendMethodResponseOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub.SendMethodResponseOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"method_response": mocker.MagicMock(), "callback": mocker.MagicMock()}
        return kwargs


class SendMethodResponseOperationInstantiationTests(SendMethodResponseOperationTestConfig):
    @pytest.mark.it(
        "Initializes 'method_response' attribute with the provided 'method_response' parameter"
    )
    def test_method_response(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.method_response is init_kwargs["method_response"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub.SendMethodResponseOperation,
    op_test_config_class=SendMethodResponseOperationTestConfig,
    extended_op_instantiation_test_class=SendMethodResponseOperationInstantiationTests,
)


class GetTwinOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub.GetTwinOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"callback": mocker.MagicMock()}
        return kwargs


class GetTwinOperationInstantiationTests(GetTwinOperationTestConfig):
    @pytest.mark.it("Initializes 'twin' attribute as None")
    def test_twin(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.twin is None


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub.GetTwinOperation,
    op_test_config_class=GetTwinOperationTestConfig,
    extended_op_instantiation_test_class=GetTwinOperationInstantiationTests,
)


class PatchTwinReportedPropertiesOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub.PatchTwinReportedPropertiesOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"patch": {"some": "patch"}, "callback": mocker.MagicMock()}
        return kwargs


class PatchTwinReportedPropertiesOperationInstantiationTests(
    PatchTwinReportedPropertiesOperationTestConfig
):
    @pytest.mark.it("Initializes 'patch' attribute with the provided 'patch' parameter")
    def test_patch(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.patch is init_kwargs["patch"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub.PatchTwinReportedPropertiesOperation,
    op_test_config_class=PatchTwinReportedPropertiesOperationTestConfig,
    extended_op_instantiation_test_class=PatchTwinReportedPropertiesOperationInstantiationTests,
)
