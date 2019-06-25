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
from azure.iot.device.common.pipeline import pipeline_ops_base
from azure.iot.device.iothub.pipeline import pipeline_stages_iothub, pipeline_ops_iothub
from tests.common.pipeline.helpers import (
    assert_callback_succeeded,
    assert_callback_failed,
    all_common_ops,
    all_common_events,
    all_except,
    make_mock_stage,
    UnhandledException,
)
from tests.iothub.pipeline.helpers import all_iothub_ops, all_iothub_events
from tests.common.pipeline import pipeline_stage_test

logging.basicConfig(level=logging.INFO)

this_module = sys.modules[__name__]


fake_device_id = "__fake_device_id__"
fake_module_id = "__fake_module_id__"
fake_hostname = "__fake_hostname__"
fake_gateway_hostname = "__fake_gateway_hostname__"
fake_ca_cert = "__fake_ca_cert__"
fake_sas_token = "__fake_sas_token__"

pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_iothub.UseSkAuthProviderStage,
    module=this_module,
    all_ops=all_common_ops + all_iothub_ops,
    handled_ops=[pipeline_ops_iothub.SetAuthProviderOperation],
    all_events=all_common_events + all_iothub_events,
    handled_events=[],
)


def make_mock_auth_provider(mocker):
    class MockAuthProvider(object):
        pass

    auth_provider = MockAuthProvider()
    auth_provider.device_id = fake_device_id
    auth_provider.hostname = fake_hostname
    auth_provider.get_current_sas_token = mocker.Mock(return_value=fake_sas_token)
    return auth_provider


