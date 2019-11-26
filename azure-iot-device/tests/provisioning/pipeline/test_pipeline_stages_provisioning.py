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
from azure.iot.device.exceptions import ServiceError
import json
import datetime
from azure.iot.device.provisioning.models.registration_result import (
    RegistrationResult,
    RegistrationState,
)
from azure.iot.device import exceptions


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
fake_request_id = "Request1234"
fake_operation_id = "Operation4567"
fake_status = "Flying"
fake_assigned_hub = "Dumbledore'sArmy"
fake_sub_status = "FlyingOnHippogriff"
fake_created_dttm = datetime.datetime(2020, 5, 17)
fake_last_update_dttm = datetime.datetime(2020, 10, 17)
fake_etag = "HighQualityFlyingBroom"
fake_payload = "petrificus totalus"
fake_symmetric_key = "Zm9vYmFy"
fake_x509_cert_file = "fantastic_beasts"
fake_x509_cert_key_file = "where_to_find_them"
fake_pass_phrase = "alohomora"


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


pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_provisioning.RegistrationStage,
    module=this_module,
    all_ops=all_common_ops + all_provisioning_ops,
    handled_ops=[pipeline_ops_provisioning.SendRegistrationRequestOperation],
    all_events=all_common_events,
    handled_events=[],
)


pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_provisioning.PollingStatusStage,
    module=this_module,
    all_ops=all_common_ops + all_provisioning_ops,
    handled_ops=[pipeline_ops_provisioning.SendQueryRequestOperation],
    all_events=all_common_events,
    handled_events=[],
)


def make_mock_x509_security_client():
    mock_x509 = X509(fake_x509_cert_file, fake_x509_cert_key_file, fake_pass_phrase)
    return X509SecurityClient(
        provisioning_host=fake_provisioning_host,
        registration_id=fake_registration_id,
        id_scope=fake_id_scope,
        x509=mock_x509,
    )


def make_mock_symmetric_security_client():
    return SymmetricKeySecurityClient(
        provisioning_host=fake_provisioning_host,
        registration_id=fake_registration_id,
        id_scope=fake_id_scope,
        symmetric_key=fake_symmetric_key,
    )


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
        return "\n".join([self.deviceId, self.assignedHub, self.substatus, self.payload])


def create_registration_result(status):
    state = FakeRegistrationState(payload=fake_payload)
    return FakeRegistrationResult(fake_operation_id, status, state)


def get_registration_result_as_bytes(status):
    registration_result = create_registration_result(status)
    return json.dumps(registration_result, default=lambda o: o.__dict__).encode("utf-8")


different_security_ops = [
    {
        "name": "set symmetric key security",
        "current_op_class": pipeline_ops_provisioning.SetSymmetricKeySecurityClientOperation,
        "security_client_function_name": make_mock_symmetric_security_client,
    },
    {
        "name": "set x509 security",
        "current_op_class": pipeline_ops_provisioning.SetX509SecurityClientOperation,
        "security_client_function_name": make_mock_x509_security_client,
    },
]


@pytest.mark.parametrize(
    "params_security_ops",
    different_security_ops,
    ids=[x["current_op_class"].__name__ for x in different_security_ops],
)
@pytest.mark.describe(
    "UseSecurityClientStage .run_op() -- called with SetSymmetricKeySecurityClientOperation or SetX509SecurityClientOperation operations"
)
class TestUseSecurityClientStageWithSetSecurityClientOperation(StageTestBase):
    @pytest.fixture
    def stage(self, mocker):
        stage = pipeline_stages_provisioning.UseSecurityClientStage()
        mocker.spy(stage, "send_op_down")
        return stage

    @pytest.fixture
    def set_security_client_op(self, mocker, params_security_ops):
        # Create new security client every time to pass into fixture to avoid re-use of old security client
        # Otherwise the exception/failure raised by one test is makes the next test fail.
        op = params_security_ops["current_op_class"](
            security_client=params_security_ops["security_client_function_name"](),
            callback=mocker.MagicMock(),
        )
        mocker.spy(op, "complete")
        mocker.spy(op, "spawn_worker_op")
        return op

    @pytest.mark.it("runs SetProvisioningClientConnectionArgsOperation op on the next stage")
    def test_runs_set_security_client_args(self, mocker, stage, set_security_client_op):
        set_security_client_op.spawn_worker_op = mocker.MagicMock()
        stage.next._execute_op = mocker.Mock()
        stage.run_op(set_security_client_op)

        assert set_security_client_op.spawn_worker_op.call_count == 1
        assert (
            set_security_client_op.spawn_worker_op.call_args[1]["worker_op_type"]
            is pipeline_ops_provisioning.SetProvisioningClientConnectionArgsOperation
        )
        worker = set_security_client_op.spawn_worker_op.return_value
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(worker)
        stage.next._execute_op.call_args[0][0]

    @pytest.mark.it(
        "Completes the SetSecurityClient with the SetProvisioningClientConnectionArgsOperation error"
        "when the SetProvisioningClientConnectionArgsOperation op raises an Exception"
    )
    def test_set_security_client_raises_exception(
        self, mocker, stage, arbitrary_exception, set_security_client_op
    ):
        stage.next._execute_op = mocker.Mock(side_effect=arbitrary_exception)
        stage.run_op(set_security_client_op)
        assert set_security_client_op.complete.call_count == 1
        assert set_security_client_op.complete.call_args == mocker.call(error=arbitrary_exception)

    @pytest.mark.it(
        "Retrieves sas_token or x509_client_cert on the security_client and passes the result as the attribute of the next operation"
    )
    def test_calls_get_current_sas_token_or_get_x509_certificate(
        self, mocker, stage, set_security_client_op, params_security_ops
    ):
        if (
            params_security_ops["current_op_class"].__name__
            == "SetSymmetricKeySecurityClientOperation"
        ):
            spy_method = mocker.spy(set_security_client_op.security_client, "get_current_sas_token")
        elif params_security_ops["current_op_class"].__name__ == "SetX509SecurityClientOperation":
            spy_method = mocker.spy(set_security_client_op.security_client, "get_x509_certificate")

        stage.run_op(set_security_client_op)
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
        self, mocker, stage, set_security_client_op, next_stage_succeeds
    ):
        stage.run_op(set_security_client_op)
        assert set_security_client_op.complete.call_count == 1
        assert set_security_client_op.complete.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Returns error when get_current_sas_token or get_x509_certificate raises an exception"
    )
    def test_get_current_sas_token_or_get_x509_certificate_raises_exception(
        self, mocker, arbitrary_exception, stage, set_security_client_op, params_security_ops
    ):
        if (
            params_security_ops["current_op_class"].__name__
            == "SetSymmetricKeySecurityClientOperation"
        ):
            set_security_client_op.security_client.get_current_sas_token = mocker.Mock(
                side_effect=arbitrary_exception
            )
        elif params_security_ops["current_op_class"].__name__ == "SetX509SecurityClientOperation":
            set_security_client_op.security_client.get_x509_certificate = mocker.Mock(
                side_effect=arbitrary_exception
            )
        stage.run_op(set_security_client_op)
        assert set_security_client_op.complete.call_count == 1
        assert set_security_client_op.complete.call_args == mocker.call(error=arbitrary_exception)


