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
from azure.iot.device.iothub.auth.authentication_provider import AuthenticationProvider
from tests.common.pipeline.helpers import StageRunOpTestBase, StageHandlePipelineEventTestBase
from tests.common.pipeline import pipeline_stage_test
from azure.iot.device.common.models.x509 import X509
from azure.iot.device.iothub.auth.x509_authentication_provider import X509AuthenticationProvider

logging.basicConfig(level=logging.DEBUG)
this_module = sys.modules[__name__]
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")


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
def mock_handle_background_exception(mocker):
    mock_handler = mocker.patch.object(handle_exceptions, "handle_background_exception")
    return mock_handler


###########################
# USE AUTH PROVIDER STAGE #
###########################


class UseAuthProviderStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_iothub.UseAuthProviderStage

    @pytest.fixture
    def init_kwargs(self):
        return {}

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        return stage


class UseAuthProviderStageInstantiationTests(UseAuthProviderStageTestConfig):
    @pytest.mark.it("Initializes 'auth_provider' as None")
    def test_auth_provider(self, init_kwargs):
        stage = pipeline_stages_iothub.UseAuthProviderStage(**init_kwargs)
        assert stage.auth_provider is None


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_iothub.UseAuthProviderStage,
    stage_test_config_class=UseAuthProviderStageTestConfig,
    extended_stage_instantiation_test_class=UseAuthProviderStageInstantiationTests,
)


@pytest.mark.describe(
    "UseAuthProviderStage - .run_op() -- Called with SetAuthProviderOperation (SAS Authentication)"
)
class TestUseAuthProviderStageRunOpWithSetAuthProviderOperation(
    StageRunOpTestBase, UseAuthProviderStageTestConfig
):
    # Auth Providers are configured with different values depending on if the higher level client
    # is a Device or Module. Parametrize with both possibilities.
    # TODO: Eventually would be ideal to test using real auth provider instead of the fake one
    # This probably should just wait until auth provider refactor for ease though.
    @pytest.fixture(params=["Device", "Module"])
    def fake_auth_provider(self, request, mocker):
        class FakeAuthProvider(AuthenticationProvider):
            pass

        if request.param == "Device":
            fake_auth_provider = FakeAuthProvider(hostname=fake_hostname, device_id=fake_device_id)
        else:
            fake_auth_provider = FakeAuthProvider(
                hostname=fake_hostname, device_id=fake_device_id, module_id=fake_module_id
            )
        fake_auth_provider.get_current_sas_token = mocker.MagicMock()
        return fake_auth_provider

    @pytest.fixture
    def op(self, mocker, fake_auth_provider):
        return pipeline_ops_iothub.SetAuthProviderOperation(
            auth_provider=fake_auth_provider, callback=mocker.MagicMock()
        )

    @pytest.mark.it(
        "Sets the operation's authentication provider on the stage as the 'auth_provider' attribute"
    )
    def test_set_auth_provider(self, op, stage):
        assert stage.auth_provider is None

        stage.run_op(op)

        assert stage.auth_provider is op.auth_provider

    # NOTE: Because currently auth providers don't have a consistent attribute surface, only some
    # have the 'ca_cert' and 'gateway_hostname' attributes, so parametrize to show they default to
    # None when non-existent. If authentication providers ever receive a uniform surface, this
    # parametrization will no longer be required.
    @pytest.mark.it(
        "Sends a new SetIoTHubConnectionArgsOperation op down the pipeline, containing connection info from the authentication provider"
    )
    @pytest.mark.parametrize(
        "all_auth_args", [True, False], ids=["All authentication args", "Only guaranteed args"]
    )
    def test_send_new_op_down(self, mocker, op, stage, all_auth_args):
        if all_auth_args:
            op.auth_provider.ca_cert = fake_ca_cert
            op.auth_provider.gateway_hostname = fake_gateway_hostname

        stage.run_op(op)

        # A SetIoTHubConnectionArgsOperation op has been sent down the pipeline
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_iothub.SetIoTHubConnectionArgsOperation)

        # The IoTHubConnectionArgsOperation has details from the auth provider
        assert new_op.device_id == op.auth_provider.device_id
        assert new_op.module_id == op.auth_provider.module_id
        assert new_op.hostname == op.auth_provider.hostname
        assert new_op.sas_token is op.auth_provider.get_current_sas_token.return_value
        assert new_op.client_cert is None
        if all_auth_args:
            assert new_op.ca_cert == op.auth_provider.ca_cert
            assert new_op.gateway_hostname == op.auth_provider.gateway_hostname
        else:
            assert new_op.ca_cert is None
            assert new_op.gateway_hostname is None

    @pytest.mark.it(
        "Completes the original operation upon completion of the SetIoTHubConnectionArgsOperation"
    )
    def test_complete_worker(self, op, stage, op_error):
        # Run original op
        stage.run_op(op)
        assert not op.completed

        # A SetIoTHubConnectionArgsOperation op has been sent down the pipeline
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_iothub.SetIoTHubConnectionArgsOperation)
        assert not new_op.completed

        # Complete the new op
        new_op.complete(error=op_error)

        # Both ops are now completed
        assert new_op.completed
        assert new_op.error is op_error
        assert op.completed
        assert op.error is op_error


