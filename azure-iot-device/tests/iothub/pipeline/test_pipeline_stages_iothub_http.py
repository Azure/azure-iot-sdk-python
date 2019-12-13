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
    mock = mocker.patch("azure.iot.device.iothub.pipeline.http_path_iothub")
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

    @pytest.fixture(params=[True, False], ids=["w/ CA cert", "No CA cert"])
    def use_ca_cert(self, request):
        return request.param

    @pytest.fixture(params=["Device", "Module"])
    def op(self, mocker, request, auth_type, use_gateway_hostname, use_ca_cert):
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

        if use_ca_cert:
            kwargs["ca_cert"] = "fake_ca_cert"

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
        assert new_op.ca_cert == op.ca_cert
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


# CT-TODO: Revisit this

# @pytest.mark.describe("IoTHubHTTPTranslationStage - .run_op() -- Called with MethodInvokeOperation op")
# class TestIoTHubHTTPTranslationStageRunOpCalledWithMethodInvokeOperation(IoTHubHTTPTranslationStageTestConfig, StageRunOpTestBase):
#     @pytest.fixture
#     def op(self, mocker):
#         return pipeline_ops_iothub_http.MethodInvokeOperation(device_id="fake_device_id")


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

    @pytest.mark.it(
        "Sends a new HTTPRequestAndResponseOperation op down the pipeline, configured to request storage info based on the stage details and the GetStorageInfoOperation op"
    )
    def test_sends_op_down(self, mocker, stage, op, mock_http_path_iothub):
        stage.run_op(op)

        # Op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_http.HTTPRequestAndResponseOperation)

        mock_http_path_iothub.call_count == 1
        mock_http_path_iothub.call_args == mocker.call(stage.device_id)

        # Validate op
        assert new_op.method == "POST"
        assert new_op.path == mock_http_path_iothub.get_storage_info_path.return_value

        # Validate body
        assert new_op.body == '{"blobName": "{}"}'.format(op.blob_name)

        # Validate headers
        assert new_op.headers["Host"] == stage.hostname
        assert new_op.headers["Accept"] == "application/json"
        assert new_op.headers["Content-Type"] == "application/json"
        assert new_op.headers["Content-Length"] == len(new_op.body)
