# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import sys
import six
from azure.iot.device.common import transport_exceptions, handle_exceptions
from azure.iot.device.common.pipeline import (
    pipeline_ops_base,
    pipeline_stages_base,
    pipeline_ops_http,
    pipeline_stages_http,
    pipeline_exceptions,
    config,
)
from tests.common.pipeline.helpers import StageRunOpTestBase
from tests.common.pipeline import pipeline_stage_test


this_module = sys.modules[__name__]
logging.basicConfig(level=logging.DEBUG)
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")

###################
# COMMON FIXTURES #
###################


@pytest.fixture
def mock_transport(mocker):
    return mocker.patch(
        "azure.iot.device.common.pipeline.pipeline_stages_http.HTTPTransport", autospec=True
    )


# Not a fixture, but used in parametrization
def fake_callback():
    pass


########################
# HTTP TRANSPORT STAGE #
########################


class HTTPTransportStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_http.HTTPTransportStage

    @pytest.fixture
    def init_kwargs(self, mocker):
        return {}

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.send_op_down = mocker.MagicMock()
        return stage


class HTTPTransportInstantiationTests(HTTPTransportStageTestConfig):
    @pytest.mark.it("Initializes 'sas_token' attribute as None")
    def test_sas_token(self, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        assert stage.sas_token is None

    @pytest.mark.it("Initializes 'transport' attribute as None")
    def test_transport(self, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        assert stage.transport is None


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_http.HTTPTransportStage,
    stage_test_config_class=HTTPTransportStageTestConfig,
    extended_stage_instantiation_test_class=HTTPTransportInstantiationTests,
)


@pytest.mark.describe(
    "HTTPTransportStage - .run_op() -- Called with SetHTTPConnectionArgsOperation"
)
class TestHTTPTransportStageRunOpCalledWithSetHTTPConnectionArgsOperation(
    HTTPTransportStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_http.SetHTTPConnectionArgsOperation(
            hostname="fake_hostname",
            ca_cert="fake_ca_cert",
            client_cert="fake_client_cert",
            sas_token="fake_sas_token",
            callback=mocker.MagicMock(),
        )

    @pytest.mark.it("Stores the sas_token operation in the 'sas_token' attribute of the stage")
    def test_stores_data(self, stage, op, mocker, mock_transport):
        stage.run_op(op)
        assert stage.sas_token == op.sas_token

    # TODO: Should probably remove the requirement to set it on the root. This seems only needed by Horton
    @pytest.mark.it(
        "Creates an HTTPTransport object and sets it as the 'transport' attribute of the stage (and on the pipeline root)"
    )
    def test_creates_transport(self, mocker, stage, op, mock_transport):
        assert stage.transport is None
        assert not hasattr(stage.pipeline_root, "transport")

        stage.run_op(op)

        assert mock_transport.call_count == 1
        assert mock_transport.call_args == mocker.call(
            hostname=op.hostname, ca_cert=op.ca_cert, x509_cert=op.client_cert
        )
        assert stage.transport is mock_transport.return_value
        assert stage.pipeline_root.transport is mock_transport.return_value

    @pytest.mark.it("Completes the operation with success, upon successful execution")
    def test_succeeds(self, mocker, stage, op, mock_transport):
        assert not op.completed
        stage.run_op(op)
        assert op.completed


# NOTE: The HTTPTransport object is not instantiated upon instantiation of the HTTPTransportStage.
# It is only added once the SetHTTPConnectionArgsOperation runs.
# The lifecycle of the HTTPTransportStage is as follows:
#   1. Instantiate the stage
#   2. Configure the stage with a SetHTTPConnectionArgsOperation
#   3. Run any other desired operations.
#
# This is to say, no operation should be running before SetHTTPConnectionArgsOperation.
# Thus, for the following tests, we will assume that the HTTPTransport has already been created,
# and as such, the stage fixture used will have already have one.
class HTTPTransportStageTestConfigComplex(HTTPTransportStageTestConfig):
    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        mock_transport = mocker.patch(
            "azure.iot.device.common.pipeline.pipeline_stages_http.HTTPTransport", autospec=True
        )
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.send_op_down = mocker.MagicMock()

        # Set up the Transport on the stage
        op = pipeline_ops_http.SetHTTPConnectionArgsOperation(
            hostname="fake_hostname",
            ca_cert="fake_ca_cert",
            client_cert="fake_client_cert",
            sas_token="fake_sas_token",
            callback=mocker.MagicMock(),
        )
        stage.run_op(op)
        assert stage.transport is mock_transport.return_value

        return stage


@pytest.mark.describe("HTTPTransportStage - .run_op() -- Called with UpdateSasTokenOperation")
class TestHTTPTransportStageRunOpCalledWithUpdateSasTokenOperation(
    HTTPTransportStageTestConfigComplex, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.UpdateSasTokenOperation(
            sas_token="new_fake_sas_token", callback=mocker.MagicMock()
        )

    @pytest.mark.it(
        "Updates the 'sas_token' attribute to be the new value contained in the operation"
    )
    def test_updates_token(self, stage, op):
        assert stage.sas_token != op.sas_token
        stage.run_op(op)
        assert stage.sas_token == op.sas_token

    @pytest.mark.it("Completes the operation with success, upon successful execution")
    def test_complets_op(self, stage, op):
        assert not op.completed
        stage.run_op(op)
        assert op.completed


fake_method = "__fake_method__"
fake_path = "__fake_path__"
fake_headers = {"__fake_key__": "__fake_value__"}
fake_body = "__fake_body__"
fake_query_params = "__fake_query_params__"


@pytest.mark.describe(
    "HTTPTransportStage - .run_op() -- Called with HTTPRequestAndResponseOperation"
)
class TestHTTPTransportStageRunOpCalledWithHTTPRequestAndResponseOperation(
    HTTPTransportStageTestConfigComplex, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_http.HTTPRequestAndResponseOperation(
            method=fake_method,
            path=fake_path,
            headers=fake_headers,
            body=fake_body,
            query_params=fake_query_params,
            callback=mocker.MagicMock(),
        )

    @pytest.mark.it("Performs an HTTP connect via the HTTPTransport")
    def test_http_request(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.transport.request.call_count == 1
        assert stage.transport.request.call_args == mocker.call(
            method=fake_method,
            path=fake_path,
            headers=fake_headers,
            body=fake_body,
            query_params=fake_query_params,
            callback=mocker.ANY,
        )

    @pytest.mark.it(
        "Completes the operation unsucessfully if there is a failure requesting via the HTTPTransport, using the error raised by the HTTPTransport"
    )
    def test_fails_operation(self, mocker, stage, op, arbitrary_exception):
        stage.transport.request.side_effect = arbitrary_exception
        stage.run_op(op)
        assert op.completed
        assert op.error is arbitrary_exception

    # YMTODO: Ask Carter how I make this work with the callback in the stage.
    @pytest.mark.it(
        "Completes the operation successfully if the request invokes the provided callback without an error"
    )
    def test_completes_callback(self, mocker, stage, op):
        def mock_on_response_complete(method, path, headers, query_params, body, callback):
            fake_response = {
                "resp": "__fake_response__",
                "status_code": "__fake_status_code__",
                "reason": "__fake_reason__",
            }
            return callback(response=fake_response)

        stage.transport.request.side_effect = mock_on_response_complete
        stage.run_op(op)
        assert op.completed

    @pytest.mark.it(
        "Completes the operation with an error if the request invokes the provided callback with an error"
    )
    def test_completes_callback_with_error(self, mocker, stage, op, arbitrary_exception):
        def mock_on_response_complete(method, path, headers, query_params, body, callback):
            return callback(error=arbitrary_exception)

        stage.transport.request.side_effect = mock_on_response_complete
        stage.run_op(op)
        assert op.completed
        assert op.error is arbitrary_exception


# NOTE: This is not something that should ever happen in correct program flow
# There should be no operations that make it to the HTTPTransportStage that are not handled by it
@pytest.mark.describe("HTTPTransportStage - .run_op() -- called with arbitrary other operation")
class TestHTTPTransportStageRunOpCalledWithArbitraryOperation(
    HTTPTransportStageTestConfigComplex, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down")
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)