@pytest.mark.describe(
    "UseAuthProviderStage - .run_op() -- Called with SetX509AuthProviderOperation"
)
class TestUseAuthProviderStageRunOpWithSetX509AuthProviderOperation(
    StageRunOpTestBase, UseAuthProviderStageTestConfig
):
    # Auth Providers are configured with different values depending on if the higher level client
    # is a Device or Module. Parametrize with both possibilities.
    # TODO: Eventually would be ideal to test using real auth provider instead of the fake one
    # This probably should just wait until auth provider refactor for ease though.
    @pytest.fixture(params=["Device", "Module"])
    def fake_auth_provider(self, request, mocker):
        class FakeAuthProvider(AuthenticationProvider):
            pass

        if request.param == "Device":
            fake_auth_provider = FakeAuthProvider(hostname=fake_hostname, device_id=fake_device_id)
        else:
            fake_auth_provider = FakeAuthProvider(
                hostname=fake_hostname, device_id=fake_device_id, module_id=fake_module_id
            )
        fake_auth_provider.get_x509_certificate = mocker.MagicMock()
        return fake_auth_provider

    @pytest.fixture
    def op(self, mocker, fake_auth_provider):
        return pipeline_ops_iothub.SetX509AuthProviderOperation(
            auth_provider=fake_auth_provider, callback=mocker.MagicMock()
        )

    @pytest.mark.it(
        "Sets the operation's authentication provider on the stage as the 'auth_provider' attribute"
    )
    def test_set_auth_provider(self, op, stage):
        assert stage.auth_provider is None

        stage.run_op(op)

        assert stage.auth_provider is op.auth_provider

    # NOTE: Because currently auth providers don't have a consistent attribute surface, only some
    # have the 'ca_cert' and 'gateway_hostname' attributes, so parametrize to show they default to
    # None when non-existent. If authentication providers ever receive a uniform surface, this
    # parametrization will no longer be required.
    @pytest.mark.it(
        "Sends a new SetIoTHubConnectionArgsOperation op down the pipeline, containing connection info from the authentication provider"
    )
    @pytest.mark.parametrize(
        "all_auth_args", [True, False], ids=["All authentication args", "Only guaranteed args"]
    )
    def test_send_new_op_down(self, mocker, op, stage, all_auth_args):
        if all_auth_args:
            op.auth_provider.ca_cert = fake_ca_cert
            op.auth_provider.gateway_hostname = fake_gateway_hostname

        stage.run_op(op)

        # A SetIoTHubConnectionArgsOperation op has been sent down the pipeline
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_iothub.SetIoTHubConnectionArgsOperation)

        # The IoTHubConnectionArgsOperation has details from the auth provider
        assert new_op.device_id == op.auth_provider.device_id
        assert new_op.module_id == op.auth_provider.module_id
        assert new_op.hostname == op.auth_provider.hostname
        assert new_op.client_cert is op.auth_provider.get_x509_certificate.return_value
        assert new_op.sas_token is None
        if all_auth_args:
            assert new_op.ca_cert == op.auth_provider.ca_cert
            assert new_op.gateway_hostname == op.auth_provider.gateway_hostname
        else:
            assert new_op.ca_cert is None
            assert new_op.gateway_hostname is None

    @pytest.mark.it(
        "Completes the original operation upon completion of the SetIoTHubConnectionArgsOperation"
    )
    def test_complete_worker(self, op, stage, op_error):
        # Run original op
        stage.run_op(op)
        assert not op.completed

        # A SetIoTHubConnectionArgsOperation op has been sent down the pipeline
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_iothub.SetIoTHubConnectionArgsOperation)
        assert not new_op.completed

        # Complete the new op
        new_op.complete(error=op_error)

        # Both ops are now completed
        assert new_op.completed
        assert new_op.error is op_error
        assert op.completed
        assert op.error is op_error


