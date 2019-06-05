# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import functools
from azure.iot.device.common.pipeline import pipeline_ops_base
from azure.iot.device.iothub.pipeline import pipeline_stages_iothub, pipeline_ops_iothub
from tests.common.pipeline_test import (
    assert_default_stage_attributes,
    assert_callback_succeeded,
    assert_callback_failed,
    ConcretePipelineStage,
    all_common_ops,
    all_except,
    make_mock_stage,
    UnhandledException,
)
from tests.iothub.pipeline_test import all_iothub_ops

logging.basicConfig(level=logging.INFO)


@pytest.fixture
def stage(mocker):
    return make_mock_stage(mocker, pipeline_stages_iothub.UseSkAuthProvider)


fake_device_id = "__fake_device_id__"
fake_module_id = "__fake_module_id__"
fake_hostname = "__fake_hostname__"
fake_gateway_hostname = "__fake_gateway_hostname__"
fake_ca_cert = "__fake_ca_cert__"
fake_sas_token = "__fake_sas_token__"


def make_mock_auth_provider(mocker):
    class MockAuthProvider(object):
        pass

    auth_provider = MockAuthProvider()
    auth_provider.device_id = fake_device_id
    auth_provider.hostname = fake_hostname
    auth_provider.get_current_sas_token = mocker.Mock(return_value=fake_sas_token)
    return auth_provider


@pytest.fixture
def set_auth_provider(mocker, callback):
    op = pipeline_ops_iothub.SetAuthProvider(auth_provider=make_mock_auth_provider(mocker))
    op.callback = callback
    return op


@pytest.fixture
def set_auth_provider_required_args_only(mocker, callback):
    op = pipeline_ops_iothub.SetAuthProvider(auth_provider=make_mock_auth_provider(mocker))
    op.callback = callback
    return op


@pytest.fixture
def set_auth_provider_all_args(mocker, callback):
    auth_provider = make_mock_auth_provider(mocker)
    auth_provider.module_id = fake_module_id
    auth_provider.ca_cert = fake_ca_cert
    auth_provider.gateway_hostname = fake_gateway_hostname
    op = pipeline_ops_iothub.SetAuthProvider(auth_provider=auth_provider)
    op.callback = callback
    return op


@pytest.mark.describe("UseSkAuthProvider initializer")
class TestUseSkAuthProvierInitializer(object):
    @pytest.mark.it("Sets name attribute on instantiation")
    @pytest.mark.it("Sets next attribute to None on instantiation")
    @pytest.mark.it("Sets previous attribute to None on instantiation")
    @pytest.mark.it("Sets pipeline_root attribute to None on instantiation")
    def test_initializer(self):
        obj = pipeline_stages_iothub.UseSkAuthProvider()
        assert_default_stage_attributes(obj)


unknown_ops = all_except(
    all_items=(all_common_ops + all_iothub_ops),
    items_to_exclude=[pipeline_ops_iothub.SetAuthProvider],
)

# TODO: test any events in here?


@pytest.mark.describe("UseSkAuthProvider _runOp function with unhandled operations")
class TestUseSkAuthProviderRunOpWithUnknownOperation(object):
    @pytest.mark.parametrize(
        "op_init,op_init_args", unknown_ops, ids=[x[0].__name__ for x in unknown_ops]
    )
    @pytest.mark.it("passes unknown operations to the next stage")
    def test_passes_unknown_op_down(self, mocker, stage, op_init, op_init_args):
        op = op_init(*op_init_args)
        op.action = "pend"
        stage.run_op(op)
        assert stage.next._run_op.call_count == 1
        assert stage.next._run_op.call_args == mocker.call(op)