@pytest.mark.describe("UseSkAuthProvider - .run_op() -- called with SetAuthProviderOperation")
class TestUseSkAuthProviderRunOpWithSetAuthProviderOperation(object):
    @pytest.fixture
    def stage(self, mocker):
        return make_mock_stage(mocker, pipeline_stages_iothub.UseSkAuthProviderStage)

    @pytest.fixture
    def set_auth_provider(self, mocker, callback):
        op = pipeline_ops_iothub.SetAuthProviderOperation(
            auth_provider=make_mock_auth_provider(mocker)
        )
        op.callback = callback
        return op

    @pytest.fixture
    def set_auth_provider_required_args_only(self, mocker, callback):
        op = pipeline_ops_iothub.SetAuthProviderOperation(
            auth_provider=make_mock_auth_provider(mocker)
        )
        op.callback = callback
        return op

    @pytest.fixture
    def set_auth_provider_all_args(self, mocker, callback):
        auth_provider = make_mock_auth_provider(mocker)
        auth_provider.module_id = fake_module_id
        auth_provider.ca_cert = fake_ca_cert
        auth_provider.gateway_hostname = fake_gateway_hostname
        op = pipeline_ops_iothub.SetAuthProviderOperation(auth_provider=auth_provider)
        op.callback = callback
        return op

    @pytest.mark.it("Runs SetAuthProviderArgsOperation op on the next stage")
    def test_runs_set_auth_provider_args(self, mocker, stage, set_auth_provider_required_args_only):
        stage.next._run_op = mocker.Mock()
        stage.run_op(set_auth_provider_required_args_only)
        assert stage.next._run_op.call_count == 1
        set_args = stage.next._run_op.call_args[0][0]
        assert isinstance(set_args, pipeline_ops_iothub.SetAuthProviderArgsOperation)

    @pytest.mark.it(
        "Sets the device_id, and hostname attributes on SetAuthProviderArgsOperation based on the same-names auth_provider attributes"
    )
    def test_sets_required_attributes(self, mocker, stage, set_auth_provider_required_args_only):
        stage.next._run_op = mocker.Mock()
        stage.run_op(set_auth_provider_required_args_only)
        set_args = stage.next._run_op.call_args[0][0]
        assert set_args.device_id == fake_device_id
        assert set_args.hostname == fake_hostname

    @pytest.mark.it(
        "Sets the gateway_hostname, ca_cert, and module_id attributes to None if they don't exist on the auth_provider object"
    )
    def test_defaults_optional_attributes_to_none(
        self, mocker, stage, set_auth_provider_required_args_only
    ):
        stage.next._run_op = mocker.Mock()
        stage.run_op(set_auth_provider_required_args_only)
        set_args = stage.next._run_op.call_args[0][0]
        assert set_args.gateway_hostname is None
        assert set_args.ca_cert is None
        assert set_args.module_id is None

    @pytest.mark.it(
        "Sets the module_id, gateway_hostname and ca_cert attributes on SetAuthProviderArgsOperation if they exist on the auth_provider object"
    )
    def test_sets_optional_attributes(self, mocker, stage, set_auth_provider_all_args):
        stage.next._run_op = mocker.Mock()
        stage.run_op(set_auth_provider_all_args)
        set_args = stage.next._run_op.call_args[0][0]
        assert set_args.gateway_hostname == fake_gateway_hostname
        assert set_args.ca_cert == fake_ca_cert
        assert set_args.module_id == fake_module_id

    @pytest.mark.it(
        "Handles any Exceptions raised by SetAuthProviderArgsOperation and returns them through the op callback"
    )
    def test_set_auth_provider_raises_exception(
        self, mocker, stage, fake_exception, set_auth_provider
    ):
        stage.next._run_op = mocker.Mock(side_effect=fake_exception)
        stage.run_op(set_auth_provider)
        assert_callback_failed(op=set_auth_provider, error=fake_exception)

    @pytest.mark.it(
        "Allows any  BaseExceptions raised by SetAuthProviderArgsOperation to propogate"
    )
    def test_set_auth_provider_raises_base_exception(
        self, mocker, stage, fake_base_exception, set_auth_provider
    ):
        stage.next._run_op = mocker.Mock(side_effect=fake_base_exception)
        with pytest.raises(UnhandledException):
            stage.run_op(set_auth_provider)

    @pytest.mark.it(
        "Does not run a SetSasToken op on the next stage if the SetAuthProviderArgsOperation op fails"
    )
    def test_does_not_set_sas_token_on_set_auth_provider_args_failure(
        self, mocker, stage, fake_exception, set_auth_provider
    ):
        stage.next._run_op = mocker.Mock(side_effect=fake_exception)
        stage.run_op(set_auth_provider)
        assert stage.next._run_op.call_count == 1

    @pytest.mark.it(
        "Runs a SetSasToken op on the next stage if the SetAuthProviderArgsOperation op succeeds"
    )
    def test_runs_set_sas_token(self, mocker, stage, set_auth_provider):
        def next_run_op(self, op):
            if isinstance(op, pipeline_ops_iothub.SetAuthProviderArgsOperation):
                op.callback(op)
            else:
                pass

        stage.next._run_op = functools.partial(next_run_op, stage)
        mocker.spy(stage.next, "_run_op")
        stage.run_op(set_auth_provider)
        assert stage.next._run_op.call_count == 2
        assert isinstance(
            stage.next._run_op.call_args_list[0][0][0],
            pipeline_ops_iothub.SetAuthProviderArgsOperation,
        )
        assert isinstance(
            stage.next._run_op.call_args_list[1][0][0], pipeline_ops_base.SetSasTokenOperation
        )

    @pytest.mark.it(
        "Calls get_current_sas_token on the auth_provider and passes the result as a SetSasToken attribute"
    )
    def test_calls_get_current_sas_token(self, stage, set_auth_provider):
        stage.run_op(set_auth_provider)
        assert set_auth_provider.auth_provider.get_current_sas_token.call_count == 1
        set_sas_token_op = stage.next._run_op.call_args_list[1][0][0]
        assert set_sas_token_op.sas_token == fake_sas_token

    @pytest.mark.it("Calls the callback with no error if the SetSasToken op succeeds")
    def test_returns_success_if_set_sas_token_succeeds(self, stage, set_auth_provider):
        stage.run_op(set_auth_provider)
        assert_callback_succeeded(op=set_auth_provider)

    @pytest.mark.it(
        "Handles any Exceptions raised by SetSasToken and returns them through the op callback"
    )
    def test_set_sas_token_raises_exception(self, mocker, fake_exception, stage, set_auth_provider):
        set_auth_provider.auth_provider.get_current_sas_token = mocker.Mock(
            side_effect=fake_exception
        )
        stage.run_op(set_auth_provider)
        assert_callback_failed(op=set_auth_provider, error=fake_exception)

    @pytest.mark.it("Allows any BaseExceptions raised by SetSasToken to propagate")
    def test_set_sas_token_raises_base_exception(
        self, mocker, fake_base_exception, stage, set_auth_provider
    ):
        set_auth_provider.auth_provider.get_current_sas_token = mocker.Mock(
            side_effect=fake_base_exception
        )
        with pytest.raises(UnhandledException):
            stage.run_op(set_auth_provider)

    @pytest.mark.it(
        "Calls the SetAuthProviderOperation callback with the SetSasToken error if SetSasToken fails"
    )
    def test_returns_set_sas_token_failure(self, fake_exception, stage, set_auth_provider):
        def next_run_op(self, op):
            if isinstance(op, pipeline_ops_iothub.SetAuthProviderArgsOperation):
                op.callback(op)
            else:
                raise fake_exception

        stage.next._run_op = functools.partial(next_run_op, stage)
        stage.run_op(set_auth_provider)
        assert_callback_failed(op=set_auth_provider, error=fake_exception)


pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_iothub.HandleTwinOperationsStage,
    module=this_module,
    all_ops=all_common_ops + all_iothub_ops,
    handled_ops=[
        pipeline_ops_iothub.GetTwinOperation,
        pipeline_ops_iothub.PatchTwinReportedPropertiesOperation,
    ],
    all_events=all_common_events + all_iothub_events,
    handled_events=[],
)


@pytest.mark.describe("HandleTwinOperationsStage - .run_op() -- called with GetTwinOperation")
class TestHandleTwinOperationsRunOpWithGetTwin(object):
    @pytest.fixture
    def stage(self, mocker):
        return make_mock_stage(mocker, pipeline_stages_iothub.HandleTwinOperationsStage)

    @pytest.fixture
    def op(self, stage, callback):
        return pipeline_ops_iothub.GetTwinOperation(callback=callback)

    @pytest.fixture
    def twin(self):
        return {"Am I a twin": "You bet I am"}

    @pytest.fixture
    def twin_as_bytes(self, twin):
        return json.dumps(twin).encode("utf-8")

    @pytest.mark.it(
        "Runs a SendIotRequestAndWaitForResponseOperation operation on the next stage with request_type='twin', method='GET', resource_location='/', and request_body=' '"
    )
    def test_sends_new_operation(self, stage, op):
        stage.run_op(op)
        assert stage.next.run_op.call_count == 1
        new_op = stage.next.run_op.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.SendIotRequestAndWaitForResponseOperation)
        assert new_op.request_type == "twin"
        assert new_op.method == "GET"
        assert new_op.resource_location == "/"
        assert new_op.request_body == " "

    @pytest.mark.it("Returns an Exception through the op callback if there is no next stage")
    def test_runs_with_no_next_stage(self, stage, op):
        stage.next = None
        stage.run_op(op)
        assert_callback_failed(op=op, error=Exception)

    @pytest.mark.it(
        "Handles any Exceptions raised by the SendIotRequestAndWaitForResponseOperation and returns them through the op callback"
    )
    def test_next_stage_raises_exception(self, stage, op, mocker):
        stage.next.run_op.side_effect = Exception
        stage.run_op(op)
        assert_callback_failed(op=op, error=Exception)

    @pytest.mark.it(
        "Allows any BaseExceptions raised by the SendIotRequestAndWaitForResponseOperation to propagate"
    )
    def test_next_stage_raises_base_exception(self, stage, op):
        stage.next.run_op.side_effect = UnhandledException
        with pytest.raises(UnhandledException):
            stage.run_op(op)

    @pytest.mark.it(
        "Returns any error in the SendIotRequestAndWaitForResponseOperation callback through the op callback"
    )
    def test_next_stage_returns_error(self, stage, op):
        error = Exception()

        def next_stage_run_op(self, op):
            op.error = error
            op.callback(op)

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert_callback_failed(op=op, error=error)

    @pytest.mark.it(
        "Returns an error in the op callback if the SendIotRequestAndWaitForResponseOperation returns a status code >= 300"
    )
    def test_next_stage_returns_status_over_300(self, stage, op):
        def next_stage_run_op(self, op):
            op.status_code = 400
            op.callback(op)

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert_callback_failed(op=op, error=Exception)

    @pytest.mark.it(
        "Decodes, deserializes, and returns the request_body from SendIotRequestAndWaitForResponseOperation as the twin attribute on the op along with no error if the status code < 300"
    )
    def test_next_stage_completes_correctly(self, stage, op, twin, twin_as_bytes):
        def next_stage_run_op(self, op):
            op.status_code = 200
            op.response_body = twin_as_bytes
            op.callback(op)

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert_callback_succeeded(op=op)
        assert op.twin == twin


