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
from tests.common.pipeline.helpers import (
    assert_callback_succeeded,
    assert_callback_failed,
    all_common_ops,
    all_common_events,
    all_except,
    StageTestBase,
)
from azure.iot.device import exceptions
import json


logging.basicConfig(level=logging.DEBUG)
this_module = sys.modules[__name__]
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")

fake_device_id = "elder_wand"
fake_assigned_hub = "Dumbledore'sArmy"
fake_payload = "petrificus totalus"
fake_registration_id = "registered_remembrall"
fake_operation_id = "Operation4567"
fake_sub_status = "FlyingOnHippogriff"


class FakeRegistrationResult(object):
    def __init__(self, operation_id, status, state):
        self.operationId = operation_id
        self.status = status
        self.registrationState = state

    def __str__(self):
        return "\n".join([str(self.registrationState), self.status])


class FakeRegistrationState(object):
    def __init__(self, payload):
        self.deviceId = fake_device_id
        self.assignedHub = fake_assigned_hub
        self.payload = payload
        self.substatus = fake_sub_status

    def __str__(self):
        return "\n".join(
            [self.deviceId, self.assignedHub, self.substatus, self.get_payload_string()]
        )

    def get_payload_string(self):
        return json.dumps(self.payload, default=lambda o: o.__dict__, sort_keys=True)

def create_registration_result(fake_payload, status):
    state = FakeRegistrationState(payload=fake_payload)
    return FakeRegistrationResult(fake_operation_id, status, state)


def get_registration_result_as_bytes(registration_result):
    return json.dumps(registration_result, default=lambda o: o.__dict__).encode("utf-8")

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

