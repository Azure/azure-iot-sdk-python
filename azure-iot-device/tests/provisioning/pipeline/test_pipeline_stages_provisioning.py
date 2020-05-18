# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import sys
import json
import datetime
from azure.iot.device.provisioning.pipeline import (
    pipeline_stages_provisioning,
    pipeline_ops_provisioning,
)
from azure.iot.device.common.pipeline import pipeline_ops_base, pipeline_events_base
from tests.common.pipeline import pipeline_stage_test
from azure.iot.device.exceptions import ServiceError

from azure.iot.device.provisioning.models.registration_result import (
    RegistrationResult,
    RegistrationState,
)
from tests.common.pipeline.helpers import StageRunOpTestBase
from azure.iot.device import exceptions
from azure.iot.device.provisioning.pipeline import constant
import threading

logging.basicConfig(level=logging.DEBUG)
this_module = sys.modules[__name__]
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")


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


###############################
# REGISTRATION STAGE #
###############################


class RegistrationStageConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_provisioning.RegistrationStage

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
    stage_class_under_test=pipeline_stages_provisioning.RegistrationStage,
    stage_test_config_class=RegistrationStageConfig,
)


@pytest.mark.describe("RegistrationStage - .run_op() -- called with RegisterOperation")
class TestRegistrationStageWithRegisterOperation(StageRunOpTestBase, RegistrationStageConfig):
    @pytest.fixture(params=[" ", fake_payload], ids=["empty payload", "some payload"])
    def request_payload(self, request):
        return request.param

    @pytest.fixture
    def op(self, stage, mocker, request_payload):
        op = pipeline_ops_provisioning.RegisterOperation(
            request_payload, fake_registration_id, callback=mocker.MagicMock()
        )
        return op

    @pytest.fixture
    def request_body(self, request_payload):
        return '{{"payload": {json_payload}, "registrationId": "{reg_id}"}}'.format(
            reg_id=fake_registration_id, json_payload=json.dumps(request_payload)
        )

    @pytest.mark.it(
        "Sends a new RequestAndResponseOperation down the pipeline, configured to request a registration from provisioning service"
    )
    def test_request_and_response_op(self, stage, op, request_body):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.RequestAndResponseOperation)
        assert new_op.request_type == "register"
        assert new_op.method == "PUT"
        assert new_op.resource_location == "/"
        assert new_op.request_body == request_body

        # kill the timer
        new_op.complete()


