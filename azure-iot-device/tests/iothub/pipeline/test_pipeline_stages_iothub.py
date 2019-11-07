# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import functools
import json
import logging
import pytest
import sys
import threading
from concurrent.futures import Future
from azure.iot.device.exceptions import ServiceError
from azure.iot.device.common import handle_exceptions
from azure.iot.device.common.pipeline import pipeline_ops_base
from azure.iot.device.iothub.pipeline import pipeline_stages_iothub, pipeline_ops_iothub
from azure.iot.device.iothub.pipeline.exceptions import PipelineError
from tests.common.pipeline.helpers import (
    assert_callback_succeeded,
    assert_callback_failed,
    all_common_ops,
    all_common_events,
    all_except,
    StageTestBase,
)
from tests.iothub.pipeline.helpers import all_iothub_ops, all_iothub_events
from tests.common.pipeline import pipeline_stage_test
from azure.iot.device.common.models.x509 import X509
from azure.iot.device.iothub.auth.x509_authentication_provider import X509AuthenticationProvider

logging.basicConfig(level=logging.DEBUG)

this_module = sys.modules[__name__]


# This fixture makes it look like all test in this file  tests are running
# inside the pipeline thread.  Because this is an autouse fixture, we
# manually add it to the individual test.py files that need it.  If,
# instead, we had added it to some conftest.py, it would be applied to
# every tests in every file and we don't want that.
@pytest.fixture(autouse=True)
def apply_fake_pipeline_thread(fake_pipeline_thread):
    pass


fake_device_id = "__fake_device_id__"
fake_module_id = "__fake_module_id__"
fake_hostname = "__fake_hostname__"
fake_gateway_hostname = "__fake_gateway_hostname__"
fake_ca_cert = "__fake_ca_cert__"
fake_sas_token = "__fake_sas_token__"
fake_symmetric_key = "Zm9vYmFy"
fake_x509_cert_file = "fantastic_beasts"
fake_x509_cert_key_file = "where_to_find_them"
fake_pass_phrase = "alohomora"


pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_iothub.UseAuthProviderStage,
    module=this_module,
    all_ops=all_common_ops + all_iothub_ops,
    handled_ops=[
        pipeline_ops_iothub.SetAuthProviderOperation,
        pipeline_ops_iothub.SetX509AuthProviderOperation,
    ],
    all_events=all_common_events + all_iothub_events,
    handled_events=[],
    methods_that_enter_pipeline_thread=["on_sas_token_updated"],
)


def make_mock_sas_token_auth_provider():
    class MockAuthProvider(object):
        def get_current_sas_token(self):
            return fake_sas_token

    auth_provider = MockAuthProvider()
    auth_provider.device_id = fake_device_id
    auth_provider.hostname = fake_hostname
    return auth_provider


def make_x509_auth_provider_device():
    mock_x509 = X509(fake_x509_cert_file, fake_x509_cert_key_file, fake_pass_phrase)
    return X509AuthenticationProvider(
        hostname=fake_hostname, device_id=fake_device_id, x509=mock_x509
    )


def make_x509_auth_provider_module():
    mock_x509 = X509(fake_x509_cert_file, fake_x509_cert_key_file, fake_pass_phrase)
    return X509AuthenticationProvider(
        x509=mock_x509, hostname=fake_hostname, device_id=fake_device_id, module_id=fake_module_id
    )


different_auth_provider_ops = [
    {
        "name": "sas_token_auth",
        "current_op_class": pipeline_ops_iothub.SetAuthProviderOperation,
        "auth_provider_function_name": make_mock_sas_token_auth_provider,
    },
    {
        "name": "x509_auth_device",
        "current_op_class": pipeline_ops_iothub.SetX509AuthProviderOperation,
        "auth_provider_function_name": make_x509_auth_provider_device,
    },
    {
        "name": "x509_auth_module",
        "current_op_class": pipeline_ops_iothub.SetX509AuthProviderOperation,
        "auth_provider_function_name": make_x509_auth_provider_module,
    },
]


