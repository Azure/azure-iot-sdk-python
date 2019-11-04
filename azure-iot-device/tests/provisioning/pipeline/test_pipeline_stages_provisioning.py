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
    StageTestBase,
)
from azure.iot.device.common.pipeline import pipeline_events_base
from tests.provisioning.pipeline.helpers import all_provisioning_ops
from tests.common.pipeline import pipeline_stage_test

logging.basicConfig(level=logging.DEBUG)

this_module = sys.modules[__name__]


# Make it look like we're always running inside pipeline threads
@pytest.fixture(autouse=True)
def apply_fake_pipeline_thread(fake_pipeline_thread):
    pass


fake_device_id = "elder_wand"
fake_registration_id = "registered_remembrall"
fake_provisioning_host = "hogwarts.com"
fake_id_scope = "weasley_wizard_wheezes"
fake_ca_cert = "fake_ca_cert"
fake_sas_token = "horcrux_token"


pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_provisioning.UseSecurityClientStage,
    module=this_module,
    all_ops=all_common_ops + all_provisioning_ops,
    handled_ops=[
        pipeline_ops_provisioning.SetSymmetricKeySecurityClientOperation,
        pipeline_ops_provisioning.SetX509SecurityClientOperation,
    ],
    all_events=all_common_events,
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
    },
    {
        "name": "set x509 security",
        "current_op_class": pipeline_ops_provisioning.SetX509SecurityClientOperation,
        "security_client_function_name": create_x509_security_client,
    },
]


@pytest.fixture
def set_security_client(mocker, params_security_ops):
    # Create new security client every time to pass into fixture to avoid re-use of old security client
    # Otherwise the exception/failure raised by one test is makes the next test fail.
    op = params_security_ops["current_op_class"](
        security_client=params_security_ops["security_client_function_name"](),
        callback=mocker.MagicMock(),
    )
    mocker.spy(op, "complete")
    return op


@pytest.mark.parametrize(
    "params_security_ops",
    different_security_ops,
    ids=[x["current_op_class"].__name__ for x in different_security_ops],
)
@pytest.mark.describe(
    "UseSecurityClientStage run_op function with SetProvisioningClientConnectionArgsOperation operations"
)
class TestUseSymmetricKeyOrX509SecurityClientRunOpWithSetSecurityClient(StageTestBase):
    @pytest.fixture
    def stage(self):
        return pipeline_stages_provisioning.UseSecurityClientStage()

    # @pytest.mark.it("Spawns a SetProvisioningClientConnectionArgsOperation worker operation, using values from the security client")
    # def test_worker_op_creation(self, mocker, stage, set_security_client):
    #     security_client = set_security_client.security_client

    #     stage.run_op(set_security_client)

    #     assert set_security_client.spawn_worker_op.call_count == 1
    #     assert set_security_client.spawn_worker_op.call_args == mocker.call(
    #         worker_op_type=pipeline_ops_provisioning.SetProvisioningClientConnectionArgsOperation,
    #         provisioning_host=security_client.provisioning_host,
    #         registration_id=security_client.registration_id,
    #         id_scope=security_client.id_scope,
    #         sas_token=security_client.get_current_sas_token()
    #     )

    @pytest.mark.it("runs SetProvisioningClientConnectionArgsOperation op on the next stage")
    def test_runs_set_security_client_args(self, mocker, stage, set_security_client):
        stage.next._execute_op = mocker.Mock()
        stage.run_op(set_security_client)
        assert stage.next._execute_op.call_count == 1
        set_args = stage.next._execute_op.call_args[0][0]
        assert isinstance(
            set_args, pipeline_ops_provisioning.SetProvisioningClientConnectionArgsOperation
        )

    @pytest.mark.it(
        "Completes the SetSecurityClient with the SetProvisioningClientConnectionArgsOperation error"
        "when the SetProvisioningClientConnectionArgsOperation op raises an Exception"
    )
    def test_set_security_client_raises_exception(
        self, mocker, stage, arbitrary_exception, set_security_client
    ):
        stage.next._execute_op = mocker.Mock(side_effect=arbitrary_exception)
        stage.run_op(set_security_client)
        assert set_security_client.complete.call_count == 1
        assert set_security_client.complete.call_args == mocker.call(error=arbitrary_exception)

    @pytest.mark.it(
        "Retrieves sas_token or x509_client_cert on the security_client and passes the result as the attribute of the next operation"
    )
    def test_calls_get_current_sas_token_or_get_x509_certificate(
        self, mocker, stage, set_security_client, params_security_ops
    ):
        if (
            params_security_ops["current_op_class"].__name__
            == "SetSymmetricKeySecurityClientOperation"
        ):
            spy_method = mocker.spy(set_security_client.security_client, "get_current_sas_token")
        elif params_security_ops["current_op_class"].__name__ == "SetX509SecurityClientOperation":
            spy_method = mocker.spy(set_security_client.security_client, "get_x509_certificate")

        stage.run_op(set_security_client)
        assert spy_method.call_count == 1

        set_connection_args_op = stage.next._execute_op.call_args[0][0]

        if (
            params_security_ops["current_op_class"].__name__
            == "SetSymmetricKeySecurityClientOperation"
        ):
            assert "SharedAccessSignature" in set_connection_args_op.sas_token
            assert "skn=registration" in set_connection_args_op.sas_token
            assert fake_id_scope in set_connection_args_op.sas_token
            assert fake_registration_id in set_connection_args_op.sas_token

        elif params_security_ops["current_op_class"].__name__ == "SetX509SecurityClientOperation":
            assert set_connection_args_op.client_cert.certificate_file == fake_x509_cert_file
            assert set_connection_args_op.client_cert.key_file == fake_x509_cert_key_file
            assert set_connection_args_op.client_cert.pass_phrase == fake_pass_phrase

    @pytest.mark.it(
        "Completes the setting security client with no error when the next operation of "
        "setting token or setting client_cert operation succeeds"
    )
    def test_returns_success_if_set_sas_token_or_set_client_client_cert_succeeds(
        self, mocker, stage, set_security_client, next_stage_succeeds
    ):
        stage.run_op(set_security_client)
        assert set_security_client.complete.call_count == 1
        assert set_security_client.complete.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Returns error when get_current_sas_token or get_x509_certificate raises an exception"
    )
    def test_get_current_sas_token_or_get_x509_certificate_raises_exception(
        self, mocker, arbitrary_exception, stage, set_security_client, params_security_ops
    ):
        if (
            params_security_ops["current_op_class"].__name__
            == "SetSymmetricKeySecurityClientOperation"
        ):
            set_security_client.security_client.get_current_sas_token = mocker.Mock(
                side_effect=arbitrary_exception
            )
        elif params_security_ops["current_op_class"].__name__ == "SetX509SecurityClientOperation":
            set_security_client.security_client.get_x509_certificate = mocker.Mock(
                side_effect=arbitrary_exception
            )
        stage.run_op(set_security_client)
        assert set_security_client.complete.call_count == 1
        assert set_security_client.complete.call_args == mocker.call(error=arbitrary_exception)
