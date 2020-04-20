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
from azure.iot.device.common.pipeline import pipeline_events_base, pipeline_ops_base
from azure.iot.device.iothub.pipeline import (
    pipeline_events_iothub,
    pipeline_ops_iothub,
    pipeline_stages_iothub,
    constant as pipeline_constants,
)
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
fake_server_verification_cert = "__fake_server_verification_cert__"
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
        fake_auth_provider.on_sas_token_updated_handler_list = [mocker.MagicMock()]
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
    # have the 'server_verification_cert' and 'gateway_hostname' attributes, so parametrize to show they default to
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
            op.auth_provider.server_verification_cert = fake_server_verification_cert
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
            assert new_op.server_verification_cert == op.auth_provider.server_verification_cert
            assert new_op.gateway_hostname == op.auth_provider.gateway_hostname
        else:
            assert new_op.server_verification_cert is None
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
    "UseAuthProviderStage - .run_op() -- Called with SetX509AuthProviderOperation (X509 Authentication)"
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
    # have the 'server_verification_cert' and 'gateway_hostname' attributes, so parametrize to show they default to
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
            op.auth_provider.server_verification_cert = fake_server_verification_cert
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
            assert new_op.server_verification_cert == op.auth_provider.server_verification_cert
            assert new_op.gateway_hostname == op.auth_provider.gateway_hostname
        else:
            assert new_op.server_verification_cert is None
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


@pytest.mark.describe(
    "UseAuthProviderStage - OCCURANCE: SAS Authentication Provider updates SAS token"
)
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
        fake_auth_provider.on_sas_token_updated_handler_list = [mocker.MagicMock()]
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
        for x in stage.auth_provider.on_sas_token_updated_handler_list:
            x()

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
        for x in stage.auth_provider.on_sas_token_updated_handler_list:
            x()

        assert stage.send_op_down.call_count == 1
        op = stage.send_op_down.call_args[0][0]

        assert mock_handle_background_exception.call_count == 0

        op.complete(error=arbitrary_exception)
        assert mock_handle_background_exception.call_count == 1
        assert mock_handle_background_exception.call_args == mocker.call(arbitrary_exception)


#########################################
# ENSURE DESIRED PROPERTIES STAGE STAGE #
#########################################


class EnsureDesiredPropertiesStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_iothub.EnsureDesiredPropertiesStage

    @pytest.fixture
    def init_kwargs(self):
        return {}

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        return stage


class EnsureDesiredPropertiesStageInstantiationTests(EnsureDesiredPropertiesStageTestConfig):
    @pytest.mark.it("Initializes 'last_version_seen' None")
    def test_last_version_seen(self, init_kwargs):
        stage = pipeline_stages_iothub.EnsureDesiredPropertiesStage(**init_kwargs)
        assert stage.last_version_seen is None

    @pytest.mark.it("Initializes 'pending_get_request' None")
    def test_pending_get_request(self, init_kwargs):
        stage = pipeline_stages_iothub.EnsureDesiredPropertiesStage(**init_kwargs)
        assert stage.pending_get_request is None


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_iothub.EnsureDesiredPropertiesStage,
    stage_test_config_class=EnsureDesiredPropertiesStageTestConfig,
    extended_stage_instantiation_test_class=EnsureDesiredPropertiesStageInstantiationTests,
)