@pytest.mark.parametrize(
    "params_auth_provider_ops",
    different_auth_provider_ops,
    ids=[x["current_op_class"].__name__ for x in different_auth_provider_ops],
)
@pytest.mark.describe("UseAuthProvider - .run_op() -- called with SetAuthProviderOperation")
class TestUseAuthProviderRunOpWithSetAuthProviderOperation(StageTestBase):
    @pytest.fixture
    def stage(self, mocker):
        stage = pipeline_stages_iothub.UseAuthProviderStage()
        mocker.spy(stage, "send_worker_op_down")
        return stage

    @pytest.fixture
    def set_auth_provider(self, params_auth_provider_ops, mocker):
        op = params_auth_provider_ops["current_op_class"](
            auth_provider=params_auth_provider_ops["auth_provider_function_name"](),
            callback=mocker.MagicMock(),
        )
        mocker.spy(op, "complete")
        return op

    @pytest.fixture
    def set_auth_provider_all_args(self, params_auth_provider_ops, mocker):
        auth_provider = params_auth_provider_ops["auth_provider_function_name"]()
        auth_provider.module_id = fake_module_id

        if not isinstance(auth_provider, X509AuthenticationProvider):
            auth_provider.ca_cert = fake_ca_cert
            auth_provider.gateway_hostname = fake_gateway_hostname
            auth_provider.sas_token = fake_sas_token
        op = params_auth_provider_ops["current_op_class"](
            auth_provider=auth_provider, callback=mocker.MagicMock()
        )
        mocker.spy(op, "complete")
        return op

    @pytest.mark.it("Runs a SetIoTHubConnectionArgsOperation worker op on the next stage")
    def test_runs_set_auth_provider_args(self, mocker, stage, set_auth_provider):
        stage.next._execute_op = mocker.Mock()
        stage.run_op(set_auth_provider)

        assert stage.send_worker_op_down.call_count == 1
        assert isinstance(
            stage.send_worker_op_down.call_args[1]["worker_op"],
            pipeline_ops_iothub.SetIoTHubConnectionArgsOperation,
        )
        assert stage.send_worker_op_down.call_args[1]["op"] is set_auth_provider

    @pytest.mark.it(
        "Sets the device_id, and hostname attributes on SetIoTHubConnectionArgsOperation based on the same-names auth_provider attributes"
    )
    def test_sets_required_attributes(self, mocker, stage, set_auth_provider):
        stage.next._execute_op = mocker.Mock()
        stage.run_op(set_auth_provider)
        set_args = stage.next._execute_op.call_args[0][0]
        assert set_args.device_id == fake_device_id
        assert set_args.hostname == fake_hostname

    @pytest.mark.it(
        "Sets the gateway_hostname, ca_cert, and module_id attributes to None if they don't exist on the auth_provider object"
    )
    def test_defaults_optional_attributes_to_none(
        self, mocker, stage, set_auth_provider, params_auth_provider_ops
    ):
        stage.next._execute_op = mocker.Mock()
        stage.run_op(set_auth_provider)
        set_args = stage.next._execute_op.call_args[0][0]
        assert set_args.gateway_hostname is None
        assert set_args.ca_cert is None
        if params_auth_provider_ops["name"] == "x509_auth_module":
            assert set_args.module_id is not None
        else:
            assert set_args.module_id is None

    @pytest.mark.it(
        "Sets the module_id, gateway_hostname, sas_token, and ca_cert attributes on SetIoTHubConnectionArgsOperation if they exist on the auth_provider object"
    )
    def test_sets_optional_attributes(
        self, mocker, stage, set_auth_provider_all_args, params_auth_provider_ops
    ):
        stage.next._execute_op = mocker.Mock()
        stage.run_op(set_auth_provider_all_args)
        set_args = stage.next._execute_op.call_args[0][0]
        assert set_args.module_id == fake_module_id

        if params_auth_provider_ops["name"] == "sas_token_auth":
            assert set_args.gateway_hostname == fake_gateway_hostname
            assert set_args.ca_cert == fake_ca_cert
            assert set_args.sas_token == fake_sas_token

    @pytest.mark.it(
        "Retrieves sas_token or x509_certificate on the auth provider and passes the result as the attribute of the next operation"
    )
    def test_calls_get_current_sas_token_or_get_x509_certificate(
        self, mocker, stage, set_auth_provider, params_auth_provider_ops
    ):

        if params_auth_provider_ops["name"] == "sas_token_auth":
            spy_method = mocker.spy(set_auth_provider.auth_provider, "get_current_sas_token")
        elif "x509_auth" in params_auth_provider_ops["name"]:
            spy_method = mocker.spy(set_auth_provider.auth_provider, "get_x509_certificate")

        stage.run_op(set_auth_provider)
        assert spy_method.call_count == 1
        set_connection_args_op = stage.next._execute_op.call_args_list[0][0][0]

        if params_auth_provider_ops["name"] == "sas_token_auth":
            assert set_connection_args_op.sas_token == fake_sas_token
        elif "x509_auth" in params_auth_provider_ops["name"]:
            assert set_connection_args_op.client_cert.certificate_file == fake_x509_cert_file
            assert set_connection_args_op.client_cert.key_file == fake_x509_cert_key_file
            assert set_connection_args_op.client_cert.pass_phrase == fake_pass_phrase

    @pytest.mark.it("Sets the on_sas_token_updated_handler handler")
    def test_sets_sas_token_updated_handler(
        self, mocker, stage, set_auth_provider_all_args, params_auth_provider_ops
    ):
        if params_auth_provider_ops["name"] != "sas_token_auth":
            pytest.mark.skip()
        else:
            stage.next._execute_op = mocker.Mock()
            stage.run_op(set_auth_provider_all_args)
            assert (
                set_auth_provider_all_args.auth_provider.on_sas_token_updated_handler
                == stage.on_sas_token_updated
            )


