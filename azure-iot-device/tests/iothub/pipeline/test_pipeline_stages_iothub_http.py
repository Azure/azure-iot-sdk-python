# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import functools
import logging
import pytest
import json
import sys
import six.moves.urllib as urllib
from azure.iot.device.common.pipeline import (
    pipeline_events_base,
    pipeline_ops_base,
    pipeline_stages_base,
    pipeline_ops_http,
)
from azure.iot.device.iothub.pipeline import (
    constant,
    pipeline_events_iothub,
    pipeline_ops_iothub,
    pipeline_ops_iothub_http,
    pipeline_stages_iothub_http,
    config,
)
from azure.iot.device.iothub.pipeline.exceptions import OperationError, PipelineError
from azure.iot.device.exceptions import ServiceError
from azure.iot.device.iothub.models.message import Message
from azure.iot.device.iothub.models.methods import MethodRequest, MethodResponse
from tests.common.pipeline.helpers import StageRunOpTestBase
from tests.common.pipeline import pipeline_stage_test
from azure.iot.device import constant as pkg_constant
import uuid

logging.basicConfig(level=logging.DEBUG)
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")
this_module = sys.modules[__name__]

###################
# COMMON FIXTURES #
###################


@pytest.fixture(params=[True, False], ids=["With error", "No error"])
def op_error(request, arbitrary_exception):
    if request.param:
        return arbitrary_exception
    else:
        return None


@pytest.fixture
def mock_http_path_iothub(mocker):
    mock = mocker.patch(
        "azure.iot.device.iothub.pipeline.pipeline_stages_iothub_http.http_path_iothub"
    )
    return mock


##################################
# IOT HUB HTTP TRANSLATION STAGE #
##################################


class IoTHubHTTPTranslationStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_iothub_http.IoTHubHTTPTranslationStage

    @pytest.fixture
    def init_kwargs(self):
        return {}

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        return stage


class IoTHubHTTPTranslationStageInstantiationTests(IoTHubHTTPTranslationStageTestConfig):
    @pytest.mark.it("Initializes 'device_id' as None")
    def test_device_id(self, init_kwargs):
        stage = pipeline_stages_iothub_http.IoTHubHTTPTranslationStage(**init_kwargs)
        assert stage.device_id is None

    @pytest.mark.it("Initializes 'module_id' as None")
    def test_module_id(self, init_kwargs):
        stage = pipeline_stages_iothub_http.IoTHubHTTPTranslationStage(**init_kwargs)
        assert stage.module_id is None

    @pytest.mark.it("Initializes 'hostname' as None")
    def test_hostname(self, init_kwargs):
        stage = pipeline_stages_iothub_http.IoTHubHTTPTranslationStage(**init_kwargs)
        assert stage.hostname is None


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_iothub_http.IoTHubHTTPTranslationStage,
    stage_test_config_class=IoTHubHTTPTranslationStageTestConfig,
    extended_stage_instantiation_test_class=IoTHubHTTPTranslationStageInstantiationTests,
)