@pytest.mark.describe("UseAuthProviderStage - .run_op() -- Called with arbitrary other operation")
class TestUseAuthProviderStageRunOpWithAribitraryOperation(
    StageRunOpTestBase, UseAuthProviderStageTestConfig
):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down the pipeline")
    def test_sends_down(self, mocker, stage, op):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)
        assert not op.completed


@pytest.mark.describe("UseAuthProviderStage - EVENT: SAS Authentication Provider updates SAS token")
class TestUseAuthProviderStageWhenAuthProviderGeneratesNewSasToken(UseAuthProviderStageTestConfig):
    # Auth Providers are configured with different values depending on if the higher level client
    # is a Device or Module. Parametrize with both possibilities.
    # TODO: Eventually would be ideal to test using real auth provider instead of the fake one
    # This probably should just wait until auth provider refactor for ease though.
    @pytest.fixture(params=["Device", "Module"])
    def fake_auth_provider(self, request, mocker):
        class FakeAuthProvider(AuthenticationProvider):
            pass

        if request.param == "Device":
            fake_auth_provider = FakeAuthProvider(hostname=fake_hostname, device_id=fake_device_id)
        else:
            fake_auth_provider = FakeAuthProvider(
                hostname=fake_hostname, device_id=fake_device_id, module_id=fake_module_id
            )
        fake_auth_provider.get_current_sas_token = mocker.MagicMock()
        return fake_auth_provider

    @pytest.fixture
    def stage(self, mocker, init_kwargs, fake_auth_provider):
        stage = pipeline_stages_iothub.UseAuthProviderStage(**init_kwargs)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()

        # Attach an auth provider
        set_auth_op = pipeline_ops_iothub.SetAuthProviderOperation(
            auth_provider=fake_auth_provider, callback=mocker.MagicMock()
        )
        stage.run_op(set_auth_op)
        assert stage.auth_provider is fake_auth_provider
        stage.send_op_down.reset_mock()
        stage.send_event_up.reset_mock()
        return stage

    @pytest.mark.it("Sends an UpdateSasTokenOperation with the new SAS token down the pipeline")
    def test_generates_new_token(self, mocker, stage):
        stage.auth_provider.on_sas_token_updated_handler()

        assert stage.send_op_down.call_count == 1
        op = stage.send_op_down.call_args[0][0]
        assert isinstance(op, pipeline_ops_base.UpdateSasTokenOperation)
        assert op.sas_token is stage.auth_provider.get_current_sas_token.return_value

    @pytest.mark.it(
        "Sends the error to the background exception handler, if the UpdateSasTokenOperation is completed with error"
    )
    def test_update_fails(
        self, mocker, stage, arbitrary_exception, mock_handle_background_exception
    ):
        stage.auth_provider.on_sas_token_updated_handler()

        assert stage.send_op_down.call_count == 1
        op = stage.send_op_down.call_args[0][0]

        assert mock_handle_background_exception.call_count == 0

        op.complete(error=arbitrary_exception)
        assert mock_handle_background_exception.call_count == 1
        assert mock_handle_background_exception.call_args == mocker.call(arbitrary_exception)


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
    # CT-TODO: parametrize this with realistic json objects
    @pytest.fixture
    def json_patch(self):
        return {"json_key": "json_val"}

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


