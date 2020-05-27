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
        stage.pipeline_root.hostname = "some.fake-host.name.com"
        stage.send_op_down = mocker.MagicMock()
        return stage


class HTTPTransportInstantiationTests(HTTPTransportStageTestConfig):
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


@pytest.mark.describe("HTTPTransportStage - .run_op() -- Called with InitializePipelineOperation")
class TestHTTPTransportStageRunOpCalledWithInitializePipelineOperation(
    HTTPTransportStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        op = pipeline_ops_base.InitializePipelineOperation(callback=mocker.MagicMock())
        return op

    @pytest.mark.it(
        "Creates an HTTPTransport object and sets it as the 'transport' attribute of the stage (and on the pipeline root)"
    )
    @pytest.mark.parametrize(
        "cipher",
        [
            pytest.param("DHE-RSA-AES128-SHA", id="Pipeline configured for custom cipher"),
            pytest.param(
                "DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:ECDHE-ECDSA-AES128-GCM-SHA256",
                id="Pipeline configured for multiple custom ciphers",
            ),
            pytest.param("", id="Pipeline NOT configured for custom cipher(s)"),
        ],
    )
    @pytest.mark.parametrize(
        "gateway_hostname",
        [
            pytest.param("fake.gateway.hostname.com", id="Using Gateway Hostname"),
            pytest.param(None, id="Not using Gateway Hostname"),
        ],
    )
    def test_creates_transport(self, mocker, stage, op, mock_transport, cipher, gateway_hostname):
        # Setup pipeline config
        stage.pipeline_root.pipeline_configuration.cipher = cipher
        stage.pipeline_root.pipeline_configuration.gateway_hostname = gateway_hostname

        # NOTE: if more of this type of logic crops up, consider splitting this test up
        if stage.pipeline_root.pipeline_configuration.gateway_hostname:
            expected_hostname = stage.pipeline_root.pipeline_configuration.gateway_hostname
        else:
            expected_hostname = stage.pipeline_root.pipeline_configuration.hostname

        assert stage.transport is None

        stage.run_op(op)

        assert mock_transport.call_count == 1
        assert mock_transport.call_args == mocker.call(
            hostname=expected_hostname,
            server_verification_cert=stage.pipeline_root.pipeline_configuration.server_verification_cert,
            x509_cert=stage.pipeline_root.pipeline_configuration.x509,
            cipher=cipher,
        )
        assert stage.transport is mock_transport.return_value

    @pytest.mark.it("Completes the operation with success, upon successful execution")
    def test_succeeds(self, mocker, stage, op, mock_transport):
        assert not op.completed
        stage.run_op(op)
        assert op.completed


# NOTE: The HTTPTransport object is not instantiated upon instantiation of the HTTPTransportStage.
# It is only added once the InitializePipelineOperation runs.
# The lifecycle of the HTTPTransportStage is as follows:
#   1. Instantiate the stage
#   2. Configure the stage with an InitializePipelineOperation
#   3. Run any other desired operations.
#
# This is to say, no operation should be running before InitializePipelineOperation.
# Thus, for the following tests, we will assume that the HTTPTransport has already been created,
# and as such, the stage fixture used will have already have one.
class HTTPTransportStageTestConfigComplex(HTTPTransportStageTestConfig):
    @pytest.fixture
    def stage(self, mocker, request, cls_type, init_kwargs, mock_transport):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.send_op_down = mocker.MagicMock()

        # Set up the Transport on the stage
        op = pipeline_ops_base.InitializePipelineOperation(callback=mocker.MagicMock())
        stage.run_op(op)

        assert stage.transport is mock_transport.return_value

        return stage


@pytest.mark.describe(
    "HTTPTransportStage - .run_op() -- Called with HTTPRequestAndResponseOperation"
)
class TestHTTPTransportStageRunOpCalledWithHTTPRequestAndResponseOperation(
    HTTPTransportStageTestConfigComplex, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_http.HTTPRequestAndResponseOperation(
            method="SOME_METHOD",
            path="fake/path",
            headers={"fake_key": "fake_val"},
            body="fake_body",
            query_params="arg1=val1;arg2=val2",
            callback=mocker.MagicMock(),
        )

    @pytest.mark.it("Sends an HTTP request via the HTTPTransport")
    def test_http_request(self, mocker, stage, op):
        stage.run_op(op)

        assert stage.transport.request.call_count == 1
        assert stage.transport.request.call_args == mocker.call(
            method=op.method,
            path=op.path,
            # headers are tested in depth in the following two tests
            headers=mocker.ANY,
            body=op.body,
            query_params=op.query_params,
            callback=mocker.ANY,
        )

    @pytest.mark.it(
        "Adds the SasToken in the request's 'Authorization' header if using SAS-based authentication"
    )
    def test_headers_with_sas_auth(self, mocker, stage, op):
        # A SasToken is set on the pipeline, but Authorization headers have not yet been set
        assert stage.pipeline_root.pipeline_configuration.sastoken is not None
        assert op.headers.get("Authorization") is None

        stage.run_op(op)

        # Need to get the headers sent to the transport, not provided by the op, due to a
        # deep copy that occurs
        headers = stage.transport.request.call_args[1]["headers"]
        assert headers["Authorization"] == str(stage.pipeline_root.pipeline_configuration.sastoken)

    @pytest.mark.it(
        "Does NOT add the 'Authorization' header to the request if NOT using SAS-based authentication"
    )
    def test_headers_with_no_sas(self, mocker, stage, op):
        # NO SasToken is set on the pipeline, and Authorization headers have not yet been set
        stage.pipeline_root.pipeline_configuration.sastoken = None
        assert op.headers.get("Authorization") is None

        stage.run_op(op)

        # Need to get the headers sent to the transport, not provided by the op, due to a
        # deep copy that occurs
        headers = stage.transport.request.call_args[1]["headers"]
        assert headers.get("Authorization") is None

    @pytest.mark.it(
        "Completes the operation unsucessfully if there is a failure requesting via the HTTPTransport, using the error raised by the HTTPTransport"
    )
    def test_fails_operation(self, mocker, stage, op, arbitrary_exception):
        stage.transport.request.side_effect = arbitrary_exception
        stage.run_op(op)
        assert op.completed
        assert op.error is arbitrary_exception

    @pytest.mark.it(
        "Completes the operation successfully if the request invokes the provided callback without an error"
    )
    def test_completes_callback(self, mocker, stage, op):
        def mock_request_callback(method, path, headers, query_params, body, callback):
            fake_response = {
                "resp": "__fake_response__".encode("utf-8"),
                "status_code": "__fake_status_code__",
                "reason": "__fake_reason__",
            }
            return callback(response=fake_response)

        # This is a way for us to mock the transport invoking the callback
        stage.transport.request.side_effect = mock_request_callback
        stage.run_op(op)
        assert op.completed

    @pytest.mark.it(
        "Adds a reason, status code, and response body to the op if request invokes the provided callback without an error"
    )
    def test_formats_op_on_complete(self, mocker, stage, op):
        def mock_request_callback(method, path, headers, query_params, body, callback):
            fake_response = {
                "resp": "__fake_response__".encode("utf-8"),
                "status_code": "__fake_status_code__",
                "reason": "__fake_reason__",
            }
            return callback(response=fake_response)

        # This is a way for us to mock the transport invoking the callback
        stage.transport.request.side_effect = mock_request_callback
        stage.run_op(op)
        assert op.reason == "__fake_reason__"
        assert op.response_body == "__fake_response__".encode("utf-8")
        assert op.status_code == "__fake_status_code__"

    @pytest.mark.it(
        "Completes the operation with an error if the request invokes the provided callback with the same error"
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