@pytest.mark.parametrize(
    "request_payload",
    [
        pytest.param(" ", id="empty payload"),
        # pytest.param(None, id="some payload")
    ],
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
        assert type(op.complete.call_args[1]["error"]) is ServiceError

    @pytest.mark.it(
        "Decodes, deserializes, and returns the response from RequestAndResponseOperation as the registration_result attribute on the op along with no error if the status code < 300 and if status is 'assigned'"
    )
    def test_stage_completes_with_result_when_next_stage_responds_with_status_assigned(
        self, mocker, stage, op
    ):
        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 200
            next_stage_op.response_body = get_registration_result_as_bytes("assigned")
            next_stage_op.retry_after = None
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert op.complete.call_args == mocker.call(error=None)
        # We need to assert string representations as these are inherently different objects
        assert str(op.registration_result) == str(create_registration_result("assigned"))

    @pytest.mark.it(
        "Decodes, deserializes, and returns the response from RequestAndResponseOperation as the registration_result attribute on the op along with an error if the status code < 300 and if status is 'failed'"
    )
    def test_stage_completes_with_error_if_next_stage_responds_with_status_failed(self, stage, op):
        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 200
            next_stage_op.response_body = get_registration_result_as_bytes("failed")
            next_stage_op.retry_after = None
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        # We need to assert string representations as these are different objects
        assert str(op.registration_result) == str(create_registration_result("failed"))
        # We can only assert instance other wise we need to assert the exact text
        assert isinstance(op.complete.call_args[1]["error"], exceptions.ServiceError)

    @pytest.mark.it(
        "Decodes, deserializes the response from RequestAndResponseOperation and creates another op if the status code < 300 and if status is 'assigning'"
    )
    def test_stage_spawns_another_op_if_next_stage_responds_with_status_assigning(self, stage, op):
        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 200
            next_stage_op.response_body = get_registration_result_as_bytes("assigning")
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
        self, mocker, stage, op, request_body
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
        next_op.response_body = get_registration_result_as_bytes("flying")
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
        assert type(op.complete.call_args[1]["error"]) is ServiceError

    @pytest.mark.it(
        "Decodes, deserializes, and returns the response from RequestAndResponseOperation as the registration_result attribute on the op with no error if the status code < 300 and if status is 'assigned'"
    )
    def test_stage_completes_with_result_when_next_stage_responds_with_status_assigned(
        self, mocker, stage, op
    ):
        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 200
            next_stage_op.response_body = get_registration_result_as_bytes("assigned")
            next_stage_op.retry_after = None
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert op.complete.call_args == mocker.call(error=None)
        # We need to assert string representations as these are inherently different objects
        assert str(op.registration_result) == str(create_registration_result("assigned"))

    @pytest.mark.it(
        "Decodes, deserializes, and returns the response from RequestAndResponseOperation as the registration_result attribute on the op along with an error if the status code < 300 and if status is 'failed'"
    )
    def test_stage_completes_with_error_if_next_stage_responds_with_status_failed(self, stage, op):
        def next_stage_run_op(self, next_stage_op):
            next_stage_op.status_code = 200
            next_stage_op.response_body = get_registration_result_as_bytes("failed")
            next_stage_op.retry_after = None
            next_stage_op.complete()

        stage.next.run_op = functools.partial(next_stage_run_op, (stage.next,))
        stage.run_op(op)
        assert op.complete.call_count == 1
        # We need to assert string representations as these are different objects
        assert str(op.registration_result) == str(create_registration_result("failed"))
        # We can only assert instance other wise we need to assert the exact text
        assert isinstance(op.complete.call_args[1]["error"], exceptions.ServiceError)

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
        next_op.response_body = get_registration_result_as_bytes("flying")
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
        next_op.response_body = get_registration_result_as_bytes("assigning")
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