@pytest.mark.describe(
    "EnsureDesiredPropertiesStage - .run_op() -- Called with EnableFeatureOperation"
)
class TestEnsureDesiredPropertiesStageRunOpWithEnableFeatureOperation(
    StageRunOpTestBase, EnsureDesiredPropertiesStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.EnableFeatureOperation(
            feature_name="fake_feature_name", callback=mocker.MagicMock()
        )

    @pytest.mark.it("Sets `last_version_seen` to -1 if `op.feature_name` is 'twin_patches'")
    def test_sets_last_version_seen(self, mocker, stage, op):
        op.feature_name = pipeline_constants.TWIN_PATCHES

        assert stage.last_version_seen is None
        stage.run_op(op)

        assert stage.last_version_seen == -1

    @pytest.mark.parametrize(
        "feature_name",
        [
            pipeline_constants.C2D_MSG,
            pipeline_constants.INPUT_MSG,
            pipeline_constants.METHODS,
            pipeline_constants.TWIN,
        ],
    )
    @pytest.mark.it(
        "Does not change `last_version_seen` if `op.feature_name` is not 'twin_patches'"
    )
    def test_doesnt_set_last_version_seen(self, mocker, stage, op, feature_name):
        op.feature_name = feature_name
        stage.last_version_seen = mocker.MagicMock()

        old_value = stage.last_version_seen
        stage.run_op(op)

        assert stage.last_version_seen == old_value

    @pytest.mark.parametrize(
        "feature_name",
        [
            pipeline_constants.C2D_MSG,
            pipeline_constants.INPUT_MSG,
            pipeline_constants.METHODS,
            pipeline_constants.TWIN,
            pipeline_constants.TWIN_PATCHES,
        ],
    )
    @pytest.mark.it(
        "Sends the EnableFeatureOperation op to the next stage for all valid `op.feature_name` values"
    )
    def test_passes_all_other_features_down(self, mocker, stage, op, feature_name):
        op.feature_name = feature_name

        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe("EnsureDesiredPropertiesStage - OCCURANCE: ConnectedEvent received")
class TestEnsureDesiredPropertiesStageWhenConnectedEventReceived(
    EnsureDesiredPropertiesStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        return stage

    @pytest.fixture
    def event(self):
        return pipeline_events_base.ConnectedEvent()

    @pytest.mark.it(
        "Sends a GetTwinOperation if last_version_seen is set and there is no pending GetTwinOperation"
    )
    def test_last_version_seen_no_pending(self, mocker, stage, event):
        stage.last_version_seen = mocker.MagicMock()
        stage.pending_get_request = None

        stage.handle_pipeline_event(event)

        assert stage.send_op_down.call_count == 1
        assert isinstance(stage.send_op_down.call_args[0][0], pipeline_ops_iothub.GetTwinOperation)

    @pytest.mark.it(
        "Does not send a GetTwinOperation if last verion seen is set and there is already a pending GetTwinOperation"
    )
    def test_last_version_seen_pending(self, mocker, stage, event):
        stage.last_version_seen = mocker.MagicMock()
        stage.pending_get_request = mocker.MagicMock()

        stage.handle_pipeline_event(event)

        assert stage.send_op_down.call_count == 0

    @pytest.mark.it(
        "Does not send a GetTwinOperation if last_version_seen is not set and there is no pending GetTwinOperation"
    )
    def test_no_last_version_seen_no_pending(self, mocker, stage, event):
        stage.last_version_seen = None
        stage.pending_get_request = None

        stage.handle_pipeline_event(event)

        assert stage.send_op_down.call_count == 0

    @pytest.mark.it(
        "Does not send a GetTwinOperation if last verion seen is not set and there is already a pending GetTwinOperation"
    )
    def test_no_last_version_seen_pending(self, mocker, stage, event):
        stage.last_version_seen = None
        stage.pending_get_request = mocker.MagicMock()

        stage.handle_pipeline_event(event)

        assert stage.send_op_down.call_count == 0


@pytest.mark.describe(
    "EnsureDesiredPropertiesStage - OCCURANCE: TwinDesiredPropertiesPatchEvent received"
)
class TestEnsureDesiredPropertiesStageWhenTwinDesiredPropertiesPatchEventReceived(
    EnsureDesiredPropertiesStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        return stage

    @pytest.fixture
    def version(self, mocker):
        return mocker.MagicMock()

    @pytest.fixture
    def event(self, version):
        return pipeline_events_iothub.TwinDesiredPropertiesPatchEvent(patch={"$version": version})

    @pytest.mark.it("Saves the `$version` attribute of the patch into `last_version_seen`")
    def test_saves_the_last_version_seen(self, mocker, stage, event, version):
        stage.last_version_seen = mocker.MagicMock()

        stage.handle_pipeline_event(event)

        assert stage.last_version_seen == version

    @pytest.mark.it("Sends the event to the previous stage")
    def test_sends_event_up(self, mocker, stage, event, version):

        stage.handle_pipeline_event(event)

        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)


@pytest.mark.describe(
    "EnsureDesiredPropertiesStage - OCCURANCE: GetTwinOperation that was sent down by this stage completes"
)
class TestEnsureDesiredPropertiesStageWhenGetTwinOperationCompletes(
    EnsureDesiredPropertiesStageTestConfig
):
    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        return stage

    @pytest.fixture
    def get_twin_op(self, stage):
        stage.last_version_seen = -1
        stage.handle_pipeline_event(pipeline_events_base.ConnectedEvent())

        get_twin_op = stage.send_op_down.call_args[0][0]
        assert isinstance(get_twin_op, pipeline_ops_iothub.GetTwinOperation)

        stage.send_op_down.reset_mock()
        stage.send_event_up.reset_mock()

        return get_twin_op

    @pytest.fixture
    def new_version(self):
        return 1234

    @pytest.fixture
    def new_twin(self, new_version):
        return {"desired": {"$version": new_version}, "reported": {}}

    @pytest.mark.it("Does not send a new GetTwinOperation if the op completes with success")
    def test_does_not_send_new_get_twin_operation_on_success(self, stage, get_twin_op, new_twin):

        get_twin_op.twin = new_twin
        get_twin_op.complete()

        assert stage.send_op_down.call_count == 0

    @pytest.mark.it("Sets `pending_get_request` to None if the op completes with success")
    def test_sets_pending_request_to_none_on_success(self, mocker, stage, get_twin_op, new_twin):
        stage.pending_get_request = mocker.MagicMock()

        get_twin_op.twin = new_twin
        get_twin_op.complete()

        assert stage.pending_get_request is None

    @pytest.mark.it("Sends a new GetTwinOperation if the op completes with an error")
    def test_sends_new_get_twin_operation_on_failure(self, stage, get_twin_op, arbitrary_exception):

        assert stage.send_op_down.call_count == 0

        get_twin_op.complete(error=arbitrary_exception)

        assert stage.send_op_down.call_count == 1
        assert isinstance(stage.send_op_down.call_args[0][0], pipeline_ops_iothub.GetTwinOperation)

    @pytest.mark.it(
        "Sets `pending_get_request` to the new GetTwinOperation if the op completes with an error"
    )
    def test_sets_pending_request_to_none_on_failure(
        self, mocker, stage, get_twin_op, arbitrary_exception
    ):
        old_get_request = mocker.MagicMock()
        stage.pending_get_request = old_get_request

        get_twin_op.complete(error=arbitrary_exception)

        assert stage.pending_get_request is not old_get_request
        assert isinstance(stage.pending_get_request, pipeline_ops_iothub.GetTwinOperation)

    @pytest.mark.it(
        "Does not send a `TwinDesiredPropertiesPatchEvent` if the op copmletes with an error"
    )
    def test_doesnt_send_patch_event_if_error(self, stage, get_twin_op, arbitrary_exception):
        get_twin_op.complete(arbitrary_exception)

        assert stage.send_event_up.call_count == 0

    @pytest.mark.it(
        "Sends a `TwinDesiredPropertiesPatchEvent` if the desired properties '$version' doesn't match the `last_version_seen`"
    )
    def test_sends_patch_event_if_different_version(
        self, mocker, stage, get_twin_op, new_twin, new_version
    ):
        stage.last_version_seen = mocker.MagicMock()

        get_twin_op.twin = new_twin
        get_twin_op.complete()

        assert stage.send_event_up.call_count == 1
        assert isinstance(
            stage.send_event_up.call_args[0][0],
            pipeline_events_iothub.TwinDesiredPropertiesPatchEvent,
        )

    @pytest.mark.it(
        "Does not send a `TwinDesiredPropertiesPatchEvent` if the desired properties '$version'  matches the `last_version_seen`"
    )
    def test_doesnt_send_patch_event_if_same_version(
        self, stage, get_twin_op, new_twin, new_version
    ):
        stage.last_version_seen = new_version

        get_twin_op.twin = new_twin
        get_twin_op.complete()

        assert stage.send_event_up.call_count == 0

    @pytest.mark.it(
        "Does not change the `last_version_seen` attribute if the op completes with an error"
    )
    def test_doesnt_change_last_version_seen_if_error(
        self, mocker, stage, get_twin_op, arbitrary_exception
    ):
        old_version = mocker.MagicMock()
        stage.last_version_seen = old_version

        get_twin_op.complete(error=arbitrary_exception)

        assert stage.last_version_seen == old_version

    @pytest.mark.it(
        "Sets the `last_version_seen` attribute to the new version if the desired properties '$version' doesn't match the `last_version_seen`"
    )
    def test_changes_last_version_seen_if_different_version(
        self, mocker, stage, get_twin_op, new_twin, new_version
    ):
        stage.last_version_seen = mocker.MagicMock()

        get_twin_op.twin = new_twin
        get_twin_op.complete()

        assert stage.last_version_seen == new_version

    @pytest.mark.it(
        "Does not change the `last_version_seen` attribute if the desired properties '$version' matches the `last_version_seen`"
    )
    def test_does_not_change_last_version_seen_if_same_version(
        self, stage, get_twin_op, new_twin, new_version
    ):
        stage.last_version_seen = new_version

        get_twin_op.twin = new_twin
        get_twin_op.complete()

        assert stage.last_version_seen == new_version


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


# TODO: Provide a more accurate set of status codes for tests
@pytest.mark.describe(
    "TwinRequestResponseStage - OCCURANCE: RequestAndResponseOperation created from GetTwinOperation is completed"
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
    "TwinRequestResponseStage - OCCURANCE: RequestAndResponseOperation created from PatchTwinReportedPropertiesOperation is completed"
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