@pytest.mark.describe("UseSkAuthProvider _runOp function with SetAuthProvider operations")
class TestUseSkAuthProviderRunOpWithSetAuthProvider(object):
    @pytest.mark.it("runs SetAuthProviderArgs op on the next stage")
    def test_runs_set_auth_provider_args(self, mocker, stage, set_auth_provider_required_args_only):
        stage.next._run_op = mocker.Mock()
        stage.run_op(set_auth_provider_required_args_only)
        assert stage.next._run_op.call_count == 1
        set_args = stage.next._run_op.call_args[0][0]
        assert isinstance(set_args, pipeline_ops_iothub.SetAuthProviderArgs)

    @pytest.mark.it(
        "sets the device_id, and hostname attributes on SetAuthProviderArgs based on the same-names auth_provider attributes"
    )
    def test_sets_required_attributes(self, mocker, stage, set_auth_provider_required_args_only):
        stage.next._run_op = mocker.Mock()
        stage.run_op(set_auth_provider_required_args_only)
        set_args = stage.next._run_op.call_args[0][0]
        assert set_args.device_id == fake_device_id
        assert set_args.hostname == fake_hostname

    @pytest.mark.it(
        "sets the gateway_hostname, ca_cert, and module_id attributes to None if they don't exist on the auth_provider object"
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
        "sets the module_id, gateway_hostname and ca_cert attributes on SetAuthProviderArgs if they exist on the auth_provider object"
    )
    def test_sets_optional_attributes(self, mocker, stage, set_auth_provider_all_args):
        stage.next._run_op = mocker.Mock()
        stage.run_op(set_auth_provider_all_args)
        set_args = stage.next._run_op.call_args[0][0]
        assert set_args.gateway_hostname == fake_gateway_hostname
        assert set_args.ca_cert == fake_ca_cert
        assert set_args.module_id == fake_module_id

    @pytest.mark.it(
        "handles any Exceptions raised by SetAuthProviderArgs and returns them through the op callback"
    )
    def test_set_auth_provider_raises_exception(
        self, mocker, stage, fake_exception, set_auth_provider
    ):
        stage.next._run_op = mocker.Mock(side_effect=fake_exception)
        stage.run_op(set_auth_provider)
        assert_callback_failed(op=set_auth_provider, error=fake_exception)

    def test_set_auth_provider_raises_base_exception(
        self, mocker, stage, fake_base_exception, set_auth_provider
    ):
        stage.next._run_op = mocker.Mock(side_effect=fake_base_exception)
        with pytest.raises(UnhandledException):
            stage.run_op(set_auth_provider)

    @pytest.mark.it(
        "If the SetAuthProviderArgs op fails, _run_op does not un a SetSasToken op on the next stage"
    )
    def test_does_not_set_sas_token_on_set_auth_provider_args_failure(
        self, mocker, stage, fake_exception, set_auth_provider
    ):
        stage.next._run_op = mocker.Mock(side_effect=fake_exception)
        stage.run_op(set_auth_provider)
        assert stage.next._run_op.call_count == 1

    @pytest.mark.it(
        "If the SetAuthProviderArgs op succeeds, _run_op runs a SetSasToken op on the next stage"
    )
    def test_runs_set_sas_token(self, mocker, stage, set_auth_provider):
        def next_run_op(self, op):
            if isinstance(op, pipeline_ops_iothub.SetAuthProviderArgs):
                op.callback(op)
            else:
                pass

        stage.next._run_op = functools.partial(next_run_op, stage)
        mocker.spy(stage.next, "_run_op")
        stage.run_op(set_auth_provider)
        assert stage.next._run_op.call_count == 2
        assert isinstance(
            stage.next._run_op.call_args_list[0][0][0], pipeline_ops_iothub.SetAuthProviderArgs
        )
        assert isinstance(stage.next._run_op.call_args_list[1][0][0], pipeline_ops_base.SetSasToken)

    @pytest.mark.it(
        "calls get_current_sas_token on the auth_provider and passes the result as a SetSasToken attribute"
    )
    def test_calls_get_current_sas_token(self, stage, set_auth_provider):
        stage.run_op(set_auth_provider)
        assert set_auth_provider.auth_provider.get_current_sas_token.call_count == 1
        set_sas_token_op = stage.next._run_op.call_args_list[1][0][0]
        assert set_sas_token_op.sas_token == fake_sas_token

    @pytest.mark.it(
        "if the SetSasToken operation succeeds, _run_op calls the SetAuthProvider callback with no error"
    )
    def test_returns_success_if_set_sas_token_succeeds(self, stage, set_auth_provider):
        stage.run_op(set_auth_provider)
        assert_callback_succeeded(op=set_auth_provider)

    @pytest.mark.it(
        "handles any Exceptions raised by SetSasToken and returns them through the op callback"
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
        "if the SetSasToken operation fails, _run_op calls the SetAuthProvider callback with the SetSasToken error"
    )
    def test_returns_set_sas_token_failure(self, fake_exception, stage, set_auth_provider):
        def next_run_op(self, op):
            if isinstance(op, pipeline_ops_iothub.SetAuthProviderArgs):
                op.callback(op)
            else:
                raise fake_exception

        stage.next._run_op = functools.partial(next_run_op, stage)
        stage.run_op(set_auth_provider)
        assert_callback_failed(op=set_auth_provider, error=fake_exception)