@pytest.mark.describe("UseAuthProvider - .on_sas_token_updated()")
class TestUseAuthProviderOnSasTokenUpdated(StageTestBase):
    @pytest.fixture
    def stage(self, mocker):
        stage = pipeline_stages_iothub.UseAuthProviderStage()

        auth_provider = mocker.MagicMock()
        auth_provider.get_current_sas_token = mocker.MagicMock(return_value=fake_sas_token)
        stage.auth_provider = auth_provider
        return stage

    @pytest.mark.it("Runs as a non-blocking function on the pipeline thread")
    def test_runs_non_blocking(self, stage):
        threading.current_thread().name = "not_pipeline"
        return_value = stage.on_sas_token_updated()
        assert isinstance(return_value, Future)

    @pytest.mark.it(
        "Runs a UpdateSasTokenOperation on the next stage with the sas token from self.auth_provider"
    )
    def test_update_sas_token_operation(self, stage):
        stage.on_sas_token_updated()
        assert stage.next.run_op.call_count == 1
        assert isinstance(
            stage.next.run_op.call_args[0][0], pipeline_ops_base.UpdateSasTokenOperation
        )

    @pytest.mark.it(
        "Handles any Exceptions raised by the UpdateSasTokenOperation and passes them into the unhandled exception handler"
    )
    def test_raises_exception(self, stage, mocker, unhandled_error_handler, arbitrary_exception):
        threading.current_thread().name = "not_pipeline"

        stage.next.run_op = mocker.MagicMock(side_effect=arbitrary_exception)
        future = stage.on_sas_token_updated()
        future.result()

        assert unhandled_error_handler.call_count == 1
        assert unhandled_error_handler.call_args[0][0] is arbitrary_exception

    @pytest.mark.it("Allows any BaseExceptions raised by the UpdateSasTokenOperation to propagate")
    def test_raises_base_exception(self, mocker, stage, arbitrary_base_exception):
        threading.current_thread().name = "not_pipeline"

        stage.next.run_op = mocker.MagicMock(side_effect=arbitrary_base_exception)
        future = stage.on_sas_token_updated()

        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            future.result()
        assert e_info.value is arbitrary_base_exception


pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_iothub.TwinRequestResponseStage,
    module=this_module,
    all_ops=all_common_ops + all_iothub_ops,
    handled_ops=[
        pipeline_ops_iothub.GetTwinOperation,
        pipeline_ops_iothub.PatchTwinReportedPropertiesOperation,
    ],
    all_events=all_common_events + all_iothub_events,
    handled_events=[],
)