@pytest.mark.describe(
    "IoTHubHTTPTranslationStage - .run_op() -- Called with SetIoTHubConnectionArgsOperation op"
)
class TestIoTHubHTTPTranslationStageRunOpCalledWithConnectionArgsOperation(
    IoTHubHTTPTranslationStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture(params=["SAS", "X509"])
    def auth_type(self, request):
        return request.param

    @pytest.fixture(params=[True, False], ids=["w/ GatewayHostName", "No GatewayHostName"])
    def use_gateway_hostname(self, request):
        return request.param

    @pytest.fixture(
        params=[True, False], ids=["w/ server verification cert", "No server verification cert"]
    )
    def use_server_verification_cert(self, request):
        return request.param

    @pytest.fixture(params=["Device", "Module"])
    def op(self, mocker, request, auth_type, use_gateway_hostname, use_server_verification_cert):
        kwargs = {
            "device_id": "fake_device_id",
            "hostname": "fake_hostname",
            "callback": mocker.MagicMock(),
        }
        if request.param == "Module":
            kwargs["module_id"] = "fake_module_id"

        if auth_type == "SAS":
            kwargs["sas_token"] = "fake_sas_token"
        else:
            kwargs["client_cert"] = mocker.MagicMock()  # representing X509 obj

        if use_gateway_hostname:
            kwargs["gateway_hostname"] = "fake_gateway_hostname"

        if use_server_verification_cert:
            kwargs["server_verification_cert"] = "fake_server_verification_cert"

        return pipeline_ops_iothub.SetIoTHubConnectionArgsOperation(**kwargs)

    @pytest.mark.it(
        "Sets the 'device_id' and 'module_id' values from the op as the stage's 'device_id' and 'module_id' attributes"
    )
    def test_cache_device_id_and_module_id(self, stage, op):
        assert stage.device_id is None
        assert stage.module_id is None

        stage.run_op(op)

        assert stage.device_id == op.device_id
        assert stage.module_id == op.module_id

    @pytest.mark.it(
        "Sets the 'gateway_hostname' value from the op as the stage's 'hostname' attribute if one is provided, otherwise, use the op's 'hostname'"
    )
    def test_cache_hostname(self, stage, op):
        assert stage.hostname is None
        stage.run_op(op)

        if op.gateway_hostname is not None:
            assert stage.hostname == op.gateway_hostname
            assert stage.hostname != op.hostname
        else:
            assert stage.hostname == op.hostname
            assert stage.hostname != op.gateway_hostname

    @pytest.mark.it(
        "Sends a new SetHTTPConnectionArgsOperation op down the pipeline, configured based on the settings of the SetIoTHubConnectionArgsOperation"
    )
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.SetHTTPConnectionArgsOperation)

        # Validate contents of the op
        assert new_op.hostname == stage.hostname
        assert new_op.server_verification_cert == op.server_verification_cert
        assert new_op.client_cert == op.client_cert
        assert new_op.sas_token == op.sas_token

    @pytest.mark.it(
        "Completes the original SetIoTHubConnectionArgsOperation (with the same error, or lack thereof) if the new SetHTTPConnectionArgsOperation is completed later on"
    )
    def test_completing_new_op_completes_original(self, mocker, stage, op_error, op):
        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]

        assert not op.completed
        assert not new_op.completed

        new_op.complete(error=op_error)

        assert new_op.completed
        assert new_op.error is op_error
        assert op.completed
        assert op.error is op_error