@pytest.mark.describe(
    "TwinRequestResponseStage - EVENT: RequestAndResponseOperation created from GetTwinOperation is completed"
)
class TestTwinRequestResponseStageWhenRequestAndResponseCreatedFromGetTwinOperationCompleted(
    TwinRequestResponseStageTestConfig
):
    # 200s - Successful, 300s - Redirect, 400s - Service error, 500s - Server error
    status_codes = [200, 300, 400, 500]

    @pytest.fixture
    def get_twin_op(self, mocker):
        return pipeline_ops_iothub.GetTwinOperation(callback=mocker.MagicMock())

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs, get_twin_op):
        stage = cls_type(**init_kwargs)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()

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
    def test_request_and_response_op_completed_with_err(self, stage, request_and_response_op):
        pass


# pipeline_stage_test.add_base_pipeline_stage_tests_old(
#     cls=pipeline_stages_iothub.TwinRequestResponseStage,
#     module=this_module,
#     all_ops=all_common_ops + all_iothub_ops,
#     handled_ops=[
#         pipeline_ops_iothub.GetTwinOperation,
#         pipeline_ops_iothub.PatchTwinReportedPropertiesOperation,
#     ],
#     all_events=all_common_events + all_iothub_events,
#     handled_events=[],
# )


# @pytest.mark.describe("TwinRequestResponseStage - .run_op() -- called with GetTwinOperation")
# class TestHandleTwinOperationsRunOpWithGetTwin(StageTestBase):
#     @pytest.fixture
#     def stage(self):
#         return pipeline_stages_iothub.TwinRequestResponseStage()

#     @pytest.fixture
#     def op(self, stage, mocker):
#         op = pipeline_ops_iothub.GetTwinOperation(callback=mocker.MagicMock())
#         mocker.spy(op, "complete")
#         return op

#     @pytest.fixture
#     def twin(self):
#         return {"Am I a twin": "You bet I am"}

#     @pytest.fixture
#     def twin_as_bytes(self, twin):
#         return json.dumps(twin).encode("utf-8")

#     @pytest.mark.it(
#         "Runs a RequestAndResponseOperation operation on the next stage with request_type='twin', method='GET', resource_location='/', and request_body=' '"
#     )
#     def test_sends_new_operation(self, stage, op):
#         stage.run_op(op)
#         assert stage.next.run_op.call_count == 1
#         new_op = stage.next.run_op.call_args[0][0]
#         assert isinstance(new_op, pipeline_ops_base.RequestAndResponseOperation)
#         assert new_op.request_type == "twin"
#         assert new_op.method == "GET"
#         assert new_op.resource_location == "/"
#         assert new_op.request_body == " "

#     @pytest.mark.it(
#         "Completes the GetTwinOperation with the failure from RequestAndResponseOperation, if the RequestAndResponseOperation completes with failure"
#     )
#     def test_next_stage_returns_error(self, mocker, stage, op, arbitrary_exception):
#         def next_stage_run_op(self, next_stage_op):
#             next_stage_op.complete(error=arbitrary_exception)

#         stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
#         stage.run_op(op)
#         assert op.complete.call_count == 1
#         assert op.complete.call_args == mocker.call(error=arbitrary_exception)

#     @pytest.mark.it(
#         "Completes the GetTwinOperation with a ServiceError if the RequestAndResponseOperation returns a status code >= 300"
#     )
#     def test_next_stage_returns_status_over_300(self, mocker, stage, op):
#         def next_stage_run_op(self, next_stage_op):
#             next_stage_op.status_code = 400
#             # TODO: should this have a body? Should with/without be a separate test?
#             next_stage_op.response_body = json.dumps("").encode("utf-8")
#             next_stage_op.complete()

