# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import json
import logging
import pytest
import sys
from azure.iot.device.exceptions import ServiceError
from azure.iot.device.iothub.pipeline import (
    pipeline_ops_iothub,
    pipeline_stages_iothub,
)
from azure.iot.device.common.pipeline import pipeline_ops_base
from tests.unit.common.pipeline.helpers import StageRunOpTestBase
from tests.unit.common.pipeline import pipeline_stage_test

logging.basicConfig(level=logging.DEBUG)
this_module = sys.modules[__name__]
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")


fake_device_id = "__fake_device_id__"
fake_module_id = "__fake_module_id__"
fake_hostname = "__fake_hostname__"
fake_gateway_hostname = "__fake_gateway_hostname__"
fake_server_verification_cert = "__fake_server_verification_cert__"
fake_sas_token = "__fake_sas_token__"
fake_symmetric_key = "Zm9vYmFy"
fake_x509_cert_file = "fake_certificate_file"
fake_x509_cert_key_file = "fake_certificate_key_file"
fake_pass_phrase = "fake_pass_phrase"


###################
# COMMON FIXTURES #
###################


@pytest.fixture(params=[True, False], ids=["With error", "No error"])
def op_error(request, arbitrary_exception):
    if request.param:
        return arbitrary_exception
    else:
        return None


###############################
# TWIN REQUEST RESPONSE STAGE #
###############################


class TwinRequestResponseStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_iothub.TwinRequestResponseStage

    @pytest.fixture
    def init_kwargs(self):
        return {}

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")
        return stage


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_iothub.TwinRequestResponseStage,
    stage_test_config_class=TwinRequestResponseStageTestConfig,
)


@pytest.mark.describe("TwinRequestResponseStage - .run_op() -- Called with GetTwinOperation")
class TestTwinRequestResponseStageRunOpWithGetTwinOperation(
    StageRunOpTestBase, TwinRequestResponseStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_iothub.GetTwinOperation(callback=mocker.MagicMock())

    @pytest.mark.it(
        "Sends a new RequestAndResponseOperation down the pipeline, configured to request a twin"
    )
    def test_request_and_response_op(self, mocker, stage, op):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.RequestAndResponseOperation)
        assert new_op.request_type == "twin"
        assert new_op.method == "GET"
        assert new_op.resource_location == "/"
        assert new_op.request_body == " "


@pytest.mark.describe(
    "TwinRequestResponseStage - .run_op() -- Called with PatchTwinReportedPropertiesOperation"
)
class TestTwinRequestResponseStageRunOpWithPatchTwinReportedPropertiesOperation(
    StageRunOpTestBase, TwinRequestResponseStageTestConfig
):
    @pytest.fixture(params=["Dictionary Patch", "String Patch", "Integer Patch", "None Patch"])
    def json_patch(self, request):
        if request.param == "Dictionary Patch":
            return {"json_key": "json_val"}
        elif request.param == "String Patch":
            return "some_json"
        elif request.param == "Integer Patch":
            return 1234
        elif request.param == "None Patch":
            return None

    @pytest.fixture
    def op(self, mocker, json_patch):
        return pipeline_ops_iothub.PatchTwinReportedPropertiesOperation(
            patch=json_patch, callback=mocker.MagicMock()
        )

    @pytest.mark.it(
        "Sends a new RequestAndResponseOperation down the pipeline, configured to send a twin reported properties patch, with the patch serialized as a JSON string"
    )
    def test_request_and_response_op(self, mocker, stage, op):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.RequestAndResponseOperation)
        assert new_op.request_type == "twin"
        assert new_op.method == "PATCH"
        assert new_op.resource_location == "/properties/reported/"
        assert new_op.request_body == json.dumps(op.patch)


@pytest.mark.describe(
    "TwinRequestResponseStage - .run_op() -- Called with other arbitrary operation"
)
class TestTwinRequestResponseStageRunOpWithArbitraryOperation(
    StageRunOpTestBase, TwinRequestResponseStageTestConfig
):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down the pipeline")
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


