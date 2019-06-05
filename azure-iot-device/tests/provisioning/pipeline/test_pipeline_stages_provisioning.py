# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import functools
from azure.iot.device.provisioning.security.sk_security_client import SymmetricKeySecurityClient
from azure.iot.device.provisioning.pipeline import (
    pipeline_stages_provisioning,
    pipeline_ops_provisioning,
)
from azure.iot.device.common.pipeline import pipeline_ops_base

from tests.common.pipeline_test import (
    assert_default_stage_attributes,
    assert_callback_succeeded,
    assert_callback_failed,
    all_common_ops,
    all_except,
    make_mock_stage,
    UnhandledException,
)
from tests.common import pipeline_test
from azure.iot.device.common.pipeline import pipeline_events_base
from tests.provisioning.pipeline_test import all_provisioning_ops

logging.basicConfig(level=logging.INFO)

fake_device_id = "elder_wand"
fake_registration_id = "registered_remembrall"
fake_provisioning_host = "hogwarts.com"
fake_id_scope = "weasley_wizard_wheezes"
fake_ca_cert = "fake_certificate"
fake_sas_token = "horcrux_token"


@pytest.fixture
def mock_stage(mocker):
    return make_mock_stage(mocker, pipeline_stages_provisioning.UseSymmetricKeySecurityClient)


def mock_symmetric_security_client(mocker):
    class MockSymmetricKeySecurityClient(SymmetricKeySecurityClient):
        def provisioning_host(self):
            return fake_provisioning_host

        def id_scope(self):
            return fake_id_scope

        def registration_id(self):
            return fake_registration_id

    security_client = MockSymmetricKeySecurityClient(
        fake_provisioning_host, fake_registration_id, fake_sas_token, fake_id_scope
    )
    security_client.get_current_sas_token = mocker.Mock(return_value=fake_sas_token)
    return security_client


@pytest.fixture
def set_security_client(mocker, callback):
    op = pipeline_ops_provisioning.SetSymmetricKeySecurityClient(
        security_client=mock_symmetric_security_client(mocker)
    )
    op.callback = callback
    return op


@pytest.mark.describe("UseSymmetricKeySecurityClient initializer")
class TestUseSymmetricKeySecurityClientInitializer(object):
    @pytest.mark.it("Sets name, next, previous and pipeline root attributes on instantiation")
    def test_initializer(self):
        obj = pipeline_stages_provisioning.UseSymmetricKeySecurityClient()
        assert_default_stage_attributes(obj)


unknown_ops = all_except(
    all_items=(all_common_ops + all_provisioning_ops),
    items_to_exclude=[pipeline_ops_provisioning.SetSymmetricKeySecurityClient],
)


@pytest.mark.describe("UseSymmetricKeySecurityClient run_op function with unhandled operations")
class TestUseSymmetricKeySecurityClientRunOpWithUnknownOperation(object):
    @pytest.mark.parametrize(
        "op_init,op_init_args", unknown_ops, ids=[x[0].__name__ for x in unknown_ops]
    )
    @pytest.mark.it("passes unknown operations to the next stage")
    def test_passes_unknown_op_down(self, mocker, mock_stage, op_init, op_init_args):
        print(op_init)
        print(op_init_args)
        op = op_init(*op_init_args)
        op.action = "pend"
        mock_stage.run_op(op)
        assert mock_stage.next._run_op.call_count == 1
        assert mock_stage.next._run_op.call_args == mocker.call(op)