@pytest.mark.describe("RegistrationStage - .run_op() -- Called with other arbitrary operation")
class TestRegistrationStageWithArbitraryOperation(StageRunOpTestBase, RegistrationStageConfig):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down the pipeline")
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe(
    "RegistrationStage - EVENT: RequestAndResponseOperation created from RegisterOperation is completed"
)
class TestRegistrationStageWithRegisterOperationCompleted(RegistrationStageConfig):
    @pytest.fixture(params=[" ", fake_payload], ids=["empty payload", "some payload"])
    def request_payload(self, request):
        return request.param

    @pytest.fixture
    def send_registration_op(self, mocker, request_payload):
        op = pipeline_ops_provisioning.RegisterOperation(
            request_payload, fake_registration_id, callback=mocker.MagicMock()
        )
        return op

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs, send_registration_op):
        stage = cls_type(**init_kwargs)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        # Run the registration operation
        stage.run_op(send_registration_op)
        return stage

    @pytest.fixture
    def request_and_response_op(self, stage):
        assert stage.send_op_down.call_count == 1
        op = stage.send_op_down.call_args[0][0]
        assert isinstance(op, pipeline_ops_base.RequestAndResponseOperation)
        # reset the stage mock for convenience
        stage.send_op_down.reset_mock()
        return op

    @pytest.fixture
    def request_body(self, request_payload):
        return '{{"payload": {json_payload}, "registrationId": "{reg_id}"}}'.format(
            reg_id=fake_registration_id, json_payload=json.dumps(request_payload)
        )

    @pytest.mark.it(
        "Completes the RegisterOperation unsuccessfully, with the error from the RequestAndResponseOperation, if the RequestAndResponseOperation is completed unsuccessfully"
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
    @pytest.mark.parametrize(
        "has_response_body", [True, False], ids=["With Response Body", "No Response Body"]
    )
    def test_request_and_response_op_completed_with_err(
        self,
        stage,
        send_registration_op,
        request_and_response_op,
        status_code,
        has_response_body,
        arbitrary_exception,
    ):
        assert not send_registration_op.completed
        assert not request_and_response_op.completed

        # NOTE: It shouldn't happen that an operation completed with error has a status code or a
        # response body, but it IS possible.
        request_and_response_op.status_code = status_code
        if has_response_body:
            request_and_response_op.response_body = b'{"key": "value"}'
        request_and_response_op.complete(error=arbitrary_exception)

        assert request_and_response_op.completed
        assert request_and_response_op.error is arbitrary_exception
        assert send_registration_op.completed
        assert send_registration_op.error is arbitrary_exception
        assert send_registration_op.registration_result is None

    @pytest.mark.it(
        "Completes the RegisterOperation unsuccessfully with a ServiceError if the RequestAndResponseOperation is completed with a status code >= 300 and less than 429"
    )
    @pytest.mark.parametrize(
        "has_response_body", [True, False], ids=["With Response Body", "No Response Body"]
    )
    @pytest.mark.parametrize(
        "status_code",
        [
            pytest.param(300, id="Status Code: 300"),
            pytest.param(400, id="Status Code: 400"),
            pytest.param(428, id="Status Code: 428"),
        ],
    )
    def test_request_and_response_op_completed_success_with_bad_code(
        self, stage, send_registration_op, request_and_response_op, status_code, has_response_body
    ):
        assert not send_registration_op.completed
        assert not request_and_response_op.completed

        request_and_response_op.status_code = status_code
        if has_response_body:
            request_and_response_op.response_body = b'{"key": "value"}'
        request_and_response_op.complete()

        assert request_and_response_op.completed
        assert request_and_response_op.error is None
        assert send_registration_op.completed
        assert isinstance(send_registration_op.error, ServiceError)
        # Twin is NOT returned
        assert send_registration_op.registration_result is None

    @pytest.mark.it(
        "Decodes, deserializes, and returns registration_result on the RegisterOperation op when RequestAndResponseOperation completes with no error if the status code < 300 and if status is 'assigned'"
    )
    def test_request_and_response_op_completed_success_with_status_assigned(
        self, stage, request_payload, send_registration_op, request_and_response_op
    ):
        registration_result = create_registration_result(request_payload, "assigned")

        assert not send_registration_op.completed
        assert not request_and_response_op.completed

        request_and_response_op.status_code = 200
        request_and_response_op.retry_after = None
        request_and_response_op.response_body = get_registration_result_as_bytes(
            registration_result
        )
        request_and_response_op.complete()

        assert request_and_response_op.completed
        assert request_and_response_op.error is None
        assert send_registration_op.completed
        assert send_registration_op.error is None
        # We need to assert string representations as these are inherently different objects
        assert str(send_registration_op.registration_result) == str(registration_result)

    @pytest.mark.it(
        "Decodes, deserializes, and returns registration_result along with an error on the RegisterOperation op when RequestAndResponseOperation completes with status code < 300 and status 'failed'"
    )
    def test_request_and_response_op_completed_success_with_status_failed(
        self, stage, request_payload, send_registration_op, request_and_response_op
    ):
        registration_result = create_registration_result(request_payload, "failed")

        assert not send_registration_op.completed
        assert not request_and_response_op.completed

        request_and_response_op.status_code = 200
        request_and_response_op.retry_after = None
        request_and_response_op.response_body = get_registration_result_as_bytes(
            registration_result
        )
        request_and_response_op.complete()

        assert request_and_response_op.completed
        assert request_and_response_op.error is None
        assert send_registration_op.completed
        assert isinstance(send_registration_op.error, ServiceError)
        # We need to assert string representations as these are inherently different objects
        assert str(send_registration_op.registration_result) == str(registration_result)
        assert "failed registration status" in str(send_registration_op.error)

    @pytest.mark.it(
        "Returns error on the RegisterOperation op when RequestAndResponseOperation completes with status code < 300 and some unknown status"
    )
    def test_request_and_response_op_completed_success_with_unknown_status(
        self, stage, request_payload, send_registration_op, request_and_response_op
    ):
        registration_result = create_registration_result(request_payload, "quidditching")

        assert not send_registration_op.completed
        assert not request_and_response_op.completed

        request_and_response_op.status_code = 200
        request_and_response_op.retry_after = None
        request_and_response_op.response_body = get_registration_result_as_bytes(
            registration_result
        )
        request_and_response_op.complete()

        assert request_and_response_op.completed
        assert request_and_response_op.error is None
        assert send_registration_op.completed
        assert isinstance(send_registration_op.error, ServiceError)
        assert "invalid registration status" in str(send_registration_op.error)

    @pytest.mark.it(
        "Decodes, deserializes the response from RequestAndResponseOperation and creates another op if the status code < 300 and if status is 'assigning'"
    )
    def test_spawns_another_op_request_and_response_op_completed_success_with_status_assigning(
        self, mocker, stage, request_payload, send_registration_op, request_and_response_op
    ):
        mock_timer = mocker.patch(
            "azure.iot.device.provisioning.pipeline.pipeline_stages_provisioning.Timer"
        )

        mocker.spy(send_registration_op, "spawn_worker_op")
        registration_result = create_registration_result(request_payload, "assigning")

        assert not send_registration_op.completed
        assert not request_and_response_op.completed

        request_and_response_op.status_code = 200
        request_and_response_op.retry_after = None
        request_and_response_op.response_body = get_registration_result_as_bytes(
            registration_result
        )
        request_and_response_op.complete()

        assert send_registration_op.retry_after_timer is None
        assert send_registration_op.polling_timer is not None
        timer_callback = mock_timer.call_args[0][1]
        timer_callback()

        assert request_and_response_op.completed
        assert request_and_response_op.error is None
        assert not send_registration_op.completed
        assert send_registration_op.error is None
        assert (
            send_registration_op.spawn_worker_op.call_args[1]["operation_id"] == fake_operation_id
        )


class RetryStageConfig(object):
    @pytest.fixture
    def init_kwargs(self):
        return {}

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        mocker.spy(stage, "run_op")
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        return stage


@pytest.mark.describe("RegistrationStage - .run_op() -- retried again with RegisterOperation")
class TestRegistrationStageWithRetryOfRegisterOperation(RetryStageConfig):
    @pytest.fixture(params=[" ", fake_payload], ids=["empty payload", "some payload"])
    def request_payload(self, request):
        return request.param

    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_provisioning.RegistrationStage

    @pytest.fixture
    def op(self, stage, mocker, request_payload):
        return pipeline_ops_provisioning.RegisterOperation(
            request_payload, fake_registration_id, callback=mocker.MagicMock()
        )

    @pytest.fixture
    def request_body(self, request_payload):
        return '{{"payload": {json_payload}, "registrationId": "{reg_id}"}}'.format(
            reg_id=fake_registration_id, json_payload=json.dumps(request_payload)
        )

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
        assert stage.send_op_down.call_count == 1
        next_op = stage.send_op_down.call_args[0][0]
        assert isinstance(next_op, pipeline_ops_base.RequestAndResponseOperation)

        next_op.status_code = 430
        next_op.retry_after = "1"
        registration_result = create_registration_result(request_payload, "flying")
        next_op.response_body = get_registration_result_as_bytes(registration_result)
        next_op.complete()

        assert op.retry_after_timer is not None
        assert op.polling_timer is None
        timer_callback = mock_timer.call_args[0][1]
        timer_callback()

        assert stage.run_op.call_count == 2
        assert stage.send_op_down.call_count == 2

        next_op_2 = stage.send_op_down.call_args[0][0]
        assert isinstance(next_op_2, pipeline_ops_base.RequestAndResponseOperation)
        assert next_op_2.request_type == "register"
        assert next_op_2.method == "PUT"
        assert next_op_2.resource_location == "/"
        assert next_op_2.request_body == request_body


@pytest.mark.describe(
    "RegistrationStage - .run_op() -- Called with register request operation eligible for timeout"
)
class TestRegistrationStageWithTimeoutOfRegisterOperation(
    StageRunOpTestBase, RegistrationStageConfig
):
    @pytest.fixture
    def op(self, stage, mocker):
        op = pipeline_ops_provisioning.RegisterOperation(
            " ", fake_registration_id, callback=mocker.MagicMock()
        )
        return op

    @pytest.fixture
    def mock_timer(self, mocker):
        return mocker.patch(
            "azure.iot.device.provisioning.pipeline.pipeline_stages_provisioning.Timer"
        )

    @pytest.mark.it(
        "Adds a provisioning timeout timer with the interval specified in the configuration to the operation, and starts it"
    )
    def test_adds_timer(self, mocker, stage, op, mock_timer):
        stage.run_op(op)

        assert mock_timer.call_count == 1
        assert mock_timer.call_args == mocker.call(constant.DEFAULT_TIMEOUT_INTERVAL, mocker.ANY)
        assert op.provisioning_timeout_timer is mock_timer.return_value
        assert op.provisioning_timeout_timer.start.call_count == 1
        assert op.provisioning_timeout_timer.start.call_args == mocker.call()

    @pytest.mark.it(
        "Sends converted RequestResponse Op down the pipeline after attaching timer to the original op"
    )
    def test_sends_down(self, mocker, stage, op, mock_timer):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1

        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.RequestAndResponseOperation)

        assert op.provisioning_timeout_timer is mock_timer.return_value

    @pytest.mark.it("Completes the operation unsuccessfully, with a ServiceError due to timeout")
    def test_not_complete_timeout(self, mocker, stage, op, mock_timer):
        # Apply the timer
        stage.run_op(op)
        assert not op.completed
        assert mock_timer.call_count == 1
        on_timer_complete = mock_timer.call_args[0][1]

        # Call timer complete callback (indicating timer completion)
        on_timer_complete()

        # Op is now completed with error
        assert op.completed
        assert isinstance(op.error, exceptions.ServiceError)
        assert "register" in op.error.args[0]

    @pytest.mark.it(
        "Completes the operation successfully, cancels and clears the operation's timeout timer"
    )
    def test_complete_before_timeout(self, mocker, stage, op, mock_timer):
        # Apply the timer
        stage.run_op(op)
        assert not op.completed
        assert mock_timer.call_count == 1
        mock_timer_inst = op.provisioning_timeout_timer
        assert mock_timer_inst is mock_timer.return_value
        assert mock_timer_inst.cancel.call_count == 0

        # Complete the next operation
        new_op = stage.send_op_down.call_args[0][0]
        new_op.complete()

        # Timer is now cancelled and cleared
        assert mock_timer_inst.cancel.call_count == 1
        assert mock_timer_inst.cancel.call_args == mocker.call()
        assert op.provisioning_timeout_timer is None


class PollingStageConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_provisioning.PollingStatusStage

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
    stage_class_under_test=pipeline_stages_provisioning.PollingStatusStage,
    stage_test_config_class=PollingStageConfig,
)


@pytest.mark.describe("PollingStatusStage - .run_op() -- called with PollStatusOperation")
class TestPollingStatusStageWithPollStatusOperation(StageRunOpTestBase, PollingStageConfig):
    @pytest.fixture
    def op(self, stage, mocker):
        op = pipeline_ops_provisioning.PollStatusOperation(
            fake_operation_id, " ", callback=mocker.MagicMock()
        )
        return op

    @pytest.mark.it(
        "Sends a new RequestAndResponseOperation down the pipeline, configured to request a registration from provisioning service"
    )
    def test_request_and_response_op(self, stage, op):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.RequestAndResponseOperation)
        assert new_op.request_type == "query"
        assert new_op.method == "GET"
        assert new_op.resource_location == "/"
        assert new_op.request_body == " "

        # kill the timer
        new_op.complete()


@pytest.mark.describe("PollingStatusStage - .run_op() -- Called with other arbitrary operation")
class TestPollingStatusStageWithArbitraryOperation(StageRunOpTestBase, PollingStageConfig):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down the pipeline")
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe(
    "PollingStatusStage - EVENT: RequestAndResponseOperation created from PollStatusOperation is completed"
)
class TestPollingStatusStageWithPollStatusOperationCompleted(PollingStageConfig):
    @pytest.fixture
    def send_query_op(self, mocker):
        op = pipeline_ops_provisioning.PollStatusOperation(
            fake_operation_id, " ", callback=mocker.MagicMock()
        )
        return op

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs, send_query_op):
        stage = cls_type(**init_kwargs)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        # Run the registration operation
        stage.run_op(send_query_op)
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
        "Completes the PollStatusOperation unsuccessfully, with the error from the RequestAndResponseOperation, if the RequestAndResponseOperation is completed unsuccessfully"
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
    @pytest.mark.parametrize(
        "has_response_body", [True, False], ids=["With Response Body", "No Response Body"]
    )
    def test_request_and_response_op_completed_with_err(
        self,
        stage,
        send_query_op,
        request_and_response_op,
        status_code,
        has_response_body,
        arbitrary_exception,
    ):
        assert not send_query_op.completed
        assert not request_and_response_op.completed

        # NOTE: It shouldn't happen that an operation completed with error has a status code or a
        # response body, but it IS possible.
        request_and_response_op.status_code = status_code
        if has_response_body:
            request_and_response_op.response_body = b'{"key": "value"}'
        request_and_response_op.complete(error=arbitrary_exception)

        assert request_and_response_op.completed
        assert request_and_response_op.error is arbitrary_exception
        assert send_query_op.completed
        assert send_query_op.error is arbitrary_exception
        assert send_query_op.registration_result is None

    @pytest.mark.it(
        "Completes the PollStatusOperation unsuccessfully with a ServiceError if the RequestAndResponseOperation is completed with a status code >= 300 and less than 429"
    )
    @pytest.mark.parametrize(
        "has_response_body", [True, False], ids=["With Response Body", "No Response Body"]
    )
    @pytest.mark.parametrize(
        "status_code",
        [
            pytest.param(300, id="Status Code: 300"),
            pytest.param(400, id="Status Code: 400"),
            pytest.param(428, id="Status Code: 428"),
        ],
    )
    def test_request_and_response_op_completed_success_with_bad_code(
        self, stage, send_query_op, request_and_response_op, status_code, has_response_body
    ):
        assert not send_query_op.completed
        assert not request_and_response_op.completed

        request_and_response_op.status_code = status_code
        if has_response_body:
            request_and_response_op.response_body = b'{"key": "value"}'
        request_and_response_op.complete()

        assert request_and_response_op.completed
        assert request_and_response_op.error is None
        assert send_query_op.completed
        assert isinstance(send_query_op.error, ServiceError)
        # Twin is NOT returned
        assert send_query_op.registration_result is None

    @pytest.mark.it(
        "Decodes, deserializes, and returns registration_result on the PollStatusOperation op when RequestAndResponseOperation completes with no error if the status code < 300 and if status is 'assigned'"
    )
    def test_request_and_response_op_completed_success_with_status_assigned(
        self, stage, send_query_op, request_and_response_op
    ):
        registration_result = create_registration_result(" ", "assigned")

        assert not send_query_op.completed
        assert not request_and_response_op.completed

        request_and_response_op.status_code = 200
        request_and_response_op.retry_after = None
        request_and_response_op.response_body = get_registration_result_as_bytes(
            registration_result
        )
        request_and_response_op.complete()

        assert request_and_response_op.completed
        assert request_and_response_op.error is None
        assert send_query_op.completed
        assert send_query_op.error is None
        # We need to assert string representations as these are inherently different objects
        assert str(send_query_op.registration_result) == str(registration_result)

    @pytest.mark.it(
        "Decodes, deserializes, and returns registration_result along with an error on the PollStatusOperation op when RequestAndResponseOperation completes with status code < 300 and status 'failed'"
    )
    def test_request_and_response_op_completed_success_with_status_failed(
        self, stage, send_query_op, request_and_response_op
    ):
        registration_result = create_registration_result(" ", "failed")

        assert not send_query_op.completed
        assert not request_and_response_op.completed

        request_and_response_op.status_code = 200
        request_and_response_op.retry_after = None
        request_and_response_op.response_body = get_registration_result_as_bytes(
            registration_result
        )
        request_and_response_op.complete()

        assert request_and_response_op.completed
        assert request_and_response_op.error is None
        assert send_query_op.completed
        assert isinstance(send_query_op.error, ServiceError)
        # We need to assert string representations as these are inherently different objects
        assert str(send_query_op.registration_result) == str(registration_result)
        assert "failed registration status" in str(send_query_op.error)

    @pytest.mark.it(
        "Returns error on the PollStatusOperation op when RequestAndResponseOperation completes with status code < 300 and some unknown status"
    )
    def test_request_and_response_op_completed_success_with_unknown_status(
        self, stage, send_query_op, request_and_response_op
    ):
        registration_result = create_registration_result(" ", "quidditching")

        assert not send_query_op.completed
        assert not request_and_response_op.completed

        request_and_response_op.status_code = 200
        request_and_response_op.retry_after = None
        request_and_response_op.response_body = get_registration_result_as_bytes(
            registration_result
        )
        request_and_response_op.complete()

        assert request_and_response_op.completed
        assert request_and_response_op.error is None
        assert send_query_op.completed
        assert isinstance(send_query_op.error, ServiceError)
        assert "invalid registration status" in str(send_query_op.error)