# TODO: Provide a more accurate set of status codes for tests
@pytest.mark.describe(
    "TwinRequestResponseStage - OCCURRENCE: RequestAndResponseOperation created from GetTwinOperation is completed"
)
class TestTwinRequestResponseStageWhenRequestAndResponseCreatedFromGetTwinOperationCompleted(
    TwinRequestResponseStageTestConfig
):
    @pytest.fixture
    def get_twin_op(self, mocker):
        return pipeline_ops_iothub.GetTwinOperation(callback=mocker.MagicMock())

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs, get_twin_op):
        stage = cls_type(**init_kwargs)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")

        # Run the GetTwinOperation
        stage.run_op(get_twin_op)

        return stage

    @pytest.fixture
    def request_and_response_op(self, stage):
        assert stage.send_op_down.call_count == 1
        op = stage.send_op_down.call_args[0][0]
        assert isinstance(op, pipeline_ops_base.RequestAndResponseOperation)

        # reset the stage mock for convenience
        stage.send_op_down.reset_mock()

        return op

    @pytest.mark.it(
        "Completes the GetTwinOperation unsuccessfully, with the error from the RequestAndResponseOperation, if the RequestAndResponseOperation is completed unsuccessfully"
    )
    @pytest.mark.parametrize(
        "has_response_body", [True, False], ids=["With Response Body", "No Response Body"]
    )
    @pytest.mark.parametrize(
        "status_code",
        [
            pytest.param(None, id="Status Code: None"),
            pytest.param(200, id="Status Code: 200"),
            pytest.param(300, id="Status Code: 300"),
            pytest.param(400, id="Status Code: 400"),
            pytest.param(500, id="Status Code: 500"),
        ],
    )
    def test_request_and_response_op_completed_with_err(
        self,
        stage,
        get_twin_op,
        request_and_response_op,
        arbitrary_exception,
        status_code,
        has_response_body,
    ):
        assert not get_twin_op.completed
        assert not request_and_response_op.completed

        # NOTE: It shouldn't happen that an operation completed with error has a status code or a
        # response body, but it IS possible.
        request_and_response_op.status_code = status_code
        if has_response_body:
            request_and_response_op.response_body = b'{"key": "value"}'
        request_and_response_op.complete(error=arbitrary_exception)

        assert request_and_response_op.completed
        assert request_and_response_op.error is arbitrary_exception
        assert get_twin_op.completed
        assert get_twin_op.error is arbitrary_exception
        # Twin is NOT returned
        assert get_twin_op.twin is None

    @pytest.mark.it(
        "Completes the GetTwinOperation unsuccessfully with a ServiceError if the RequestAndResponseOperation is completed successfully with a status code indicating an unsuccessful result from the service"
    )
    @pytest.mark.parametrize(
        "has_response_body", [True, False], ids=["With Response Body", "No Response Body"]
    )
    @pytest.mark.parametrize(
        "status_code",
        [
            pytest.param(300, id="Status Code: 300"),
            pytest.param(400, id="Status Code: 400"),
            pytest.param(500, id="Status Code: 500"),
        ],
    )
    def test_request_and_response_op_completed_success_with_bad_code(
        self, stage, get_twin_op, request_and_response_op, status_code, has_response_body
    ):
        assert not get_twin_op.completed
        assert not request_and_response_op.completed

        request_and_response_op.status_code = status_code
        if has_response_body:
            request_and_response_op.response_body = b'{"key": "value"}'
        request_and_response_op.complete()

        assert request_and_response_op.completed
        assert request_and_response_op.error is None
        assert get_twin_op.completed
        assert isinstance(get_twin_op.error, ServiceError)
        # Twin is NOT returned
        assert get_twin_op.twin is None

    @pytest.mark.it(
        "Completes the GetTwinOperation successfully (with the JSON deserialized response body from the RequestAndResponseOperation as the twin) if the RequestAndResponseOperation is completed successfully with a status code indicating a successful result from the service"
    )
    @pytest.mark.parametrize(
        "response_body, expected_twin",
        [
            pytest.param(b'{"key": "value"}', {"key": "value"}, id="Twin 1"),
            pytest.param(b'{"key1": {"key2": "value"}}', {"key1": {"key2": "value"}}, id="Twin 2"),
            pytest.param(
                b'{"key1": {"key2": {"key3": "value1", "key4": "value2"}, "key5": "value3"}, "key6": {"key7": "value4"}, "key8": "value5"}',
                {
                    "key1": {"key2": {"key3": "value1", "key4": "value2"}, "key5": "value3"},
                    "key6": {"key7": "value4"},
                    "key8": "value5",
                },
                id="Twin 3",
            ),
        ],
    )
    def test_request_and_response_op_completed_success_with_good_code(
        self, stage, get_twin_op, request_and_response_op, response_body, expected_twin
    ):
        assert not get_twin_op.completed
        assert not request_and_response_op.completed

        request_and_response_op.status_code = 200
        request_and_response_op.response_body = response_body
        request_and_response_op.complete()

        assert request_and_response_op.completed
        assert request_and_response_op.error is None
        assert get_twin_op.completed
        assert get_twin_op.error is None
        assert get_twin_op.twin == expected_twin