@pytest.mark.describe(
    "UseSymmetricKeySecurityClient run_op function with SetSymmetricKeySecurityClientArgs operations"
)
class TestUseSymmetricKeySecurityClientRunOpWithSetSymmetricKeySecurityClient(object):
    @pytest.mark.it("runs SetSymmetricKeySecurityClientArgs op on the next stage")
    def test_runs_set_symmetric_security_client_args(self, mocker, mock_stage, set_security_client):
        mock_stage.next._run_op = mocker.Mock()
        mock_stage.run_op(set_security_client)
        assert mock_stage.next._run_op.call_count == 1
        set_args = mock_stage.next._run_op.call_args[0][0]
        assert isinstance(set_args, pipeline_ops_provisioning.SetSymmetricKeySecurityClientArgs)

    @pytest.mark.it(
        "calls the SetSymmetricKeySecurityClient callback with the SetSymmetricKeySecurityClientArgs error"
        "when the SetSymmetricKeySecurityClientArgs op raises an Exception"
    )
    def test_set_security_client_raises_exception(
        self, mocker, mock_stage, fake_exception, set_security_client
    ):
        mock_stage.next._run_op = mocker.Mock(side_effect=fake_exception)
        mock_stage.run_op(set_security_client)
        assert_callback_failed(op=set_security_client, error=fake_exception)

    @pytest.mark.it(
        "Allows any BaseExceptions raised by SetSymmetricKeySecurityClientArgs operations to propagate"
    )
    def test_set_security_client_raises_base_exception(
        self, mocker, mock_stage, fake_base_exception, set_security_client
    ):
        mock_stage.next._run_op = mocker.Mock(side_effect=fake_base_exception)
        with pytest.raises(UnhandledException):
            mock_stage.run_op(set_security_client)

    @pytest.mark.it(
        "does not run a SetSasToken op on the next stage when the SetSymmetricKeySecurityClientArgs op fails"
    )
    def test_does_not_set_sas_token_on_set_security_client_args_failure(
        self, mocker, mock_stage, fake_exception, set_security_client
    ):
        mock_stage.next._run_op = mocker.Mock(side_effect=fake_exception)
        mock_stage.run_op(set_security_client)
        assert mock_stage.next._run_op.call_count == 1

    @pytest.mark.it(
        "runs a SetSasToken op on the next stage when the SetSymmetricKeySecurityClientArgs op succeeds"
    )
    def test_runs_set_sas_token(self, mocker, mock_stage, set_security_client):
        def next_run_op(self, op):
            if isinstance(op, pipeline_ops_provisioning.SetSymmetricKeySecurityClientArgs):
                op.callback(op)
            else:
                pass

        mock_stage.next._run_op = functools.partial(next_run_op, mock_stage)
        mocker.spy(mock_stage.next, "_run_op")
        mock_stage.run_op(set_security_client)
        assert mock_stage.next._run_op.call_count == 2
        assert isinstance(
            mock_stage.next._run_op.call_args_list[0][0][0],
            pipeline_ops_provisioning.SetSymmetricKeySecurityClientArgs,
        )
        assert isinstance(
            mock_stage.next._run_op.call_args_list[1][0][0], pipeline_ops_base.SetSasToken
        )

    @pytest.mark.it(
        "calls get_current_sas_token on the security_client and passes the result as a SetSasToken attribute"
    )
    def test_calls_get_current_sas_token(self, mock_stage, set_security_client):
        mock_stage.run_op(set_security_client)
        assert set_security_client.security_client.get_current_sas_token.call_count == 1
        set_sas_token_op = mock_stage.next._run_op.call_args_list[1][0][0]
        assert set_sas_token_op.sas_token == fake_sas_token

    @pytest.mark.it(
        "calls the SetSymmetricKeySecurityClient callback with no error when the SetSasToken operation succeeds"
    )
    def test_returns_success_if_set_sas_token_succeeds(self, mock_stage, set_security_client):
        mock_stage.run_op(set_security_client)
        assert_callback_succeeded(op=set_security_client)

    @pytest.mark.it("returns error when get_current_sas_token raises an exception")
    def test_get_current_sas_token_raises_exception(
        self, mocker, fake_exception, mock_stage, set_security_client
    ):
        set_security_client.security_client.get_current_sas_token = mocker.Mock(
            side_effect=fake_exception
        )
        mock_stage.run_op(set_security_client)
        assert_callback_failed(op=set_security_client, error=fake_exception)

    @pytest.mark.it("Allows any BaseExceptions raised by get_current_sas_token to propagate")
    def test_get_current_sas_token_raises_base_exception(
        self, mocker, fake_base_exception, mock_stage, set_security_client
    ):
        set_security_client.security_client.get_current_sas_token = mocker.Mock(
            side_effect=fake_base_exception
        )
        with pytest.raises(UnhandledException):
            mock_stage.run_op(set_security_client)

    @pytest.mark.it(
        "calls the SetSymmetricKeySecurityClient callback with the SetSasToken error when the SetSasToken operation fails"
    )
    def test_returns_set_sas_token_failure(self, fake_exception, mock_stage, set_security_client):
        def next_run_op(self, op):
            if isinstance(op, pipeline_ops_provisioning.SetSymmetricKeySecurityClientArgs):
                op.callback(op)
            else:
                raise fake_exception

        mock_stage.next._run_op = functools.partial(next_run_op, mock_stage)
        mock_stage.run_op(set_security_client)
        assert_callback_failed(op=set_security_client, error=fake_exception)