@pytest.mark.describe("PollingStatusStage - .run_op() -- retried again with PollStatusOperation")
class TestPollingStatusStageWithPollStatusRetryOperation(RetryStageConfig):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_provisioning.PollingStatusStage

    @pytest.fixture
    def op(self, stage, mocker):
        op = pipeline_ops_provisioning.PollStatusOperation(
            fake_operation_id, " ", callback=mocker.MagicMock()
        )
        return op

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
        assert stage.send_op_down.call_count == 1
        next_op = stage.send_op_down.call_args[0][0]
        assert isinstance(next_op, pipeline_ops_base.RequestAndResponseOperation)

        next_op.status_code = 430
        next_op.retry_after = "1"
        registration_result = create_registration_result(" ", "flying")
        next_op.response_body = get_registration_result_as_bytes(registration_result)
        next_op.complete()

        assert op.retry_after_timer is not None
        assert op.polling_timer is None
        timer_callback = mock_timer.call_args[0][1]
        timer_callback()

        assert stage.run_op.call_count == 2
        assert stage.send_op_down.call_count == 2

        next_op_2 = stage.send_op_down.call_args[0][0]
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
        assert stage.send_op_down.call_count == 1
        next_op = stage.send_op_down.call_args[0][0]
        assert isinstance(next_op, pipeline_ops_base.RequestAndResponseOperation)

        next_op.status_code = 228
        next_op.retry_after = "1"
        registration_result = create_registration_result(" ", "assigning")
        next_op.response_body = get_registration_result_as_bytes(registration_result)
        next_op.complete()

        assert op.retry_after_timer is None
        assert op.polling_timer is not None
        timer_callback = mock_timer.call_args[0][1]
        timer_callback()

        assert stage.run_op.call_count == 2
        assert stage.send_op_down.call_count == 2

        next_op_2 = stage.send_op_down.call_args[0][0]
        assert isinstance(next_op_2, pipeline_ops_base.RequestAndResponseOperation)
        assert next_op_2.request_type == "query"
        assert next_op_2.method == "GET"
        assert next_op_2.resource_location == "/"
        assert next_op_2.request_body == " "