@pytest.mark.describe(
    "HandleTwinOperationsStage - .run_op() -- called with PatchTwinReportedPropertiesOperation"
)
class TestHandleTwinOperationsRunOpWithPatchTwinReportedProperties(object):
    @pytest.fixture
    def stage(self, mocker):
        return make_mock_stage(mocker, pipeline_stages_iothub.HandleTwinOperationsStage)

    @pytest.fixture
    def patch(self):
        return {"__fake_patch__": "yes"}

    @pytest.fixture
    def patch_as_string(self, patch):
        return json.dumps(patch)

    @pytest.fixture
    def op(self, stage, callback, patch):
        return pipeline_ops_iothub.PatchTwinReportedPropertiesOperation(
            patch=patch, callback=callback
        )

    @pytest.mark.it(
        "Runs a SendIotRequestAndWaitForResponseOperation operation on the next stage with request_type='twin', method='PATCH', resource_location='/properties/reported/', and the request_body attribute set to a stringification of the patch"
    )
    def test_sends_new_operation(self, stage, op, patch_as_string):
        stage.run_op(op)
        assert stage.next.run_op.call_count == 1
        new_op = stage.next.run_op.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.SendIotRequestAndWaitForResponseOperation)
        assert new_op.request_type == "twin"
        assert new_op.method == "PATCH"
        assert new_op.resource_location == "/properties/reported/"
        assert new_op.request_body == patch_as_string

    @pytest.mark.it("Returns an Exception through the op callback if there is no next stage")
    def test_runs_with_no_next_stage(self, stage, op):
        stage.next = None
        stage.run_op(op)
        assert_callback_failed(op=op, error=Exception)

    @pytest.mark.it(
        "Handles any Exceptions raised by the SendIotRequestAndWaitForResponseOperation and returns them through the op callback"
    )
    def test_next_stage_raises_exception(self, stage, op):
        stage.next.run_op.side_effect = Exception
        stage.run_op(op)
        assert_callback_failed(op=op, error=Exception)

    @pytest.mark.it(
        "Allows any BaseExceptions raised by the SendIotRequestAndWaitForResponseOperation to propagate"
    )
    def test_next_stage_raises_base_exception(self, stage, op):
        stage.next.run_op.side_effect = UnhandledException
        with pytest.raises(UnhandledException):
            stage.run_op(op)

    @pytest.mark.it(
        "Returns any error in the SendIotRequestAndWaitForResponseOperation callback through the op callback"
    )
    def test_next_stage_returns_error(self, stage, op):
        error = Exception()

        def next_stage_run_op(self, op):
            op.error = error
            op.callback(op)

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert_callback_failed(op=op, error=error)

    @pytest.mark.it(
        "Returns an error in the op callback if the SendIotRequestAndWaitForResponseOperation returns a status code >= 300"
    )
    def test_next_stage_returns_status_over_300(self, stage, op):
        def next_stage_run_op(self, op):
            op.status_code = 400
            op.callback(op)

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert_callback_failed(op=op, error=Exception)

    @pytest.mark.it("Returns no error on the op callback if the status code < 300")
    def test_next_stage_completes_correctly(self, stage, op):
        def next_stage_run_op(self, op):
            op.status_code = 200
            op.callback(op)

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert_callback_succeeded(op=op)