#         stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
#         stage.run_op(op)
#         assert op.complete.call_count == 1
#         assert type(op.complete.call_args[1]["error"]) is ServiceError

#     @pytest.mark.it(
#         "Decodes, deserializes, and returns the request_body from RequestAndResponseOperation as the twin attribute on the op along with no error if the status code < 300"
#     )
#     def test_next_stage_completes_correctly(self, mocker, stage, op, twin, twin_as_bytes):
#         def next_stage_run_op(self, next_stage_op):
#             next_stage_op.status_code = 200
#             next_stage_op.response_body = twin_as_bytes
#             next_stage_op.complete()

#         stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
#         stage.run_op(op)
#         assert op.complete.call_count == 1
#         assert op.complete.call_args == mocker.call(error=None)
#         assert op.twin == twin


# @pytest.mark.describe(
#     "TwinRequestResponseStage - .run_op() -- called with PatchTwinReportedPropertiesOperation"
# )
# class TestHandleTwinOperationsRunOpWithPatchTwinReportedProperties(StageTestBase):
#     @pytest.fixture
#     def stage(self):
#         return pipeline_stages_iothub.TwinRequestResponseStage()

#     @pytest.fixture
#     def patch(self):
#         return {"__fake_patch__": "yes"}

#     @pytest.fixture
#     def patch_as_string(self, patch):
#         return json.dumps(patch)

#     @pytest.fixture
#     def op(self, stage, mocker, patch):
#         op = pipeline_ops_iothub.PatchTwinReportedPropertiesOperation(
#             patch=patch, callback=mocker.MagicMock()
#         )
#         mocker.spy(op, "complete")
#         return op

#     @pytest.mark.it(
#         "Runs a RequestAndResponseOperation operation on the next stage with request_type='twin', method='PATCH', resource_location='/properties/reported/', and the request_body attribute set to a stringification of the patch"
#     )
#     def test_sends_new_operation(self, stage, op, patch_as_string):
#         stage.run_op(op)
#         assert stage.next.run_op.call_count == 1
#         new_op = stage.next.run_op.call_args[0][0]
#         assert isinstance(new_op, pipeline_ops_base.RequestAndResponseOperation)
#         assert new_op.request_type == "twin"
#         assert new_op.method == "PATCH"
#         assert new_op.resource_location == "/properties/reported/"
#         assert new_op.request_body == patch_as_string

#     @pytest.mark.it(
#         "Completes the PatchTwinReportedPropertiesOperation with the failure from RequestAndResponseOperation, if the RequestAndResponse operation completes with failure"
#     )
#     def test_next_stage_returns_error(self, mocker, stage, op, arbitrary_exception):
#         def next_stage_run_op(self, next_stage_op):
#             next_stage_op.complete(error=arbitrary_exception)

#         stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
#         stage.run_op(op)
#         assert op.complete.call_count == 1
#         assert op.complete.call_args == mocker.call(error=arbitrary_exception)

#     @pytest.mark.it(
#         "Completes the PatchTwinReportedPropertiesOperation with a ServiceError, if the RequestAndResponseOperation returns a status code >= 300"
#     )
#     def test_next_stage_returns_status_over_300(self, stage, op):
#         def next_stage_run_op(self, next_stage_op):
#             next_stage_op.status_code = 400
#             next_stage_op.complete()

#         stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
#         stage.run_op(op)
#         assert op.complete.call_count == 1
#         assert type(op.complete.call_args[1]["error"]) is ServiceError

#     @pytest.mark.it(
#         "Completes the PatchTwinReportedPropertiesOperation successfully if the status code < 300"
#     )
#     def test_next_stage_completes_correctly(self, mocker, stage, op):
#         def next_stage_run_op(self, next_stage_op):
#             next_stage_op.status_code = 200
#             next_stage_op.complete()

#         stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
#         stage.run_op(op)
#         assert op.complete.call_count == 1
#         assert op.complete.call_args == mocker.call(error=None)