@pytest.mark.describe(
    "TwinRequestResponseStage - OCCURRENCE: RequestAndResponseOperation created from PatchTwinReportedPropertiesOperation is completed"
)
class TestTwinRequestResponseStageWhenRequestAndResponseCreatedFromPatchTwinReportedPropertiesOperation(
    TwinRequestResponseStageTestConfig
):
    @pytest.fixture
    def patch_twin_reported_properties_op(self, mocker):
        return pipeline_ops_iothub.PatchTwinReportedPropertiesOperation(
            patch={"json_key": "json_val"}, callback=mocker.MagicMock()
        )

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs, patch_twin_reported_properties_op):
        stage = cls_type(**init_kwargs)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")

        # Run the GetTwinOperation
        stage.run_op(patch_twin_reported_properties_op)

        return stage

    @pytest.fixture
    def request_and_response_op(self, stage):
        assert stage.send_op_down.call_count == 1
        op = stage.send_op_down.call_args[0][0]
        assert isinstance(op, pipeline_ops_base.RequestAndResponseOperation)

        # reset the stage mock for convenience
        stage.send_op_down.reset_mock()

        return op

    @pytest.mark.it(
        "Completes the PatchTwinReportedPropertiesOperation unsuccessfully, with the error from the RequestAndResponseOperation, if the RequestAndResponseOperation is completed unsuccessfully"
    )
    @pytest.mark.parametrize(
        "status_code",
        [
            pytest.param(None, id="Status Code: None"),
            pytest.param(200, id="Status Code: 200"),
            pytest.param(300, id="Status Code: 300"),
            pytest.param(400, id="Status Code: 400"),
            pytest.param(500, id="Status Code: 500"),
        ],
    )
    def test_request_and_response_op_completed_with_err(
        self,
        stage,
        patch_twin_reported_properties_op,
        request_and_response_op,
        arbitrary_exception,
        status_code,
    ):
        assert not patch_twin_reported_properties_op.completed
        assert not request_and_response_op.completed

        # NOTE: It shouldn't happen that an operation completed with error has a status code
        # but it IS possible
        request_and_response_op.status_code = status_code
        request_and_response_op.complete(error=arbitrary_exception)

        assert request_and_response_op.completed
        assert request_and_response_op.error is arbitrary_exception
        assert patch_twin_reported_properties_op.completed
        assert patch_twin_reported_properties_op.error is arbitrary_exception

    @pytest.mark.it(
        "Completes the PatchTwinReportedPropertiesOperation unsuccessfully with a ServiceError if the RequestAndResponseOperation is completed successfully with a status code indicating an unsuccessful result from the service"
    )
    @pytest.mark.parametrize(
        "status_code",
        [
            pytest.param(300, id="Status Code: 300"),
            pytest.param(400, id="Status Code: 400"),
            pytest.param(500, id="Status Code: 500"),
        ],
    )
    def test_request_and_response_op_completed_success_with_bad_code(
        self, stage, patch_twin_reported_properties_op, request_and_response_op, status_code
    ):
        assert not patch_twin_reported_properties_op.completed
        assert not request_and_response_op.completed

        request_and_response_op.status_code = status_code
        request_and_response_op.complete()

        assert request_and_response_op.completed
        assert request_and_response_op.error is None
        assert patch_twin_reported_properties_op.completed
        assert isinstance(patch_twin_reported_properties_op.error, ServiceError)

    @pytest.mark.it(
        "Completes the PatchTwinReportedPropertiesOperation successfully if the RequestAndResponseOperation is completed successfully with a status code indicating a successful result from the service"
    )
    def test_request_and_response_op_completed_success_with_good_code(
        self, stage, patch_twin_reported_properties_op, request_and_response_op
    ):
        assert not patch_twin_reported_properties_op.completed
        assert not request_and_response_op.completed

        request_and_response_op.status_code = 200
        request_and_response_op.complete()

        assert request_and_response_op.completed
        assert request_and_response_op.error is None
        assert patch_twin_reported_properties_op.completed
        assert patch_twin_reported_properties_op.error is None