@pytest.mark.describe(
    "IoTHubHTTPTranslationStage - .run_op() -- Called with MethodInvokeOperation op"
)
class TestIoTHubHTTPTranslationStageRunOpCalledWithMethodInvokeOperation(
    IoTHubHTTPTranslationStageTestConfig, StageRunOpTestBase
):
    # Because Storage/Blob related functionality is limited to Module, configure the stage for a module
    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        pl_config = config.IoTHubPipelineConfig()
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=pl_config
        )
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        stage.device_id = "fake_device_id"
        stage.module_id = "fake_module_id"
        stage.hostname = "fake_hostname"
        return stage

    @pytest.fixture(params=["Targeting Device Method", "Targeting Module Method"])
    def op(self, mocker, request):
        method_params = {"arg1": "val", "arg2": 2, "arg3": True}
        if request.param == "Targeting Device Method":
            return pipeline_ops_iothub_http.MethodInvokeOperation(
                target_device_id="fake_target_device_id",
                target_module_id=None,
                method_params=method_params,
                callback=mocker.MagicMock(),
            )
        else:
            return pipeline_ops_iothub_http.MethodInvokeOperation(
                target_device_id="fake_target_device_id",
                target_module_id="fake_target_module_id",
                method_params=method_params,
                callback=mocker.MagicMock(),
            )

    @pytest.mark.it("Sends a new HTTPRequestAndResponseOperation op down the pipeline")
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

    @pytest.mark.it(
        "Configures the HTTPRequestAndResponseOperation with request details for sending a Method Invoke request"
    )
    def test_sends_get_storage_request(self, mocker, stage, op, mock_http_path_iothub):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Validate request
        assert mock_http_path_iothub.get_method_invoke_path.call_count == 1
        assert mock_http_path_iothub.get_method_invoke_path.call_args == mocker.call(
            op.target_device_id, op.target_module_id
        )
        expected_path = mock_http_path_iothub.get_method_invoke_path.return_value

        assert new_op.method == "POST"
        assert new_op.path == expected_path
        assert new_op.query_params == "api-version={}".format(pkg_constant.IOTHUB_API_VERSION)

    @pytest.mark.it(
        "Configures the HTTPRequestAndResponseOperation with the headers for a Method Invoke request"
    )
    @pytest.mark.parametrize(
        "custom_user_agent",
        [
            pytest.param("", id="No custom user agent"),
            pytest.param("MyCustomUserAgent", id="With custom user agent"),
            pytest.param(
                "My/Custom?User+Agent", id="With custom user agent containing reserved characters"
            ),
            pytest.param(12345, id="Non-string custom user agent"),
        ],
    )
    def test_new_op_headers(self, mocker, stage, op, custom_user_agent):
        stage.pipeline_root.pipeline_configuration.product_info = custom_user_agent
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Validate headers
        expected_user_agent = urllib.parse.quote_plus(
            pkg_constant.USER_AGENT + str(custom_user_agent)
        )
        expected_edge_string = "{}/{}".format(stage.device_id, stage.module_id)

        assert new_op.headers["Host"] == stage.hostname
        assert new_op.headers["Content-Type"] == "application/json"
        assert new_op.headers["Content-Length"] == len(new_op.body)
        assert new_op.headers["x-ms-edge-moduleId"] == expected_edge_string
        assert new_op.headers["User-Agent"] == expected_user_agent

    @pytest.mark.it(
        "Configures the HTTPRequestAndResponseOperation with a body for a Method Invoke request"
    )
    def test_new_op_body(self, mocker, stage, op):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Validate body
        assert new_op.body == json.dumps(op.method_params)

    @pytest.mark.it(
        "Completes the original MethodInvokeOperation op (no error) if the new HTTPRequestAndResponseOperation op is completed later on (no error) with a status code indicating success"
    )
    def test_new_op_completes_with_good_code(self, mocker, stage, op):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Neither op is completed
        assert not op.completed
        assert op.error is None
        assert not new_op.completed
        assert new_op.error is None

        # Complete new op
        new_op.response_body = b'{"some_response_key": "some_response_value"}'
        new_op.status_code = 200
        new_op.complete()

        # Both ops are now completed successfully
        assert new_op.completed
        assert new_op.error is None
        assert op.completed
        assert op.error is None

    @pytest.mark.it(
        "Deserializes the completed HTTPRequestAndResponseOperation op's 'response_body' (the received storage info) and set it on the MethodInvokeOperation op as the 'method_response', if the HTTPRequestAndResponseOperation is completed later (no error) with a status code indicating success"
    )
    @pytest.mark.parametrize(
        "response_body, expected_method_response",
        [
            pytest.param(
                b'{"key": "val"}', {"key": "val"}, id="Response Body: dict value as bytestring"
            ),
            pytest.param(
                b'{"key": "val", "key2": {"key3": "val2"}}',
                {"key": "val", "key2": {"key3": "val2"}},
                id="Response Body: dict value as bytestring",
            ),
        ],
    )
    def test_deserializes_response(
        self, mocker, stage, op, response_body, expected_method_response
    ):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Original op has no 'method_response'
        assert op.method_response is None

        # Complete new op
        new_op.response_body = response_body
        new_op.status_code = 200
        new_op.complete()

        # Method Response is set
        assert op.method_response == expected_method_response

    @pytest.mark.it(
        "Completes the original MethodInvokeOperation op with a ServiceError if the new HTTPRequestAndResponseOperation is completed later on (no error) with a status code indicating non-success"
    )
    @pytest.mark.parametrize(
        "status_code",
        [
            pytest.param(300, id="Status Code: 300"),
            pytest.param(400, id="Status Code: 400"),
            pytest.param(500, id="Status Code: 500"),
        ],
    )
    def test_new_op_completes_with_bad_code(self, mocker, stage, op, status_code):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Neither op is completed
        assert not op.completed
        assert op.error is None
        assert not new_op.completed
        assert new_op.error is None

        # Complete new op successfully (but with a bad status code)
        new_op.status_code = status_code
        new_op.complete()

        # The original op is now completed with a ServiceError
        assert new_op.completed
        assert new_op.error is None
        assert op.completed
        assert isinstance(op.error, ServiceError)

    @pytest.mark.it(
        "Completes the original MethodInvokeOperation op with the error from the new HTTPRequestAndResponseOperation, if the HTTPRequestAndResponseOperation is completed later on with error"
    )
    def test_new_op_completes_with_error(self, mocker, stage, op, arbitrary_exception):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Neither op is completed
        assert not op.completed
        assert op.error is None
        assert not new_op.completed
        assert new_op.error is None

        # Complete new op with error
        new_op.complete(error=arbitrary_exception)

        # The original op is now completed with a ServiceError
        assert new_op.completed
        assert new_op.error is arbitrary_exception
        assert op.completed
        assert op.error is arbitrary_exception


