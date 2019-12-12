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
from tests.common.pipeline.helpers import StageRunOpTestBase
from azure.iot.device.common.pipeline import pipeline_events_base
from tests.common.pipeline import pipeline_stage_test

logging.basicConfig(level=logging.DEBUG)
this_module = sys.modules[__name__]
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")

###################
# COMMON FIXTURES #
###################


@pytest.fixture(params=[True, False], ids=["With error", "No error"])
def op_error(request, arbitrary_exception):
    if request.param:
        return arbitrary_exception
    else:
        return None


#############################
# USE SECURITY CLIENT STAGE #
#############################


class UseSecurityClientStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_provisioning.UseSecurityClientStage

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
    stage_class_under_test=pipeline_stages_provisioning.UseSecurityClientStage,
    stage_test_config_class=UseSecurityClientStageTestConfig,
)


@pytest.mark.describe(
    "UseSecurityClientStage - .run_op() -- Called with SetSymmetricKeySecurityClientOperation"
)
class TestUseSecurityClientStageRunOpWithSetSymmetricKeySecurityClientOperation(
    StageRunOpTestBase, UseSecurityClientStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        security_client = SymmetricKeySecurityClient(
            provisioning_host="hogwarts.com",
            registration_id="registered_remembrall",
            id_scope="weasley_wizard_wheezes",
            symmetric_key="Zm9vYmFy",
        )
        security_client.get_current_sas_token = mocker.MagicMock()
        return pipeline_ops_provisioning.SetSymmetricKeySecurityClientOperation(
            security_client=security_client, callback=mocker.MagicMock()
        )

    @pytest.mark.it(
        "Sends a new SetProvisioningClientConnectionArgsOperation op down the pipeline, containing connection info from the op's security client"
    )
    def test_send_new_op_down(self, mocker, op, stage):
        stage.run_op(op)

        # A SetProvisioningClientConnectionArgsOperation has been sent down the pipeline
        stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(
            new_op, pipeline_ops_provisioning.SetProvisioningClientConnectionArgsOperation
        )

        # The SetProvisioningClientConnectionArgsOperation has details from the security client
        assert new_op.provisioning_host == op.security_client.provisioning_host
        assert new_op.registration_id == op.security_client.registration_id
        assert new_op.id_scope == op.security_client.id_scope
        assert new_op.sas_token == op.security_client.get_current_sas_token.return_value
        assert new_op.client_cert is None

    @pytest.mark.it(
        "Completes the original SetSymmetricKeySecurityClientOperation with the same status as the new SetProvisioningClientConnectionArgsOperation, if the new  SetProvisioningClientConnectionArgsOperation is completed"
    )
    def test_new_op_completes_success(self, mocker, op, stage, op_error):
        stage.run_op(op)
        stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(
            new_op, pipeline_ops_provisioning.SetProvisioningClientConnectionArgsOperation
        )

        assert not op.completed
        assert not new_op.completed

        new_op.complete(error=op_error)

        assert new_op.completed
        assert new_op.error is op_error
        assert op.completed
        assert op.error is op_error


@pytest.mark.describe(
    "UseSecurityClientStage - .run_op() -- Called with SetX509SecurityClientOperation"
)
class TestUseSecurityClientStageRunOpWithSetX509SecurityClientOperation(
    StageRunOpTestBase, UseSecurityClientStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        x509 = X509(cert_file="fake_cert.txt", key_file="fake_key.txt", pass_phrase="alohomora")
        security_client = X509SecurityClient(
            provisioning_host="hogwarts.com",
            registration_id="registered_remembrall",
            id_scope="weasley_wizard_wheezes",
            x509=x509,
        )
        security_client.get_x509_certificate = mocker.MagicMock()
        return pipeline_ops_provisioning.SetX509SecurityClientOperation(
            security_client=security_client, callback=mocker.MagicMock()
        )

    @pytest.mark.it(
        "Sends a new SetProvisioningClientConnectionArgsOperation op down the pipeline, containing connection info from the op's security client"
    )
    def test_send_new_op_down(self, mocker, op, stage):
        stage.run_op(op)

        # A SetProvisioningClientConnectionArgsOperation has been sent down the pipeline
        stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(
            new_op, pipeline_ops_provisioning.SetProvisioningClientConnectionArgsOperation
        )

        # The SetProvisioningClientConnectionArgsOperation has details from the security client
        assert new_op.provisioning_host == op.security_client.provisioning_host
        assert new_op.registration_id == op.security_client.registration_id
        assert new_op.id_scope == op.security_client.id_scope
        assert new_op.client_cert == op.security_client.get_x509_certificate.return_value
        assert new_op.sas_token is None

    @pytest.mark.it(
        "Completes the original SetX509SecurityClientOperation with the same status as the new SetProvisioningClientConnectionArgsOperation, if the new  SetProvisioningClientConnectionArgsOperation is completed"
    )
    def test_new_op_completes_success(self, mocker, op, stage, op_error):
        stage.run_op(op)
        stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(
            new_op, pipeline_ops_provisioning.SetProvisioningClientConnectionArgsOperation
        )

        assert not op.completed
        assert not new_op.completed

        new_op.complete(error=op_error)

        assert new_op.completed
        assert new_op.error is op_error
        assert op.completed
        assert op.error is op_error
