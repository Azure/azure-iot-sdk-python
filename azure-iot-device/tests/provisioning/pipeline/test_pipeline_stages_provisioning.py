# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import functools
import sys
from azure.iot.device.common.models.x509 import X509
from azure.iot.device.provisioning.security.sk_security_client import SymmetricKeySecurityClient
from azure.iot.device.provisioning.security.x509_security_client import X509SecurityClient
from azure.iot.device.provisioning.pipeline import (
    pipeline_stages_provisioning,
    pipeline_ops_provisioning,
)
from azure.iot.device.common.pipeline import pipeline_ops_base

from tests.common.pipeline.helpers import (
    assert_callback_succeeded,
    assert_callback_failed,
    all_common_ops,
    all_common_events,
    all_except,
    make_mock_stage,
    UnhandledException,
)
from azure.iot.device.common.pipeline import pipeline_events_base
from tests.provisioning.pipeline.helpers import all_provisioning_ops, all_provisioning_events
from tests.common.pipeline import pipeline_stage_test

logging.basicConfig(level=logging.INFO)

this_module = sys.modules[__name__]


# Make it look like we're always running inside pipeline threads
@pytest.fixture(autouse=True)
def apply_fake_pipeline_thread(fake_pipeline_thread):
    pass


fake_device_id = "elder_wand"
fake_registration_id = "registered_remembrall"
fake_provisioning_host = "hogwarts.com"
fake_id_scope = "weasley_wizard_wheezes"
fake_ca_cert = "fake_certificate"
fake_sas_token = "horcrux_token"


pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_provisioning.UseSecurityClientStage,
    module=this_module,
    all_ops=all_common_ops + all_provisioning_ops,
    handled_ops=[
        pipeline_ops_provisioning.SetSymmetricKeySecurityClientOperation,
        pipeline_ops_provisioning.SetX509SecurityClientOperation,
    ],
    all_events=all_common_events + all_provisioning_events,
    handled_events=[],
)


fake_symmetric_key = "Zm9vYmFy"
fake_x509_cert_file = "fantastic_beasts"
fake_x509_cert_key_file = "where_to_find_them"
fake_pass_phrase = "alohomora"


def create_x509_security_client():
    mock_x509 = X509(fake_x509_cert_file, fake_x509_cert_key_file, fake_pass_phrase)
    return X509SecurityClient(
        provisioning_host=fake_provisioning_host,
        registration_id=fake_registration_id,
        id_scope=fake_id_scope,
        x509=mock_x509,
    )


def create_symmetric_security_client():
    return SymmetricKeySecurityClient(
        provisioning_host=fake_provisioning_host,
        registration_id=fake_registration_id,
        id_scope=fake_id_scope,
        symmetric_key=fake_symmetric_key,
    )


different_security_ops = [
    {
        "name": "set symmetric key security",
        "current_op_class": pipeline_ops_provisioning.SetSymmetricKeySecurityClientOperation,
        "security_client_function_name": create_symmetric_security_client,
        "next_op_class": pipeline_ops_base.SetSasTokenOperation,
    },
    {
        "name": "set x509 security",
        "current_op_class": pipeline_ops_provisioning.SetX509SecurityClientOperation,
        "security_client_function_name": create_x509_security_client,
        "next_op_class": pipeline_ops_base.SetClientAuthenticationCertificateOperation,
    },
]


@pytest.fixture
def security_stage(mocker):
    return make_mock_stage(mocker, pipeline_stages_provisioning.UseSecurityClientStage)


@pytest.fixture
def set_security_client(callback, params_security_ops):
    # Create new security client every time to pass into fixture to avoid re-use of old security client
    # Otherwise the exception/failure raised by one test is makes the next test fail.
    op = params_security_ops["current_op_class"](
        security_client=params_security_ops["security_client_function_name"]()
    )
    op.callback = callback
    return op