@pytest.mark.describe(
    "IoTHubHTTPTranslationStage - .run_op() -- Called with GetStorageInfoOperation op"
)
class TestIoTHubHTTPTranslationStageRunOpCalledWithGetStorageInfoOperation(
    IoTHubHTTPTranslationStageTestConfig, StageRunOpTestBase
):

    # Because Storage/Blob related functionality is limited to Devices, configure the stage for a device
    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        pl_config = config.IoTHubPipelineConfig()
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=pl_config
        )
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        stage.device_id = "fake_device_id"
        stage.module_id = None
        stage.hostname = "fake_hostname"
        return stage

    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_iothub_http.GetStorageInfoOperation(
            blob_name="fake_blob_name", callback=mocker.MagicMock()
        )

    @pytest.mark.it("Sends a new HTTPRequestAndResponseOperation op down the pipeline")
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

    @pytest.mark.it(
        "Configures the HTTPRequestAndResponseOperation with request details for sending a Get Storage Info request"
    )
    def test_sends_get_storage_request(self, mocker, stage, op, mock_http_path_iothub):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Validate request
        assert mock_http_path_iothub.get_storage_info_for_blob_path.call_count == 1
        assert mock_http_path_iothub.get_storage_info_for_blob_path.call_args == mocker.call(
            stage.device_id
        )
        expected_path = mock_http_path_iothub.get_storage_info_for_blob_path.return_value

        assert new_op.method == "POST"
        assert new_op.path == expected_path
        assert new_op.query_params == "api-version={}".format(pkg_constant.IOTHUB_API_VERSION)

    @pytest.mark.it(
        "Configures the HTTPRequestAndResponseOperation with the headers for a Get Storage Info request"
    )
    @pytest.mark.parametrize(
        "custom_user_agent",
        [
            pytest.param("", id="No custom user agent"),
            pytest.param("MyCustomUserAgent", id="With custom user agent"),
            pytest.param(
                "My/Custom?User+Agent", id="With custom user agent containing reserved characters"
            ),
            pytest.param(12345, id="Non-string custom user agent"),
        ],
    )
    def test_new_op_headers(self, mocker, stage, op, custom_user_agent):
        stage.pipeline_root.pipeline_configuration.product_info = custom_user_agent
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Validate headers
        expected_user_agent = urllib.parse.quote_plus(
            pkg_constant.USER_AGENT + str(custom_user_agent)
        )

        assert new_op.headers["Host"] == stage.hostname
        assert new_op.headers["Accept"] == "application/json"
        assert new_op.headers["Content-Type"] == "application/json"
        assert new_op.headers["Content-Length"] == len(new_op.body)
        assert new_op.headers["User-Agent"] == expected_user_agent

    @pytest.mark.it(
        "Configures the HTTPRequestAndResponseOperation with a body for a Get Storage Info request"
    )
    def test_new_op_body(self, mocker, stage, op):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Validate body
        assert new_op.body == '{{"blobName": "{}"}}'.format(op.blob_name)

    @pytest.mark.it(
        "Completes the original GetStorageInfoOperation op (no error) if the new HTTPRequestAndResponseOperation is completed later on (no error) with a status code indicating success"
    )
    def test_new_op_completes_with_good_code(self, mocker, stage, op):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Neither op is completed
        assert not op.completed
        assert op.error is None
        assert not new_op.completed
        assert new_op.error is None

        # Complete new op
        new_op.response_body = b'{"json": "response"}'
        new_op.status_code = 200
        new_op.complete()

        # Both ops are now completed successfully
        assert new_op.completed
        assert new_op.error is None
        assert op.completed
        assert op.error is None

    @pytest.mark.it(
        "Deserializes the completed HTTPRequestAndResponseOperation op's 'response_body' (the received storage info) and set it on the GetStorageInfoOperation as the 'storage_info', if the HTTPRequestAndResponseOperation is completed later (no error) with a status code indicating success"
    )
    def test_deserializes_response(self, mocker, stage, op):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Original op has no 'storage_info'
        assert op.storage_info is None

        # Complete new op
        new_op.response_body = b'{\
            "hostName": "fake_hostname",\
            "containerName": "fake_container_name",\
            "blobName": "fake_blob_name",\
            "sasToken": "fake_sas_token",\
            "correlationId": "fake_correlation_id"\
        }'
        new_op.status_code = 200
        new_op.complete()

        # Storage Info is set
        assert op.storage_info == {
            "hostName": "fake_hostname",
            "containerName": "fake_container_name",
            "blobName": "fake_blob_name",
            "sasToken": "fake_sas_token",
            "correlationId": "fake_correlation_id",
        }

    @pytest.mark.it(
        "Completes the original GetStorageInfoOperation op with a ServiceError if the new HTTPRequestAndResponseOperation is completed later on (no error) with a status code indicating non-success"
    )
    @pytest.mark.parametrize(
        "status_code",
        [
            pytest.param(300, id="Status Code: 300"),
            pytest.param(400, id="Status Code: 400"),
            pytest.param(500, id="Status Code: 500"),
        ],
    )
    def test_new_op_completes_with_bad_code(self, mocker, stage, op, status_code):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Neither op is completed
        assert not op.completed
        assert op.error is None
        assert not new_op.completed
        assert new_op.error is None

        # Complete new op successfully (but with a bad status code)
        new_op.status_code = status_code
        new_op.complete()

        # The original op is now completed with a ServiceError
        assert new_op.completed
        assert new_op.error is None
        assert op.completed
        assert isinstance(op.error, ServiceError)

    @pytest.mark.it(
        "Completes the original GetStorageInfoOperation op with the error from the new HTTPRequestAndResponseOperation, if the HTTPRequestAndResponseOperation is completed later on with error"
    )
    def test_new_op_completes_with_error(self, mocker, stage, op, arbitrary_exception):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Neither op is completed
        assert not op.completed
        assert op.error is None
        assert not new_op.completed
        assert new_op.error is None

        # Complete new op with error
        new_op.complete(error=arbitrary_exception)

        # The original op is now completed with a ServiceError
        assert new_op.completed
        assert new_op.error is arbitrary_exception
        assert op.completed
        assert op.error is arbitrary_exception