@pytest.mark.parametrize(
    "request_payload",
    [pytest.param(" ", id="empty payload"), pytest.param(fake_payload, id="some payload")],
)
@pytest.mark.describe(
    "RegistrationStage - .run_op() -- called with SendRegistrationRequestOperation"
)
class TestRegistrationStageWithSendRegistrationRequestOperation(StageTestBase):
    @pytest.fixture
    def stage(self):
        return pipeline_stages_provisioning.RegistrationStage()

    @pytest.fixture
    def op(self, stage, mocker, request_payload):
        op = pipeline_ops_provisioning.SendRegistrationRequestOperation(
            request_payload, fake_registration_id, callback=mocker.MagicMock()
        )
        mocker.spy(op, "complete")
        mocker.spy(op, "spawn_worker_op")
        return op

    @pytest.fixture()
    def request_body(self, request_payload):
        return '{{"payload": {json_payload}, "registrationId": "{reg_id}"}}'.format(
            reg_id=fake_registration_id, json_payload=json.dumps(request_payload)
        )

    @pytest.mark.it(
        "Runs a RequestAndResponseOperation operation on the next stage with request_type='register', method='PUT', resource_location='/', and request_body as json of payload"
    )
    def test_sends_new_operation(self, stage, op, request_body):
        stage.run_op(op)
        assert stage.next.run_op.call_count == 1
        new_op = stage.next.run_op.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.RequestAndResponseOperation)
        assert new_op.request_type == "register"
        assert new_op.method == "PUT"
        assert new_op.resource_location == "/"
        assert new_op.request_body == request_body

    @pytest.mark.it(
        "Completes the SendRegistrationRequestOperation with the failure from RequestAndResponseOperation, if the RequestAndResponseOperation completes with failure"
    )
    def test_next_stage_returns_error(self, mocker, stage, op, arbitrary_exception):
        def next_stage_run_op(self, next_stage_op):
            next_stage_op.complete(error=arbitrary_exception)

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert op.complete.call_args == mocker.call(error=arbitrary_exception)

    @pytest.mark.it(
        "Completes the SendRegistrationRequestOperation with a ServiceError if the RequestAndResponseOperation returns a status code >= 300"
    )
    def test_next_stage_returns_status_over_300(self, mocker, stage, op):
        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 400
            # next_stage_op.response_body = json.dumps("").encode("utf-8")
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert type(op.complete.call_args[1]["error"]) is exceptions.ServiceError

    @pytest.mark.it(
        "Decodes, deserializes, and returns the response from RequestAndResponseOperation as the registration_result attribute on the op along with no error if the status code < 300 and if status is 'assigned'"
    )
    def test_stage_completes_with_result_when_next_stage_responds_with_status_assigned(
        self, mocker, stage, op, request_payload
    ):
        registration_result = create_registration_result(request_payload, "assigned")

        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 200
            next_stage_op.response_body = get_registration_result_as_bytes(registration_result)
            next_stage_op.retry_after = None
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert op.complete.call_args == mocker.call(error=None)
        # We need to assert string representations as these are inherently different objects
        assert str(op.registration_result) == str(registration_result)

    @pytest.mark.it(
        "Decodes, deserializes, and returns the response from RequestAndResponseOperation as the registration_result attribute on the op along with an error if the status code < 300 and if status is 'failed'"
    )
    def test_stage_completes_with_error_if_next_stage_responds_with_failed_status_but_successful_status_code(
        self, stage, op, request_payload
    ):
        registration_result = create_registration_result(request_payload, "failed")

        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 200
            next_stage_op.response_body = get_registration_result_as_bytes(registration_result)
            next_stage_op.retry_after = None
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        # We need to assert string representations as these are different objects
        assert str(op.registration_result) == str(registration_result)
        # We can only assert instance other wise we need to assert the exact text
        assert isinstance(op.complete.call_args[1]["error"], exceptions.ServiceError)
        assert "failed registration status" in str(op.complete.call_args[1]["error"])

    @pytest.mark.it(
        "Decodes, deserializes the response from RequestAndResponseOperation and creates another op if the status code < 300 and if status is 'assigning'"
    )
    def test_stage_spawns_another_op_if_next_stage_responds_with_assigning_status_but_successful_status_code(
        self, stage, op, request_payload
    ):
        registration_result = create_registration_result(request_payload, "assigning")

        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 200
            next_stage_op.response_body = get_registration_result_as_bytes(registration_result)
            next_stage_op.retry_after = None
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.spawn_worker_op.call_count == 1
        assert (
            op.spawn_worker_op.call_args[1]["worker_op_type"]
            == pipeline_ops_provisioning.SendQueryRequestOperation
        )
        assert op.spawn_worker_op.call_args[1]["request_payload"] == " "
        assert op.spawn_worker_op.call_args[1]["operation_id"] == fake_operation_id
        assert op.spawn_worker_op.call_args[1]["callback"] is not None

    @pytest.mark.it(
        "Decodes, deserializes the response from RequestAndResponseOperation and retries the op if the status code > 429"
    )
    def test_stage_retries_op_if_next_stage_responds_with_status_code_greater_than_429(
        self, mocker, stage, op, request_body, request_payload
    ):
        mock_timer = mocker.patch(
            "azure.iot.device.provisioning.pipeline.pipeline_stages_provisioning.Timer"
        )

        stage.run_op(op)
        assert stage.next.run_op.call_count == 1
        next_op = stage.next.run_op.call_args[0][0]

        assert isinstance(next_op, pipeline_ops_base.RequestAndResponseOperation)

        next_op.status_code = 430
        next_op.retry_after = "1"
        registration_result = create_registration_result(request_payload, "assigning")
        next_op.response_body = get_registration_result_as_bytes(registration_result)
        next_op.complete()

        stage.next.run_op.reset_mock()

        timer_callback = mock_timer.call_args[0][1]
        timer_callback()

        assert stage.next.run_op.call_count == 1
        next_op_2 = stage.next.run_op.call_args[0][0]
        assert isinstance(next_op_2, pipeline_ops_base.RequestAndResponseOperation)
        assert next_op_2.request_type == "register"
        assert next_op_2.method == "PUT"
        assert next_op_2.resource_location == "/"
        assert next_op_2.request_body == request_body

    @pytest.mark.it(
        "Decodes, deserializes the response from RequestAndResponseOperation and completes the op with error if the status code < 300 and if status is unknown"
    )
    def test_stage_completes_with_error_if_next_stage_responds_with_some_unknown_status_but_successful_status_code(
        self, stage, op, request_payload
    ):
        registration_result = create_registration_result(request_payload, "quidditching")

        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 200
            next_stage_op.response_body = get_registration_result_as_bytes(registration_result)
            next_stage_op.retry_after = None
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        # We can only assert instance other wise we need to assert the exact text
        assert isinstance(op.complete.call_args[1]["error"], exceptions.ServiceError)
        assert "invalid registration status" in str(op.complete.call_args[1]["error"])