@pytest.mark.describe(
    "RegistrationStage - .run_op() -- Called with register request operation eligible for timeout"
)
class TestPollingStageWithTimeoutOfQueryOperation(StageRunOpTestBase, PollingStageConfig):
    @pytest.fixture
    def op(self, stage, mocker):
        op = pipeline_ops_provisioning.PollStatusOperation(
            fake_operation_id, " ", callback=mocker.MagicMock()
        )
        return op

    @pytest.fixture
    def mock_timer(self, mocker):
        return mocker.patch(
            "azure.iot.device.provisioning.pipeline.pipeline_stages_provisioning.Timer"
        )

    @pytest.mark.it(
        "Adds a provisioning timeout timer with the interval specified in the configuration to the operation, and starts it"
    )
    def test_adds_timer(self, mocker, stage, op, mock_timer):
        stage.run_op(op)

        assert mock_timer.call_count == 1
        assert mock_timer.call_args == mocker.call(constant.DEFAULT_TIMEOUT_INTERVAL, mocker.ANY)
        assert op.provisioning_timeout_timer is mock_timer.return_value
        assert op.provisioning_timeout_timer.start.call_count == 1
        assert op.provisioning_timeout_timer.start.call_args == mocker.call()

    @pytest.mark.it(
        "Sends converted RequestResponse Op down the pipeline after attaching timer to the original op"
    )
    def test_sends_down(self, mocker, stage, op, mock_timer):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1

        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.RequestAndResponseOperation)

        assert op.provisioning_timeout_timer is mock_timer.return_value

    @pytest.mark.it("Completes the operation unsuccessfully, with a ServiceError due to timeout")
    def test_not_complete_timeout(self, mocker, stage, op, mock_timer):
        # Apply the timer
        stage.run_op(op)
        assert not op.completed
        assert mock_timer.call_count == 1
        on_timer_complete = mock_timer.call_args[0][1]

        # Call timer complete callback (indicating timer completion)
        on_timer_complete()

        # Op is now completed with error
        assert op.completed
        assert isinstance(op.error, exceptions.ServiceError)
        assert "query" in op.error.args[0]

    @pytest.mark.it(
        "Completes the operation successfully, cancels and clears the operation's timeout timer"
    )
    def test_complete_before_timeout(self, mocker, stage, op, mock_timer):
        # Apply the timer
        stage.run_op(op)
        assert not op.completed
        assert mock_timer.call_count == 1
        mock_timer_inst = op.provisioning_timeout_timer
        assert mock_timer_inst is mock_timer.return_value
        assert mock_timer_inst.cancel.call_count == 0

        # Complete the next operation
        new_op = stage.send_op_down.call_args[0][0]
        new_op.complete()

        # Timer is now cancelled and cleared
        assert mock_timer_inst.cancel.call_count == 1
        assert mock_timer_inst.cancel.call_args == mocker.call()
        assert op.provisioning_timeout_timer is None