@pytest.mark.describe(
    "IoTHubHTTPTranslationStage - .run_op() -- Called with NotifyBlobUploadStatusOperation op"
)
class TestIoTHubHTTPTranslationStageRunOpCalledWithNotifyBlobUploadStatusOperation(
    IoTHubHTTPTranslationStageTestConfig, StageRunOpTestBase
):

    # Because Storage/Blob related functionality is limited to Devices, configure the stage for a device
    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        pl_config = config.IoTHubPipelineConfig()
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=pl_config
        )
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        stage.device_id = "fake_device_id"
        stage.module_id = None
        stage.hostname = "fake_hostname"
        return stage

    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_iothub_http.NotifyBlobUploadStatusOperation(
            correlation_id="fake_correlation_id",
            is_success=True,
            status_code=203,
            status_description="fake_description",
            callback=mocker.MagicMock(),
        )

    @pytest.mark.it("Sends a new HTTPRequestAndResponseOperation op down the pipeline")
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

    @pytest.mark.it(
        "Configures the HTTPRequestAndResponseOperation with request details for sending a Notify Blob Upload Status request"
    )
    def test_sends_get_storage_request(self, mocker, stage, op, mock_http_path_iothub):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Validate request
        assert mock_http_path_iothub.get_notify_blob_upload_status_path.call_count == 1
        assert mock_http_path_iothub.get_notify_blob_upload_status_path.call_args == mocker.call(
            stage.device_id
        )
        expected_path = mock_http_path_iothub.get_notify_blob_upload_status_path.return_value

        assert new_op.method == "POST"
        assert new_op.path == expected_path
        assert new_op.query_params == "api-version={}".format(pkg_constant.IOTHUB_API_VERSION)

    @pytest.mark.it(
        "Configures the HTTPRequestAndResponseOperation with the headers for a Notify Blob Upload Status request"
    )
    @pytest.mark.parametrize(
        "custom_user_agent",
        [
            pytest.param("", id="No custom user agent"),
            pytest.param("MyCustomUserAgent", id="With custom user agent"),
            pytest.param(
                "My/Custom?User+Agent", id="With custom user agent containing reserved characters"
            ),
            pytest.param(12345, id="Non-string custom user agent"),
        ],
    )
    def test_new_op_headers(self, mocker, stage, op, custom_user_agent):
        stage.pipeline_root.pipeline_configuration.product_info = custom_user_agent
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Validate headers
        expected_user_agent = urllib.parse.quote_plus(
            pkg_constant.USER_AGENT + str(custom_user_agent)
        )

        assert new_op.headers["Host"] == stage.hostname
        assert new_op.headers["Content-Type"] == "application/json; charset=utf-8"
        assert new_op.headers["Content-Length"] == len(new_op.body)
        assert new_op.headers["User-Agent"] == expected_user_agent

    @pytest.mark.it(
        "Configures the HTTPRequestAndResponseOperation with a body for a Notify Blob Upload Status request"
    )
    def test_new_op_body(self, mocker, stage, op):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Validate body
        header_dict = {
            "correlationId": op.correlation_id,
            "isSuccess": op.is_success,
            "statusCode": op.request_status_code,
            "statusDescription": op.status_description,
        }
        assert new_op.body == json.dumps(header_dict)

    @pytest.mark.it(
        "Completes the original NotifyBlobUploadStatusOperation op (no error) if the new HTTPRequestAndResponseOperation is completed later on (no error) with a status code indicating success"
    )
    def test_new_op_completes_with_good_code(self, mocker, stage, op):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Neither op is completed
        assert not op.completed
        assert op.error is None
        assert not new_op.completed
        assert new_op.error is None

        # Complete new op
        new_op.status_code = 200
        new_op.complete()

        # Both ops are now completed successfully
        assert new_op.completed
        assert new_op.error is None
        assert op.completed
        assert op.error is None

    @pytest.mark.it(
        "Completes the original NotifyBlobUploadStatusOperation op with a ServiceError if the new HTTPRequestAndResponseOperation is completed later on (no error) with a status code indicating non-success"
    )
    @pytest.mark.parametrize(
        "status_code",
        [
            pytest.param(300, id="Status Code: 300"),
            pytest.param(400, id="Status Code: 400"),
            pytest.param(500, id="Status Code: 500"),
        ],
    )
    def test_new_op_completes_with_bad_code(self, mocker, stage, op, status_code):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Neither op is completed
        assert not op.completed
        assert op.error is None
        assert not new_op.completed
        assert new_op.error is None

        # Complete new op successfully (but with a bad status code)
        new_op.status_code = status_code
        new_op.complete()

        # The original op is now completed with a ServiceError
        assert new_op.completed
        assert new_op.error is None
        assert op.completed
        assert isinstance(op.error, ServiceError)

    @pytest.mark.it(
        "Completes the original NotifyBlobUploadStatusOperation op with the error from the new HTTPRequestAndResponseOperation, if the HTTPRequestAndResponseOperation is completed later on with error"
    )
    def test_new_op_completes_with_error(self, mocker, stage, op, arbitrary_exception):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        # Neither op is completed
        assert not op.completed
        assert op.error is None
        assert not new_op.completed
        assert new_op.error is None

        # Complete new op with error
        new_op.complete(error=arbitrary_exception)

        # The original op is now completed with a ServiceError
        assert new_op.completed
        assert new_op.error is arbitrary_exception
        assert op.completed
        assert op.error is arbitrary_exception