@pytest.mark.parametrize(
    "params_security_ops",
    different_security_ops,
    ids=[
        "{}->{}".format(x["current_op_class"].__name__, x["next_op_class"].__name__)
        for x in different_security_ops
    ],
)
@pytest.mark.describe(
    "UseSecurityClientStage run_op function with SetSecurityClientArgsOperation operations"
)
class TestUseSymmetricKeyOrX509SecurityClientRunOpWithSetSecurityClient(object):
    @pytest.mark.it("runs SetSecurityClientArgsOperation op on the next stage")
    def test_runs_set_security_client_args(self, mocker, security_stage, set_security_client):
        security_stage.next._run_op = mocker.Mock()
        security_stage.run_op(set_security_client)
        assert security_stage.next._run_op.call_count == 1
        set_args = security_stage.next._run_op.call_args[0][0]
        assert isinstance(set_args, pipeline_ops_provisioning.SetSecurityClientArgsOperation)

    @pytest.mark.it(
        "Calls the SetSecurityClient callback with the SetSecurityClientArgsOperation error"
        "when the SetSecurityClientArgsOperation op raises an Exception"
    )
    def test_set_security_client_raises_exception(
        self, mocker, security_stage, fake_exception, set_security_client
    ):
        security_stage.next._run_op = mocker.Mock(side_effect=fake_exception)
        security_stage.run_op(set_security_client)
        assert_callback_failed(op=set_security_client, error=fake_exception)

    @pytest.mark.it(
        "Allows any BaseExceptions raised by SetSecurityClientArgsOperation operations to propagate"
    )
    def test_set_security_client_raises_base_exception(
        self, mocker, security_stage, fake_base_exception, set_security_client
    ):
        security_stage.next._run_op = mocker.Mock(side_effect=fake_base_exception)
        with pytest.raises(UnhandledException):
            security_stage.run_op(set_security_client)

    @pytest.mark.it(
        "Does not run a SetSasToken or a SetClientAuthenticationCertificate op on the next stage when the SetSecurityClientArgs op fails"
    )
    def test_does_not_set_sas_token_or_set_certificate_after_set_security_client_args_failure(
        self, mocker, security_stage, fake_exception, set_security_client
    ):
        security_stage.next._run_op = mocker.Mock(side_effect=fake_exception)
        security_stage.run_op(set_security_client)
        assert security_stage.next._run_op.call_count == 1

    @pytest.mark.it(
        "Runs the next operation of setting token or certificate on the next stage when the SetSecurityClientArgsOperation op succeeds"
    )
    def test_runs_set_sas_token_or_set_client_certificate(
        self, mocker, security_stage, set_security_client, params_security_ops
    ):
        def next_run_op(self, op):
            if isinstance(op, pipeline_ops_provisioning.SetSecurityClientArgsOperation):
                op.callback(op)
            else:
                pass

        security_stage.next._run_op = functools.partial(next_run_op, security_stage)
        mocker.spy(security_stage.next, "_run_op")
        security_stage.run_op(set_security_client)
        assert security_stage.next._run_op.call_count == 2
        assert isinstance(
            security_stage.next._run_op.call_args_list[0][0][0],
            pipeline_ops_provisioning.SetSecurityClientArgsOperation,
        )
        assert isinstance(
            security_stage.next._run_op.call_args_list[1][0][0],
            params_security_ops["next_op_class"],
        )

    @pytest.mark.it(
        "Retrieves sas_token or x509_certificate on the security_client and passes the result as the attribute of the next operation"
    )
    def test_calls_get_current_sas_token_or_get_x509_certificate(
        self, mocker, security_stage, set_security_client, params_security_ops
    ):
        if (
            params_security_ops["current_op_class"].__name__
            == "SetSymmetricKeySecurityClientOperation"
        ):
            spy_method = mocker.spy(set_security_client.security_client, "get_current_sas_token")
        elif params_security_ops["current_op_class"].__name__ == "SetX509SecurityClientOperation":
            spy_method = mocker.spy(set_security_client.security_client, "get_x509_certificate")

        security_stage.run_op(set_security_client)
        assert spy_method.call_count == 1

        if params_security_ops["next_op_class"].__name__ == "SetSasToken":
            set_sas_token_op = security_stage.next._run_op.call_args_list[1][0][0]
            assert "SharedAccessSignature" in set_sas_token_op.sas_token
            assert "skn=registration" in set_sas_token_op.sas_token
            assert fake_id_scope in set_sas_token_op.sas_token
            assert fake_registration_id in set_sas_token_op.sas_token

        elif params_security_ops["next_op_class"].__name__ == "SetClientAuthenticationCertificate":
            set_cert_op = security_stage.next._run_op.call_args_list[1][0][0]
            assert set_cert_op.certificate.certificate_file == fake_x509_cert_file
            assert set_cert_op.certificate.key_file == fake_x509_cert_key_file
            assert set_cert_op.certificate.pass_phrase == fake_pass_phrase

    @pytest.mark.it(
        "Calls the callback of setting security client with no error when the next operation of "
        "etting token or setting certificate operation succeeds"
    )
    def test_returns_success_if_set_sas_token_or_set_client_certificate_succeeds(
        self, security_stage, set_security_client
    ):
        security_stage.run_op(set_security_client)
        assert_callback_succeeded(op=set_security_client)

    @pytest.mark.it(
        "Returns error when get_current_sas_token or get_x509_certificate raises an exception"
    )
    def test_get_current_sas_token_or_get_x509_certificate_raises_exception(
        self, mocker, fake_exception, security_stage, set_security_client, params_security_ops
    ):
        if (
            params_security_ops["current_op_class"].__name__
            == "SetSymmetricKeySecurityClientOperation"
        ):
            set_security_client.security_client.get_current_sas_token = mocker.Mock(
                side_effect=fake_exception
            )
        elif params_security_ops["current_op_class"].__name__ == "SetX509SecurityClientOperation":
            set_security_client.security_client.get_x509_certificate = mocker.Mock(
                side_effect=fake_exception
            )
        security_stage.run_op(set_security_client)
        assert_callback_failed(op=set_security_client, error=fake_exception)

    @pytest.mark.it(
        "Allows any BaseExceptions raised by get_current_sas_token or get_x509_certificate to propagate"
    )
    def test_get_current_sas_token_get_x509_certificate_raises_base_exception(
        self, mocker, fake_base_exception, security_stage, set_security_client, params_security_ops
    ):
        if (
            params_security_ops["current_op_class"].__name__
            == "SetSymmetricKeySecurityClientOperation"
        ):
            set_security_client.security_client.get_current_sas_token = mocker.Mock(
                side_effect=fake_base_exception
            )
        elif params_security_ops["current_op_class"].__name__ == "SetX509SecurityClientOperation":
            set_security_client.security_client.get_x509_certificate = mocker.Mock(
                side_effect=fake_base_exception
            )
        with pytest.raises(UnhandledException):
            security_stage.run_op(set_security_client)

    @pytest.mark.it(
        "Calls the callback of the current operation with the next operation error when the next operation fails"
    )
    def test_returns_set_sas_token_failure(
        self, fake_exception, security_stage, set_security_client
    ):
        def next_run_op(self, op):
            if isinstance(op, pipeline_ops_provisioning.SetSecurityClientArgsOperation):
                op.callback(op)
            else:
                raise fake_exception

        security_stage.next._run_op = functools.partial(next_run_op, security_stage)
        security_stage.run_op(set_security_client)
        assert_callback_failed(op=set_security_client, error=fake_exception)