@pytest.mark.describe("PollingStatusStage - .run_op() -- called with SendQueryRequestOperation")
class TestPollingStatusStageWithSendQueryRequestOperation(StageTestBase):
    @pytest.fixture
    def stage(self):
        return pipeline_stages_provisioning.PollingStatusStage()

    @pytest.fixture
    def op(self, stage, mocker):
        op = pipeline_ops_provisioning.SendQueryRequestOperation(
            fake_operation_id, " ", callback=mocker.MagicMock()
        )
        mocker.spy(op, "complete")
        return op

    @pytest.mark.it(
        "Runs a RequestAndResponseOperation operation on the next stage with request_type='query', method='GET', resource_location='/', and blank request_body"
    )
    def test_sends_new_operation(self, stage, op):
        stage.run_op(op)
        assert stage.next.run_op.call_count == 1
        new_op = stage.next.run_op.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.RequestAndResponseOperation)
        assert new_op.request_type == "query"
        assert new_op.method == "GET"
        assert new_op.resource_location == "/"
        assert new_op.request_body == " "

    @pytest.mark.it(
        "Completes the SendQueryRequestOperation with the failure from RequestAndResponseOperation, if the RequestAndResponseOperation completes with failure"
    )
    def test_next_stage_returns_error(self, mocker, stage, op, arbitrary_exception):
        def next_stage_run_op(self, next_stage_op):
            next_stage_op.complete(error=arbitrary_exception)

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert op.complete.call_args == mocker.call(error=arbitrary_exception)

    @pytest.mark.it(
        "Completes the SendQueryRequestOperation with a ServiceError if the RequestAndResponseOperation returns a status code >= 300"
    )
    def test_next_stage_returns_status_over_300(self, mocker, stage, op):
        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 400
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert type(op.complete.call_args[1]["error"]) is exceptions.ServiceError

    @pytest.mark.it(
        "Decodes, deserializes, and returns the response from RequestAndResponseOperation as the registration_result attribute on the op with no error if the status code < 300 and if status is 'assigned'"
    )
    def test_stage_completes_with_result_when_next_stage_responds_with_status_assigned(
        self, mocker, stage, op
    ):
        registration_result = create_registration_result(" ", "assigned")

        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 200
            next_stage_op.response_body = get_registration_result_as_bytes(registration_result)
            next_stage_op.retry_after = None
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert op.complete.call_args == mocker.call(error=None)
        # We need to assert string representations as these are inherently different objects
        assert str(op.registration_result) == str(registration_result)

    @pytest.mark.it(
        "Decodes, deserializes, and returns the response from RequestAndResponseOperation as the registration_result attribute on the op along with an error if the status code < 300 and if status is 'failed'"
    )
    def test_stage_completes_with_error_if_next_stage_responds_with_status_failed(self, stage, op):
        registration_result = create_registration_result(" ", "failed")

        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 200
            next_stage_op.response_body = get_registration_result_as_bytes(registration_result)
            next_stage_op.retry_after = None
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        # We need to assert string representations as these are different objects
        assert str(op.registration_result) == str(registration_result)
        # We can only assert instance other wise we need to assert the exact text
        assert isinstance(op.complete.call_args[1]["error"], exceptions.ServiceError)
        assert "failed registration status" in str(op.complete.call_args[1]["error"])

    @pytest.mark.it(
        "Decodes, deserializes the response from RequestAndResponseOperation and retries the op if the status code > 429"
    )
    def test_stage_retries_op_if_next_stage_responds_with_status_code_greater_than_429(
        self, mocker, stage, op
    ):
        mock_timer = mocker.patch(
            "azure.iot.device.provisioning.pipeline.pipeline_stages_provisioning.Timer"
        )

        stage.run_op(op)
        assert stage.next.run_op.call_count == 1
        next_op = stage.next.run_op.call_args[0][0]

        assert isinstance(next_op, pipeline_ops_base.RequestAndResponseOperation)

        next_op.status_code = 430
        next_op.retry_after = "1"
        registration_result = create_registration_result(" ", "flying")
        next_op.response_body = get_registration_result_as_bytes(registration_result)
        next_op.complete()

        stage.next.run_op.reset_mock()

        timer_callback = mock_timer.call_args[0][1]
        timer_callback()

        assert stage.next.run_op.call_count == 1
        next_op_2 = stage.next.run_op.call_args[0][0]
        assert isinstance(next_op_2, pipeline_ops_base.RequestAndResponseOperation)
        assert next_op_2.request_type == "query"
        assert next_op_2.method == "GET"
        assert next_op_2.resource_location == "/"
        assert next_op_2.request_body == " "

    @pytest.mark.it(
        "Decodes, deserializes the response from RequestAndResponseOperation and retries the op if the status code < 300 and if status is 'assigning'"
    )
    def test_stage_retries_op_if_next_stage_responds_with_status_assigning(self, mocker, stage, op):
        mock_timer = mocker.patch(
            "azure.iot.device.provisioning.pipeline.pipeline_stages_provisioning.Timer"
        )

        stage.run_op(op)
        assert stage.next.run_op.call_count == 1
        next_op = stage.next.run_op.call_args[0][0]

        assert isinstance(next_op, pipeline_ops_base.RequestAndResponseOperation)

        next_op.status_code = 250
        next_op.retry_after = "1"
        registration_result = create_registration_result(" ", "assigning")
        next_op.response_body = get_registration_result_as_bytes(registration_result)
        next_op.complete()

        stage.next.run_op.reset_mock()

        timer_callback = mock_timer.call_args[0][1]
        timer_callback()

        assert stage.next.run_op.call_count == 1
        next_op_2 = stage.next.run_op.call_args[0][0]
        assert isinstance(next_op_2, pipeline_ops_base.RequestAndResponseOperation)
        assert next_op_2.request_type == "query"
        assert next_op_2.method == "GET"
        assert next_op_2.resource_location == "/"
        assert next_op_2.request_body == " "

    @pytest.mark.it(
        "Decodes, deserializes the response from RequestAndResponseOperation and completes the op with error if the status code < 300 and if status is unknown"
    )
    def test_stage_completes_with_error_if_next_stage_responds_with_some_unknown_status_but_successful_status_code(
        self, stage, op
    ):
        registration_result = create_registration_result(" ", "quidditching")

        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 200
            next_stage_op.response_body = get_registration_result_as_bytes(registration_result)
            next_stage_op.retry_after = None
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        # We can only assert instance other wise we need to assert the exact text
        assert isinstance(op.complete.call_args[1]["error"], exceptions.ServiceError)
        assert "invalid registration status" in str(op.complete.call_args[1]["error"])