@pytest.mark.describe("TwinRequestResponseStage - .run_op() -- called with GetTwinOperation")
class TestHandleTwinOperationsRunOpWithGetTwin(StageTestBase):
    @pytest.fixture
    def stage(self):
        return pipeline_stages_iothub.TwinRequestResponseStage()

    @pytest.fixture
    def op(self, stage, mocker):
        op = pipeline_ops_iothub.GetTwinOperation(callback=mocker.MagicMock())
        mocker.spy(op, "complete")
        return op

    @pytest.fixture
    def twin(self):
        return {"Am I a twin": "You bet I am"}

    @pytest.fixture
    def twin_as_bytes(self, twin):
        return json.dumps(twin).encode("utf-8")

    @pytest.mark.it(
        "Runs a RequestAndResponseOperation operation on the next stage with request_type='twin', method='GET', resource_location='/', and request_body=' '"
    )
    def test_sends_new_operation(self, stage, op):
        stage.run_op(op)
        assert stage.next.run_op.call_count == 1
        new_op = stage.next.run_op.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.RequestAndResponseOperation)
        assert new_op.request_type == "twin"
        assert new_op.method == "GET"
        assert new_op.resource_location == "/"
        assert new_op.request_body == " "

    @pytest.mark.it(
        "Completes the GetTwinOperation with the failure from RequestAndResponseOperation, if the RequestAndResponseOperation completes with failure"
    )
    def test_next_stage_returns_error(self, mocker, stage, op, arbitrary_exception):
        def next_stage_run_op(self, next_stage_op):
            next_stage_op.complete(error=arbitrary_exception)

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert op.complete.call_args == mocker.call(error=arbitrary_exception)

    @pytest.mark.it(
        "Completes the GetTwinOperation with a ServiceError if the RequestAndResponseOperation returns a status code >= 300"
    )
    def test_next_stage_returns_status_over_300(self, mocker, stage, op):
        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 400
            # TODO: should this have a body? Should with/without be a separate test?
            next_stage_op.response_body = json.dumps("").encode("utf-8")
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert type(op.complete.call_args[1]["error"]) is ServiceError

    @pytest.mark.it(
        "Decodes, deserializes, and returns the request_body from RequestAndResponseOperation as the twin attribute on the op along with no error if the status code < 300"
    )
    def test_next_stage_completes_correctly(self, mocker, stage, op, twin, twin_as_bytes):
        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 200
            next_stage_op.response_body = twin_as_bytes
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert op.complete.call_args == mocker.call(error=None)
        assert op.twin == twin


@pytest.mark.describe(
    "TwinRequestResponseStage - .run_op() -- called with PatchTwinReportedPropertiesOperation"
)
class TestHandleTwinOperationsRunOpWithPatchTwinReportedProperties(StageTestBase):
    @pytest.fixture
    def stage(self):
        return pipeline_stages_iothub.TwinRequestResponseStage()

    @pytest.fixture
    def patch(self):
        return {"__fake_patch__": "yes"}

    @pytest.fixture
    def patch_as_string(self, patch):
        return json.dumps(patch)

    @pytest.fixture
    def op(self, stage, mocker, patch):
        op = pipeline_ops_iothub.PatchTwinReportedPropertiesOperation(
            patch=patch, callback=mocker.MagicMock()
        )
        mocker.spy(op, "complete")
        return op

    @pytest.mark.it(
        "Runs a RequestAndResponseOperation operation on the next stage with request_type='twin', method='PATCH', resource_location='/properties/reported/', and the request_body attribute set to a stringification of the patch"
    )
    def test_sends_new_operation(self, stage, op, patch_as_string):
        stage.run_op(op)
        assert stage.next.run_op.call_count == 1
        new_op = stage.next.run_op.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.RequestAndResponseOperation)
        assert new_op.request_type == "twin"
        assert new_op.method == "PATCH"
        assert new_op.resource_location == "/properties/reported/"
        assert new_op.request_body == patch_as_string

    @pytest.mark.it(
        "Completes the PatchTwinReportedPropertiesOperation with the failure from RequestAndResponseOperation, if the RequestAndResponse operation completes with failure"
    )
    def test_next_stage_returns_error(self, mocker, stage, op, arbitrary_exception):
        def next_stage_run_op(self, next_stage_op):
            next_stage_op.complete(error=arbitrary_exception)

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert op.complete.call_args == mocker.call(error=arbitrary_exception)

    @pytest.mark.it(
        "Completes the PatchTwinReportedPropertiesOperation with a ServiceError, if the RequestAndResponseOperation returns a status code >= 300"
    )
    def test_next_stage_returns_status_over_300(self, stage, op):
        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 400
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert type(op.complete.call_args[1]["error"]) is ServiceError

    @pytest.mark.it(
        "Completes the PatchTwinReportedPropertiesOperation successfully if the status code < 300"
    )
    def test_next_stage_completes_correctly(self, mocker, stage, op):
        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 200
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert op.complete.call_args == mocker.call(error=None)
