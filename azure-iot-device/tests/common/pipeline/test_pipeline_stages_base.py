# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import copy
import time
import pytest
import sys
import threading
import random
import uuid
import queue
from azure.iot.device.common import transport_exceptions, alarm
from azure.iot.device.common.auth import sastoken as st
from azure.iot.device.common.pipeline import (
    pipeline_stages_base,
    pipeline_ops_base,
    pipeline_ops_mqtt,
    pipeline_events_base,
    pipeline_exceptions,
)

# I normally try to keep my imports in tests at module level, but it's just too unwieldy w/ ReconnectState
from azure.iot.device.common.pipeline.pipeline_stages_base import ReconnectState
from .helpers import StageRunOpTestBase, StageHandlePipelineEventTestBase
from .fixtures import ArbitraryOperation, ArbitraryEvent
from tests.common.pipeline import pipeline_stage_test


this_module = sys.modules[__name__]
logging.basicConfig(level=logging.DEBUG)
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")


fake_signed_data = "ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI="
fake_uri = "some/resource/location"
fake_current_time = 10000000000
fake_expiry = 10000003600


###################
# COMMON FIXTURES #
###################
@pytest.fixture
def mock_timer(mocker):
    return mocker.patch.object(threading, "Timer")


@pytest.fixture
def mock_alarm(mocker):
    return mocker.patch.object(alarm, "Alarm")


@pytest.fixture(autouse=True)
def mock_time(mocker):
    # Need to ALWAYS mock current time
    time_mock = mocker.patch.object(time, "time")
    time_mock.return_value = fake_current_time


# Not a fixture, but useful for sharing
def fake_callback(*args, **kwargs):
    pass


#######################
# PIPELINE ROOT STAGE #
#######################


class PipelineRootStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_base.PipelineRootStage

    @pytest.fixture
    def init_kwargs(self, mocker):
        return {"pipeline_configuration": mocker.MagicMock()}

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")
        return stage


class PipelineRootStageInstantiationTests(PipelineRootStageTestConfig):
    @pytest.mark.it("Initializes 'on_pipeline_event_handler' as None")
    def test_on_pipeline_event_handler(self, init_kwargs):
        stage = pipeline_stages_base.PipelineRootStage(**init_kwargs)
        assert stage.on_pipeline_event_handler is None

    @pytest.mark.it("Initializes 'on_connected_handler' as None")
    def test_on_connected_handler(self, init_kwargs):
        stage = pipeline_stages_base.PipelineRootStage(**init_kwargs)
        assert stage.on_connected_handler is None

    @pytest.mark.it("Initializes 'on_disconnected_handler' as None")
    def test_on_disconnected_handler(self, init_kwargs):
        stage = pipeline_stages_base.PipelineRootStage(**init_kwargs)
        assert stage.on_disconnected_handler is None

    @pytest.mark.it("Initializes 'on_new_sastoken_required_handler' as None")
    def test_on_new_sastoken_required_handler(self, init_kwargs):
        stage = pipeline_stages_base.PipelineRootStage(**init_kwargs)
        assert stage.on_new_sastoken_required_handler is None

    @pytest.mark.it("Initializes 'on_background_exception_handler' as None")
    def test_on_background_exception_handler(self, init_kwargs):
        stage = pipeline_stages_base.PipelineRootStage(**init_kwargs)
        assert stage.on_background_exception_handler is None

    @pytest.mark.it("Initializes 'connected' as False")
    def test_connected(self, init_kwargs):
        stage = pipeline_stages_base.PipelineRootStage(**init_kwargs)
        assert stage.connected is False

    @pytest.mark.it(
        "Initializes 'pipeline_configuration' with the provided 'pipeline_configuration' parameter"
    )
    def test_pipeline_configuration(self, init_kwargs):
        stage = pipeline_stages_base.PipelineRootStage(**init_kwargs)
        assert stage.pipeline_configuration is init_kwargs["pipeline_configuration"]


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_base.PipelineRootStage,
    stage_test_config_class=PipelineRootStageTestConfig,
    extended_stage_instantiation_test_class=PipelineRootStageInstantiationTests,
)


@pytest.mark.describe("PipelineRootStage - .append_stage()")
class TestPipelineRootStageAppendStage(PipelineRootStageTestConfig):
    @pytest.mark.it("Appends the provided stage to the tail of the pipeline")
    @pytest.mark.parametrize(
        "pipeline_len",
        [
            pytest.param(1, id="Pipeline Length: 1"),
            pytest.param(2, id="Pipeline Length: 2"),
            pytest.param(3, id="Pipeline Length: 3"),
            pytest.param(10, id="Pipeline Length: 10"),
            pytest.param(random.randint(4, 99), id="Randomly chosen Pipeline Length"),
        ],
    )
    def test_appends_new_stage(self, stage, pipeline_len):
        class ArbitraryStage(pipeline_stages_base.PipelineStage):
            pass

        assert stage.next is None
        assert stage.previous is None
        prev_tail = stage
        root = stage
        for _ in range(0, pipeline_len):
            new_stage = ArbitraryStage()
            stage.append_stage(new_stage)
            assert prev_tail.next is new_stage
            assert new_stage.previous is prev_tail
            assert new_stage.pipeline_root is root
            prev_tail = new_stage


# NOTE 1: Because the Root stage overrides the parent implementation, we must test it here
# (even though it's the same test).
# NOTE 2: Currently this implementation does some other things with threads, but we do not
# currently have a thread testing strategy, so it is untested for now.
@pytest.mark.describe("PipelineRootStage - .run_op()")
class TestPipelineRootStageRunOp(PipelineRootStageTestConfig):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down")
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe("PipelineRootStage - .handle_pipeline_event() -- Called with ConnectedEvent")
class TestPipelineRootStageHandlePipelineEventWithConnectedEvent(
    PipelineRootStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self):
        return pipeline_events_base.ConnectedEvent()

    @pytest.mark.it("Sets the 'connected' attribute to True")
    def test_set_connected_true(self, stage, event):
        assert not stage.connected
        stage.handle_pipeline_event(event)
        assert stage.connected

    @pytest.mark.it("Invokes the 'on_connected_handler' handler function, if set")
    def test_invoke_handler(self, mocker, stage, event):
        mock_handler = mocker.MagicMock()
        stage.on_connected_handler = mock_handler
        stage.handle_pipeline_event(event)
        time.sleep(0.1)  # Needs a brief sleep so thread can switch
        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call()


@pytest.mark.describe(
    "PipelineRootStage - .handle_pipeline_event() -- Called with DisconnectedEvent"
)
class TestPipelineRootStageHandlePipelineEventWithDisconnectedEvent(
    PipelineRootStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self):
        return pipeline_events_base.DisconnectedEvent()

    @pytest.mark.it("Sets the 'connected' attribute to True")
    def test_set_connected_false(self, stage, event):
        stage.connected = True
        stage.handle_pipeline_event(event)
        assert not stage.connected

    @pytest.mark.it("Invokes the 'on_disconnected_handler' handler function, if set")
    def test_invoke_handler(self, mocker, stage, event):
        mock_handler = mocker.MagicMock()
        stage.on_disconnected_handler = mock_handler
        stage.handle_pipeline_event(event)
        time.sleep(0.1)  # Needs a brief sleep so thread can switch
        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call()


@pytest.mark.describe(
    "PipelineRootStage - .handle_pipeline_event() -- Called with NewSasTokenRequiredEvent"
)
class TestPipelineRootStageHandlePipelineEventWithNewSasTokenRequiredEvent(
    PipelineRootStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self):
        return pipeline_events_base.NewSasTokenRequiredEvent()

    @pytest.mark.it("Invokes the 'on_new_sastoken_required_handler' handler function, if set")
    def test_invoke_handler(self, mocker, stage, event):
        mock_handler = mocker.MagicMock()
        stage.on_new_sastoken_required_handler = mock_handler
        stage.handle_pipeline_event(event)
        time.sleep(0.1)  # Needs a brief sleep so thread can switch
        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call()


@pytest.mark.describe(
    "PipelineRootStage - .handle_pipeline_event() -- Called with BackgroundExceptionEvent"
)
class TestPipelineRootStageHandlePipelineEventWithBackgroundExceptionEvent(
    PipelineRootStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self, arbitrary_exception):
        return pipeline_events_base.BackgroundExceptionEvent(arbitrary_exception)

    @pytest.mark.it(
        "Invokes the 'on_background_exception_handler' handler function, passing the exception object, if set"
    )
    def test_invoke_handler(self, mocker, stage, event):
        mock_handler = mocker.MagicMock()
        stage.on_background_exception_handler = mock_handler
        stage.handle_pipeline_event(event)
        time.sleep(0.1)  # Needs a brief sleep so thread can switch
        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call(event.e)


@pytest.mark.describe(
    "PipelineRootStage - .handle_pipeline_event() -- Called with an arbitrary other event"
)
class TestPipelineRootStageHandlePipelineEventWithArbitraryEvent(
    PipelineRootStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self, arbitrary_event):
        return arbitrary_event

    @pytest.mark.it("Invokes the 'on_pipeline_event_handler' handler function, if set")
    def test_invoke_handler(self, mocker, stage, event):
        mock_handler = mocker.MagicMock()
        stage.on_pipeline_event_handler = mock_handler
        stage.handle_pipeline_event(event)
        time.sleep(0.1)  # Needs a brief sleep so thread can switch
        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call(event)


###########################
# SAS TOKEN RENEWAL STAGE #
###########################


class SasTokenStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_base.SasTokenStage

    @pytest.fixture
    def init_kwargs(self, mocker):
        return {}

    @pytest.fixture
    def stage(self, mocker, cls_type, sastoken, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.pipeline_root.pipeline_configuration.sastoken = sastoken
        stage.pipeline_root.pipeline_configuration.connection_retry_interval = 1234
        # Mock flow methods
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        stage.report_background_exception = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")
        return stage


class SasTokenStageInstantationTests(SasTokenStageTestConfig):
    @pytest.mark.it("Initializes with the token update alarm set to 'None'")
    def test_token_update_timer(self, init_kwargs):
        stage = pipeline_stages_base.SasTokenStage(**init_kwargs)
        assert stage._token_update_alarm is None

    @pytest.mark.it("Initializes with the reauth retry timer set to 'None'")
    def test_reauth_retry_timer(self, init_kwargs):
        stage = pipeline_stages_base.SasTokenStage(**init_kwargs)
        assert stage._reauth_retry_timer is None

    @pytest.mark.it("Uses 120 seconds as the Update Margin by default")
    def test_update_margin(self, init_kwargs):
        # NOTE: currently, update margin isn't set as an instance attribute really, it just uses
        # a constant defined on the class in all cases. Eventually this logic may be expanded to
        # be more dynamic, and this test will need to change
        stage = pipeline_stages_base.SasTokenStage(**init_kwargs)
        assert stage.DEFAULT_TOKEN_UPDATE_MARGIN == 120


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_base.SasTokenStage,
    stage_test_config_class=SasTokenStageTestConfig,
    extended_stage_instantiation_test_class=SasTokenStageInstantationTests,
)


@pytest.mark.describe(
    "SasTokenStage - .run_op() -- Called with InitializePipelineOperation (Pipeline configured for SAS authentication)"
)
class TestSasTokenStageRunOpWithInitializePipelineOpSasTokenConfig(
    SasTokenStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.InitializePipelineOperation(callback=mocker.MagicMock())

    @pytest.fixture(params=["Renewable SAS Authentication", "Non-renewable SAS Authentication"])
    def sastoken(self, mocker, request):
        if request.param == "Renewable SAS Authentication":
            mock_signing_mechanism = mocker.MagicMock()
            mock_signing_mechanism.sign.return_value = fake_signed_data
            sastoken = st.RenewableSasToken(uri=fake_uri, signing_mechanism=mock_signing_mechanism)
            sastoken.refresh = mocker.MagicMock()
        else:
            token_str = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
                resource=fake_uri, signature=fake_signed_data, expiry=fake_expiry
            )
            sastoken = st.NonRenewableSasToken(token_str)
        return sastoken

    @pytest.mark.it("Cancels any existing token update alarm that may have been set")
    def test_cancels_existing_alarm(self, mocker, mock_alarm, stage, op):
        stage._token_update_alarm = mock_alarm

        stage.run_op(op)

        assert mock_alarm.cancel.call_count == 1
        assert mock_alarm.cancel.call_args == mocker.call()

    @pytest.mark.it("Resets the token update alarm to None until a new one is set")
    # Edge case, since unless something goes wrong, the alarm WILL be set, and it's like
    # it was never set to None.
    def test_alarm_set_to_none_in_intermediate(
        self, mocker, stage, op, mock_alarm, arbitrary_exception
    ):
        # Set an existing alarm
        stage._token_update_alarm = mocker.MagicMock()

        # Set an error side effect on the alarm creation, so when a new alarm is created,
        # we have an unhandled error causing op failure and early exit
        mock_alarm.side_effect = arbitrary_exception

        stage.run_op(op)

        assert op.complete
        assert op.error is arbitrary_exception
        assert stage._token_update_alarm is None

    @pytest.mark.it(
        "Starts a background update alarm that will trigger 'Update Margin' number of seconds prior to SasToken expiration"
    )
    def test_sets_alarm(self, mocker, stage, op, mock_alarm):
        expected_alarm_time = (
            stage.pipeline_root.pipeline_configuration.sastoken.expiry_time
            - pipeline_stages_base.SasTokenStage.DEFAULT_TOKEN_UPDATE_MARGIN
        )

        stage.run_op(op)

        assert mock_alarm.call_count == 1
        assert mock_alarm.call_args[0][0] == expected_alarm_time
        assert mock_alarm.return_value.daemon is True
        assert mock_alarm.return_value.start.call_count == 1
        assert mock_alarm.return_value.start.call_args == mocker.call()

    @pytest.mark.it(
        "Starts a background update alarm that will instead trigger after MAX_TIMEOUT seconds if the SasToken expiration time (less the Update Margin) is more than MAX_TIMEOUT seconds in the future"
    )
    def test_sets_alarm_long_expiration(self, mocker, stage, op, mock_alarm):
        token = stage.pipeline_root.pipeline_configuration.sastoken
        new_expiry = token.expiry_time + threading.TIMEOUT_MAX
        if isinstance(token, st.RenewableSasToken):
            token._expiry_time = new_expiry
        else:
            token._token_info["se"] = new_expiry
        # NOTE: time.time is implicitly mocked to return a constant test value here
        expected_alarm_time = time.time() + threading.TIMEOUT_MAX
        assert expected_alarm_time < token.expiry_time

        stage.run_op(op)

        assert mock_alarm.call_count == 1
        assert mock_alarm.call_args[0][0] == expected_alarm_time
        assert mock_alarm.return_value.daemon is True
        assert mock_alarm.return_value.start.call_count == 1
        assert mock_alarm.return_value.start.call_args == mocker.call()


@pytest.mark.describe(
    "SasTokenStage - .run_op() -- Called with InitializePipelineOperation (Pipeline not configured for SAS authentication)"
)
class TestSasTokenStageRunOpWithInitializePipelineOpNoSasTokenConfig(
    SasTokenStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.InitializePipelineOperation(callback=mocker.MagicMock())

    @pytest.fixture
    def sastoken(self):
        return None

    @pytest.mark.it("Sends the operation down, WITHOUT setting a update alarm")
    def test_sends_op_down_no_alarm(self, mocker, stage, mock_alarm, op):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)
        assert stage._token_update_alarm is None
        assert mock_alarm.call_count == 0


@pytest.mark.describe(
    "SasTokenStage - .run_op() -- Called with ReauthorizeConnectionOperation (Pipeline configured for SAS authentication)"
)
class TestSasTokenStageRunOpWithReauthorizeConnectionOperationPipelineOpSasTokenConfig(
    SasTokenStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ReauthorizeConnectionOperation(callback=mocker.MagicMock())

    # NOTE: We test both renewable and non-renewable here for safety, but in practice, this will
    # only ever be for non-renewable tokens due to how the client forms the pipeline. A
    # ReauthorizeConnectionOperation that appears this high in the pipeline could only be created
    # in the case of non-renewable SAS flow.
    @pytest.fixture(params=["Renewable SAS Authentication", "Non-renewable SAS Authentication"])
    def sastoken(self, mocker, request):
        if request.param == "Renewable SAS Authentication":
            mock_signing_mechanism = mocker.MagicMock()
            mock_signing_mechanism.sign.return_value = fake_signed_data
            sastoken = st.RenewableSasToken(uri=fake_uri, signing_mechanism=mock_signing_mechanism)
            sastoken.refresh = mocker.MagicMock()
        else:
            token_str = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
                resource=fake_uri, signature=fake_signed_data, expiry=fake_expiry
            )
            sastoken = st.NonRenewableSasToken(token_str)
        return sastoken

    @pytest.mark.it("Cancels any existing token update alarm that may have been set")
    def test_cancels_existing_alarm(self, mocker, mock_alarm, stage, op):
        stage._token_update_alarm = mock_alarm

        stage.run_op(op)

        assert mock_alarm.cancel.call_count == 1
        assert mock_alarm.cancel.call_args == mocker.call()

    @pytest.mark.it("Resets the token update alarm to None until a new one is set")
    # Edge case, since unless something goes wrong, the alarm WILL be set, and it's like
    # it was never set to None.
    def test_alarm_set_to_none_in_intermediate(
        self, mocker, stage, op, mock_alarm, arbitrary_exception
    ):
        # Set an existing alarm
        stage._token_update_alarm = mocker.MagicMock()

        # Set an error side effect on the alarm creation, so when a new alarm is created,
        # we have an unhandled error causing op failure and early exit
        mock_alarm.side_effect = arbitrary_exception

        stage.run_op(op)

        assert op.complete
        assert op.error is arbitrary_exception
        assert stage._token_update_alarm is None

    @pytest.mark.it(
        "Starts a background update alarm that will trigger 'Update Margin' number of seconds prior to SasToken expiration"
    )
    def test_sets_alarm(self, mocker, stage, op, mock_alarm):
        expected_alarm_time = (
            stage.pipeline_root.pipeline_configuration.sastoken.expiry_time
            - pipeline_stages_base.SasTokenStage.DEFAULT_TOKEN_UPDATE_MARGIN
        )

        stage.run_op(op)

        assert mock_alarm.call_count == 1
        assert mock_alarm.call_args[0][0] == expected_alarm_time
        assert mock_alarm.return_value.daemon is True
        assert mock_alarm.return_value.start.call_count == 1
        assert mock_alarm.return_value.start.call_args == mocker.call()

    @pytest.mark.it(
        "Starts a background update alarm that will instead trigger after MAX_TIMEOUT seconds if the SasToken expiration time (less the Update Margin) is more than MAX_TIMEOUT seconds in the future"
    )
    def test_sets_alarm_long_expiration(self, mocker, stage, op, mock_alarm):
        token = stage.pipeline_root.pipeline_configuration.sastoken
        new_expiry = token.expiry_time + threading.TIMEOUT_MAX
        if isinstance(token, st.RenewableSasToken):
            token._expiry_time = new_expiry
        else:
            token._token_info["se"] = new_expiry
        # NOTE: time.time is implicitly mocked to return a constant test value here
        expected_alarm_time = time.time() + threading.TIMEOUT_MAX
        assert expected_alarm_time < token.expiry_time

        stage.run_op(op)

        assert mock_alarm.call_count == 1
        assert mock_alarm.call_args[0][0] == expected_alarm_time
        assert mock_alarm.return_value.daemon is True
        assert mock_alarm.return_value.start.call_count == 1
        assert mock_alarm.return_value.start.call_args == mocker.call()


@pytest.mark.describe(
    "SasTokenStage - .run_op() -- Called with ReauthorizeConnectionOperation (Pipeline not configured for SAS authentication)"
)
class TestSasTokenStageRunOpWithReauthorizeConnectionOperationPipelineOpNoSasTokenConfig(
    SasTokenStageTestConfig, StageRunOpTestBase
):
    # NOTE: In practice this case will never happen. Currently ReauthorizeConnectionOperations only
    # occur for SAS-based auth. Still, we test this combination of configurations for completeness
    # and safety of having a defined behavior even for an impossible case, as we want to avoid
    # using outside knowledge in unit-tests - without that knowledge of the rest of the client and
    # pipeline, there's no reason to know that it couldn't happen.

    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ReauthorizeConnectionOperation(callback=mocker.MagicMock())

    @pytest.fixture
    def sastoken(self):
        return None

    @pytest.mark.it("Sends the operation down, WITHOUT setting a update alarm")
    def test_sends_op_down_no_alarm(self, mocker, stage, mock_alarm, op):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)
        assert stage._token_update_alarm is None
        assert mock_alarm.call_count == 0


@pytest.mark.describe("SasTokenStage - .run_op() -- Called with ShutdownPipelineOperation")
class TestSasTokenStageRunOpWithShutdownPipelineOp(SasTokenStageTestConfig, StageRunOpTestBase):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ShutdownPipelineOperation(callback=mocker.MagicMock())

    @pytest.fixture(
        params=[
            "Renewable SAS Authentication",
            "Non-renewable SAS Authentication",
            "No SAS Authentication",
        ]
    )
    def sastoken(self, mocker, request):
        if request.param == "Renewable SAS Authentication":
            mock_signing_mechanism = mocker.MagicMock()
            mock_signing_mechanism.sign.return_value = fake_signed_data
            sastoken = st.RenewableSasToken(uri=fake_uri, signing_mechanism=mock_signing_mechanism)
            sastoken.refresh = mocker.MagicMock()
        elif request.param == "Non-renewable SAS Authentication":
            token_str = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
                resource=fake_uri, signature=fake_signed_data, expiry=fake_expiry
            )
            sastoken = st.NonRenewableSasToken(token_str)
        else:
            sastoken = None
        return sastoken

    @pytest.mark.it(
        "Cancels the token update alarm and the reauth retry timer, then sends the operation down, if an alarm exists"
    )
    def test_with_timer(self, mocker, stage, op, mock_alarm, mock_timer):
        stage._token_update_alarm = mock_alarm
        stage._reauth_retry_timer = mock_timer
        assert mock_alarm.cancel.call_count == 0
        assert mock_timer.cancel.call_count == 0
        assert stage.send_op_down.call_count == 0

        stage.run_op(op)

        assert mock_alarm.cancel.call_count == 1
        assert mock_timer.cancel.call_count == 1
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

    @pytest.mark.it("Simply sends the operation down if no alarm or timer exists")
    def test_no_timer(self, mocker, stage, op):
        assert stage._token_update_alarm is None
        assert stage._reauth_retry_timer is None
        assert stage.send_op_down.call_count == 0

        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe(
    "SasTokenStage - OCCURRENCE: SasToken Update Alarm expires (Renew Token - RenewableSasToken)"
)
class TestSasTokenStageOCCURRENCEUpdateAlarmExpiresRenewToken(SasTokenStageTestConfig):
    @pytest.fixture
    def init_op(self, mocker):
        return pipeline_ops_base.InitializePipelineOperation(callback=mocker.MagicMock())

    @pytest.fixture
    def sastoken(self, mocker):
        # Renewable Token
        mock_signing_mechanism = mocker.MagicMock()
        mock_signing_mechanism.sign.return_value = fake_signed_data
        sastoken = st.RenewableSasToken(uri=fake_uri, signing_mechanism=mock_signing_mechanism)
        sastoken.refresh = mocker.MagicMock()
        return sastoken

    @pytest.mark.it("Refreshes the pipeline's SasToken")
    @pytest.mark.parametrize(
        "connected",
        [
            pytest.param(True, id="Pipeline connected"),
            pytest.param(False, id="Pipeline not connected"),
        ],
    )
    def test_refresh_token(self, stage, init_op, mock_alarm, connected):
        # Apply the alarm
        stage.run_op(init_op)

        # Set connected state
        stage.pipeline_root.connected = connected

        # Token has not been refreshed
        token = stage.pipeline_root.pipeline_configuration.sastoken
        assert token.refresh.call_count == 0
        assert mock_alarm.call_count == 1

        # Call alarm complete callback (as if alarm expired)
        on_alarm_complete = mock_alarm.call_args[0][1]
        on_alarm_complete()

        # Token has now been refreshed
        assert token.refresh.call_count == 1

    @pytest.mark.it(
        "Reports any SasTokenError that occurs while refreshing the SasToken as a background exception"
    )
    @pytest.mark.parametrize(
        "connected",
        [
            pytest.param(True, id="Pipeline connected"),
            pytest.param(False, id="Pipeline not connected"),
        ],
    )
    def test_refresh_token_fail(self, mocker, stage, init_op, mock_alarm, connected):
        # Apply the alarm
        stage.run_op(init_op)

        # Set connected state
        stage.pipeline_root.connected = connected

        # Mock refresh
        token = stage.pipeline_root.pipeline_configuration.sastoken
        refresh_failure = st.SasTokenError()
        token.refresh = mocker.MagicMock(side_effect=refresh_failure)
        assert token.refresh.call_count == 0
        assert stage.report_background_exception.call_count == 0

        # Call alarm complete callback (as if alarm expired)
        on_alarm_complete = mock_alarm.call_args[0][1]
        on_alarm_complete()

        assert token.refresh.call_count == 1
        assert stage.report_background_exception.call_count == 1
        assert stage.report_background_exception.call_args == mocker.call(refresh_failure)

    @pytest.mark.it("Cancels any reauth retry timer that may exist")
    @pytest.mark.parametrize(
        "connected",
        [
            pytest.param(True, id="Pipeline connected"),
            pytest.param(False, id="Pipeline not connected"),
        ],
    )
    def test_cancels_reauth_retry(self, mocker, stage, init_op, mock_alarm, connected):
        # Apply the alarm
        stage.run_op(init_op)
        assert mock_alarm.call_count == 1

        # Set connected state and mock timer
        mock_timer = mocker.MagicMock()
        stage._reauth_retry_timer = mock_timer
        stage.pipeline_root.connected = connected

        # Call alarm complete callback (as if alarm expired)
        on_alarm_complete = mock_alarm.call_args[0][1]
        on_alarm_complete()

        # The mock timer has been cancelled and unset
        assert mock_timer.cancel.call_count == 1
        stage._reauth_retry_timer is None

    @pytest.mark.it(
        "Sends a ReauthorizeConnectionOperation down the pipeline if the pipeline is in a 'connected' state"
    )
    def test_when_pipeline_connected(self, mocker, stage, init_op, mock_alarm):
        # Apply the alarm and set stage as connected
        stage.pipeline_root.connected = True
        stage.run_op(init_op)

        # Only the InitializePipeline init_op has been sent down
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(init_op)

        # Pipeline is still connected
        assert stage.pipeline_root.connected is True

        # Call alarm complete callback (as if alarm expired)
        assert mock_alarm.call_count == 1
        on_alarm_complete = mock_alarm.call_args[0][1]
        on_alarm_complete()

        # ReauthorizeConnectionOperation has now been sent down
        assert stage.send_op_down.call_count == 2
        assert isinstance(
            stage.send_op_down.call_args[0][0], pipeline_ops_base.ReauthorizeConnectionOperation
        )

    @pytest.mark.it(
        "Does NOT send a ReauthorizeConnectionOperation down the pipeline if the pipeline is NOT in a 'connected' state"
    )
    def test_when_pipeline_not_connected(self, mocker, stage, init_op, mock_alarm):
        # Apply the alarm and set stage as connected
        stage.pipeline_root.connected = False
        stage.run_op(init_op)

        # Only the InitializePipeline init_op has been sent down
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(init_op)

        # Pipeline is still NOT connected
        assert stage.pipeline_root.connected is False

        # Call alarm complete callback (as if alarm expired)
        on_alarm_complete = mock_alarm.call_args[0][1]
        on_alarm_complete()

        # No further ops have been sent down
        assert stage.send_op_down.call_count == 1

    @pytest.mark.it(
        "Begins a new SasToken update alarm that will trigger 'Update Margin' number of seconds prior to the refreshed SasToken expiration"
    )
    @pytest.mark.parametrize(
        "connected",
        [
            pytest.param(True, id="Pipeline connected"),
            pytest.param(False, id="Pipeline not connected"),
        ],
    )
    # I am sorry for this test length, but IDK how else to test this...
    # ... other than throwing everything at it at once
    def test_new_alarm(self, mocker, stage, init_op, mock_alarm, connected):
        token = stage.pipeline_root.pipeline_configuration.sastoken

        # Set connected state
        stage.pipeline_root.connected = connected

        # Apply the alarm
        stage.run_op(init_op)

        # init_op was passed down
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(init_op)

        # Only one alarm has been created and started. No cancellation.
        assert mock_alarm.call_count == 1
        assert mock_alarm.return_value.start.call_count == 1
        assert mock_alarm.return_value.cancel.call_count == 0

        # Call alarm complete callback (as if alarm expired)
        on_alarm_complete = mock_alarm.call_args[0][1]
        on_alarm_complete()

        # Existing alarm was cancelled
        assert mock_alarm.return_value.cancel.call_count == 1

        # Token was refreshed
        assert token.refresh.call_count == 1

        # Reauthorize was sent down (if the connection state was right)
        if connected:
            assert stage.send_op_down.call_count == 2
            assert isinstance(
                stage.send_op_down.call_args[0][0], pipeline_ops_base.ReauthorizeConnectionOperation
            )
        else:
            assert stage.send_op_down.call_count == 1

        # Another alarm was created and started for the expected time
        assert mock_alarm.call_count == 2
        expected_alarm_time = (
            stage.pipeline_root.pipeline_configuration.sastoken.expiry_time
            - pipeline_stages_base.SasTokenStage.DEFAULT_TOKEN_UPDATE_MARGIN
        )
        assert mock_alarm.call_args[0][0] == expected_alarm_time
        assert stage._token_update_alarm is mock_alarm.return_value
        assert stage._token_update_alarm.daemon is True
        assert stage._token_update_alarm.start.call_count == 2
        assert stage._token_update_alarm.start.call_args == mocker.call()

        # When THAT alarm expires, the token is refreshed, and the reauth is sent, etc. etc. etc.
        # ... recursion :)
        new_on_alarm_complete = mock_alarm.call_args[0][1]
        new_on_alarm_complete()

        assert token.refresh.call_count == 2
        if connected:
            assert stage.send_op_down.call_count == 3
            assert isinstance(
                stage.send_op_down.call_args[0][0], pipeline_ops_base.ReauthorizeConnectionOperation
            )
        else:
            assert stage.send_op_down.call_count == 1

        assert mock_alarm.call_count == 3
        # .... and on and on for infinity

    @pytest.mark.it(
        "Begins a new SasToken update alarm that will instead trigger after MAX_TIMEOUT seconds if the refreshed SasToken expiration time (less the Update Margin) is more than MAX_TIMEOUT seconds in the future"
    )
    @pytest.mark.parametrize(
        "connected",
        [
            pytest.param(True, id="Pipeline connected"),
            pytest.param(False, id="Pipeline not connected"),
        ],
    )
    # I am sorry for this test length, but IDK how else to test this...
    # ... other than throwing everything at it at once
    def test_new_alarm_long_expiry(self, mocker, stage, init_op, mock_alarm, connected):
        token = stage.pipeline_root.pipeline_configuration.sastoken
        # Manually change the token TTL and expiry time to exceed max timeout
        # Note that time.time() is implicitly mocked to return a constant value
        token.ttl = threading.TIMEOUT_MAX + 3600
        token._expiry_time = int(time.time() + token.ttl)

        # Set connected state
        stage.pipeline_root.connected = connected

        # Apply the alarm
        stage.run_op(init_op)

        # init_op was passed down
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(init_op)

        # Only one alarm has been created and started. No cancellation.
        assert mock_alarm.call_count == 1
        assert mock_alarm.return_value.start.call_count == 1
        assert mock_alarm.return_value.cancel.call_count == 0

        # Call alarm complete callback (as if alarm expired)
        on_alarm_complete = mock_alarm.call_args[0][1]
        on_alarm_complete()

        # Existing alarm was cancelled
        assert mock_alarm.return_value.cancel.call_count == 1

        # Token was refreshed
        assert token.refresh.call_count == 1

        # Reauthorize was sent down (if the connection state was right)
        if connected:
            assert stage.send_op_down.call_count == 2
            assert isinstance(
                stage.send_op_down.call_args[0][0], pipeline_ops_base.ReauthorizeConnectionOperation
            )
        else:
            assert stage.send_op_down.call_count == 1

        # Another alarm was created and started for the expected time
        assert mock_alarm.call_count == 2
        # NOTE: time.time() is implicitly mocked to return a constant test value here
        expected_alarm_time = time.time() + threading.TIMEOUT_MAX
        assert mock_alarm.call_args[0][0] == expected_alarm_time
        assert stage._token_update_alarm is mock_alarm.return_value
        assert stage._token_update_alarm.daemon is True
        assert stage._token_update_alarm.start.call_count == 2
        assert stage._token_update_alarm.start.call_args == mocker.call()

        # When THAT alarm expires, the token is refreshed, and the reauth is sent, etc. etc. etc.
        # ... recursion :)
        new_on_alarm_complete = mock_alarm.call_args[0][1]
        new_on_alarm_complete()

        assert token.refresh.call_count == 2
        if connected:
            assert stage.send_op_down.call_count == 3
            assert isinstance(
                stage.send_op_down.call_args[0][0], pipeline_ops_base.ReauthorizeConnectionOperation
            )
        else:
            assert stage.send_op_down.call_count == 1

        assert mock_alarm.call_count == 3
        # .... and on and on for infinity


@pytest.mark.describe(
    "SasTokenStage - OCCURRENCE: SasToken Update Alarm expires (Replace Token - NonRenewableSasToken)"
)
class TestSasTokenStageOCCURRENCEUpdateAlarmExpiresReplaceToken(SasTokenStageTestConfig):
    @pytest.fixture
    def init_op(self, mocker):
        return pipeline_ops_base.InitializePipelineOperation(callback=mocker.MagicMock())

    @pytest.fixture
    def sastoken(self, mocker):
        # Non-Renewable Token
        token_str = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
            resource=fake_uri, signature=fake_signed_data, expiry=fake_expiry
        )
        sastoken = st.NonRenewableSasToken(token_str)
        return sastoken

    @pytest.mark.it("Sends a NewSasTokenRequiredEvent up the pipeline")
    @pytest.mark.parametrize(
        "connected",
        [
            pytest.param(True, id="Pipeline connected"),
            pytest.param(False, id="Pipeline not connected"),
        ],
    )
    def test_sends_event(self, stage, init_op, mock_alarm, connected):
        # Set connected state
        stage.pipeline_root.connected = connected
        # Apply the alarm
        stage.run_op(init_op)
        # Alarm was created
        assert mock_alarm.call_count == 1
        # No events have been sent up the pipeline
        assert stage.send_event_up.call_count == 0

        # Call alarm complete callback (as if alarm expired)
        on_alarm_complete = mock_alarm.call_args[0][1]
        on_alarm_complete()

        # Event was sent up
        assert stage.send_event_up.call_count == 1
        assert isinstance(
            stage.send_event_up.call_args[0][0], pipeline_events_base.NewSasTokenRequiredEvent
        )


# NOTE: base tests for reauth fail suites. Reauth can be generated by two different conditions
# but need separate test classes for them, even though the tests themselves are the same
class SasTokenStageOCCURRENCEReuathorizeConnectionOperationFailsTests(SasTokenStageTestConfig):
    @pytest.fixture
    def sastoken(self, mocker):
        # Renewable Token
        mock_signing_mechanism = mocker.MagicMock()
        mock_signing_mechanism.sign.return_value = fake_signed_data
        sastoken = st.RenewableSasToken(uri=fake_uri, signing_mechanism=mock_signing_mechanism)
        sastoken.refresh = mocker.MagicMock()
        return sastoken

    # NOTE: you must implement a "reauth_op" fixture in subclass for these tests to run

    @pytest.mark.it("Reports a background exception")
    @pytest.mark.parametrize(
        "connected",
        [
            pytest.param(True, id="Pipeline Connected"),  # NOTE: this probably would never happen
            pytest.param(False, id="Pipeline Disconnected"),
        ],
    )
    @pytest.mark.parametrize(
        "connection_retry",
        [
            pytest.param(True, id="Connection Retry Enabled"),
            pytest.param(False, id="Connection Retry Disabled"),
        ],
    )
    def test_reports_background_exception(
        self, mocker, stage, reauth_op, arbitrary_exception, connected, connection_retry
    ):
        assert stage.report_background_exception.call_count == 0

        # Set the connection state and retry feature
        stage.pipeline_root.connected = connected
        stage.pipeline_root.connection_retry = connection_retry

        # Complete ReauthorizeConnectionOperation with error
        reauth_op.complete(error=arbitrary_exception)

        # Error was sent to background handler
        assert stage.report_background_exception.call_count == 1
        assert stage.report_background_exception.call_args == mocker.call(arbitrary_exception)

    @pytest.mark.it(
        "Starts a reauth retry timer for the connection retry interval if the pipeline is not connected and connection retry is enabled on the pipeline"
    )
    def test_starts_retry_timer(self, mocker, stage, reauth_op, arbitrary_exception, mock_timer):
        stage.pipeline_root.connected = False
        stage.pipeline_root.pipeline_configuration.connection_retry = True

        assert mock_timer.call_count == 0

        reauth_op.complete(error=arbitrary_exception)

        assert mock_timer.call_count == 1
        assert mock_timer.call_args == mocker.call(
            stage.pipeline_root.pipeline_configuration.connection_retry_interval, mocker.ANY
        )
        assert mock_timer.return_value.start.call_count == 1
        assert mock_timer.return_value.start.call_args == mocker.call()
        assert mock_timer.return_value.daemon is True


@pytest.mark.describe(
    "SasTokenStage - OCCURRENCE: ReauthorizeConnectionOperation sent by SasToken Update Alarm fails"
)
class TestSasTokenStageOCCURRENCEReauthorizeConnectionOperationFromAlarmFails(
    SasTokenStageOCCURRENCEReuathorizeConnectionOperationFailsTests
):
    @pytest.fixture
    def reauth_op(self, mocker, stage, mock_alarm):
        # Initialize the pipeline
        stage.pipeline_root.connected = True
        init_op = pipeline_ops_base.InitializePipelineOperation(callback=mocker.MagicMock())
        stage.run_op(init_op)

        # Call alarm complete callback (as if alarm expired)
        assert mock_alarm.call_count == 1
        on_alarm_complete = mock_alarm.call_args[0][1]
        on_alarm_complete()

        # ReauthorizeConnectionOperation has now been sent down
        assert stage.send_op_down.call_count == 2
        reauth_op = stage.send_op_down.call_args[0][0]
        assert isinstance(reauth_op, pipeline_ops_base.ReauthorizeConnectionOperation)

        # Reset mocks
        mock_alarm.reset_mock()
        return reauth_op


@pytest.mark.describe("SasTokenStage - OCCURRENCE: Reauth Retry Timer expires")
class TestSasTokenStageOCCURRENCEReauthRetryTimerExpires(SasTokenStageTestConfig):
    @pytest.fixture
    def init_op(self, mocker):
        return pipeline_ops_base.InitializePipelineOperation(callback=mocker.MagicMock())

    @pytest.fixture
    def sastoken(self, mocker):
        # Renewable Token
        mock_signing_mechanism = mocker.MagicMock()
        mock_signing_mechanism.sign.return_value = fake_signed_data
        sastoken = st.RenewableSasToken(uri=fake_uri, signing_mechanism=mock_signing_mechanism)
        sastoken.refresh = mocker.MagicMock()
        return sastoken

    @pytest.mark.it(
        "Sends a ReauthorizeConnectionOperation down the pipeline if the pipeline is still not connected"
    )
    def test_while_disconnected(
        self, mocker, stage, init_op, mock_alarm, mock_timer, arbitrary_exception
    ):
        # Initialize stage with alarm
        stage.pipeline_root.connected = True
        stage.pipeline_root.pipeline_configuration.connection_retry = True
        stage.run_op(init_op)

        # Only the InitializePipeline op has been sent down
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(init_op)

        # Pipeline is still connected
        assert stage.pipeline_root.connected is True

        # Call alarm complete callback (as if alarm expired)
        assert mock_alarm.call_count == 1
        assert stage._token_update_alarm is mock_alarm.return_value
        on_alarm_complete = mock_alarm.call_args[0][1]
        on_alarm_complete()

        # First ReauthorizeConnectionOperation has now been sent down
        assert stage.send_op_down.call_count == 2
        reauth_op = stage.send_op_down.call_args[0][0]
        assert isinstance(reauth_op, pipeline_ops_base.ReauthorizeConnectionOperation)

        # Complete the ReauthorizeConnectionOperation with failure, triggering retry
        stage.pipeline_root.connected = False
        reauth_op.complete(error=arbitrary_exception)

        # Call timer complete callback (as if timer expired)
        assert mock_timer.call_count == 1
        assert stage._reauth_retry_timer is mock_timer.return_value
        assert stage.pipeline_root.connected is False
        on_timer_complete = mock_timer.call_args[0][1]
        on_timer_complete()

        # ReauthorizeConnectionOperation has now been sent down
        assert stage.send_op_down.call_count == 3
        reauth_op = stage.send_op_down.call_args[0][0]
        assert isinstance(reauth_op, pipeline_ops_base.ReauthorizeConnectionOperation)

    @pytest.mark.it(
        "Does not send a ReauthorizeConnectionOperation if the pipeline is now connected"
    )
    def test_while_connected(
        self, mocker, stage, init_op, mock_alarm, mock_timer, arbitrary_exception
    ):
        # Initialize stage with alarm
        stage.pipeline_root.connected = True
        stage.pipeline_root.pipeline_configuration.connection_retry = True
        stage.run_op(init_op)

        # Only the InitializePipeline op has been sent down
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(init_op)

        # Pipeline is still connected
        assert stage.pipeline_root.connected is True

        # Call alarm complete callback (as if alarm expired)
        assert mock_alarm.call_count == 1
        assert stage._token_update_alarm is mock_alarm.return_value
        on_alarm_complete = mock_alarm.call_args[0][1]
        on_alarm_complete()

        # First ReauthorizeConnectionOperation has now been sent down
        assert stage.send_op_down.call_count == 2
        reauth_op = stage.send_op_down.call_args[0][0]
        assert isinstance(reauth_op, pipeline_ops_base.ReauthorizeConnectionOperation)

        # Complete the ReauthorizeConnectionOperation with failure, triggering retry
        stage.pipeline_root.connected = False
        reauth_op.complete(error=arbitrary_exception)

        # Call timer complete callback (as if timer expired)
        assert mock_timer.call_count == 1
        assert stage._reauth_retry_timer is mock_timer.return_value
        stage.pipeline_root.connected = True  # Re-establish before timer completes
        on_timer_complete = mock_timer.call_args[0][1]
        on_timer_complete()

        # Nothing else been sent down
        assert stage.send_op_down.call_count == 2


@pytest.mark.describe(
    "SasTokenStage - OCCURRENCE: ReauthorizeConnectionOperation sent by Reauth Retry Timer fails"
)
class TestSasTokenStageOCCURRENCEReauthorizeConnectionOperationFromTimerFails(
    SasTokenStageOCCURRENCEReuathorizeConnectionOperationFailsTests
):
    @pytest.fixture
    def reauth_op(self, mocker, stage, mock_alarm, mock_timer, arbitrary_exception):
        # Initialize the pipeline
        stage.pipeline_root.connected = True
        init_op = pipeline_ops_base.InitializePipelineOperation(callback=mocker.MagicMock())
        stage.run_op(init_op)

        # Call alarm complete callback (as if alarm expired)
        assert mock_alarm.call_count == 1
        on_alarm_complete = mock_alarm.call_args[0][1]
        on_alarm_complete()

        # ReauthorizeConnectionOperation has now been sent down
        assert stage.send_op_down.call_count == 2
        reauth_op = stage.send_op_down.call_args[0][0]
        assert isinstance(reauth_op, pipeline_ops_base.ReauthorizeConnectionOperation)

        # Complete the ReauthorizeConnectionOperation with failure, triggering retry
        stage.pipeline_root.connected = False
        reauth_op.complete(error=arbitrary_exception)

        # Call timer complete callback (as if timer expired)
        assert mock_timer.call_count == 1
        assert stage._reauth_retry_timer is mock_timer.return_value
        assert stage.pipeline_root.connected is False
        assert stage.report_background_exception.call_count == 1
        on_timer_complete = mock_timer.call_args[0][1]
        on_timer_complete()

        # ReauthorizeConnectionOperation has now been sent down
        assert stage.send_op_down.call_count == 3
        reauth_op = stage.send_op_down.call_args[0][0]
        assert isinstance(reauth_op, pipeline_ops_base.ReauthorizeConnectionOperation)

        # Reset mocks
        mock_timer.reset_mock()
        mock_alarm.reset_mock()
        stage.report_background_exception.reset_mock()
        return reauth_op


######################
# AUTO CONNECT STAGE #
######################


class AutoConnectStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_base.AutoConnectStage

    @pytest.fixture
    def init_kwargs(self, mocker):
        return {}

    @pytest.fixture
    def pl_config(self, mocker):
        pl_cfg = mocker.MagicMock()
        pl_cfg.auto_connect = True
        return pl_cfg

    @pytest.fixture
    def stage(self, mocker, pl_config, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=pl_config
        )
        # Mock flow methods
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")
        return stage


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_base.AutoConnectStage,
    stage_test_config_class=AutoConnectStageTestConfig,
)


@pytest.mark.describe(
    "AutoConnectStage - .run_op() -- Called with an Operation that requires an active connection (pipeline already connected)"
)
class TestAutoConnectStageRunOpWithOpThatRequiresConnectionPipelineConnected(
    AutoConnectStageTestConfig, StageRunOpTestBase
):

    fake_topic = "__fake_topic__"
    fake_payload = "__fake_payload__"

    ops_requiring_connection = [
        pipeline_ops_mqtt.MQTTPublishOperation,
        pipeline_ops_mqtt.MQTTSubscribeOperation,
        pipeline_ops_mqtt.MQTTUnsubscribeOperation,
    ]

    @pytest.fixture(params=ops_requiring_connection)
    def op(self, mocker, request):
        op_class = request.param
        if op_class is pipeline_ops_mqtt.MQTTPublishOperation:
            op = op_class(
                topic=self.fake_topic, payload=self.fake_payload, callback=mocker.MagicMock()
            )
        else:
            op = op_class(topic=self.fake_topic, callback=mocker.MagicMock())
        assert op.needs_connection
        return op

    @pytest.mark.it("Immediately sends the operation down the pipeline")
    def test_already_connected(self, mocker, stage, op):
        stage.pipeline_root.connected = True

        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe(
    "AutoConnectStage - .run_op() -- Called with an Operation that requires an active connection (pipeline not connected)"
)
class TestAutoConnectStageRunOpWithOpThatRequiresConnectionNotConnected(
    AutoConnectStageTestConfig, StageRunOpTestBase
):

    fake_topic = "__fake_topic__"
    fake_payload = "__fake_payload__"

    ops_requiring_connection = [
        pipeline_ops_mqtt.MQTTPublishOperation,
        pipeline_ops_mqtt.MQTTSubscribeOperation,
        pipeline_ops_mqtt.MQTTUnsubscribeOperation,
    ]

    @pytest.fixture(params=ops_requiring_connection)
    def op(self, mocker, request):
        op_class = request.param
        if op_class is pipeline_ops_mqtt.MQTTPublishOperation:
            op = op_class(
                topic=self.fake_topic, payload=self.fake_payload, callback=mocker.MagicMock()
            )
        else:
            op = op_class(topic=self.fake_topic, callback=mocker.MagicMock())
        assert op.needs_connection
        return op

    @pytest.mark.it("Sends a new ConnectOperation down the pipeline")
    def test_not_connected(self, mocker, stage, op):
        mock_connect_op = mocker.patch.object(pipeline_ops_base, "ConnectOperation").return_value
        stage.pipeline_root.connected = False

        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(mock_connect_op)

    @pytest.mark.it(
        "Sends the operation down the pipeline once the ConnectOperation completes successfully"
    )
    def test_connect_success(self, mocker, stage, op):
        stage.pipeline_root.connected = False
        mocker.spy(stage, "run_op")

        # Run the original operation
        stage.run_op(op)
        assert not op.completed

        # Complete the newly created ConnectOperation that was sent down the pipeline
        assert stage.send_op_down.call_count == 1
        connect_op = stage.send_op_down.call_args[0][0]
        assert isinstance(connect_op, pipeline_ops_base.ConnectOperation)
        assert not connect_op.completed
        connect_op.complete()  # no error

        # The original operation has now been sent down the pipeline
        assert stage.run_op.call_count == 2
        assert stage.run_op.call_args == mocker.call(op)

    @pytest.mark.it(
        "Completes the operation with the error from the ConnectOperation, if the ConnectOperation completes with an error"
    )
    def test_connect_failure(self, mocker, stage, op, arbitrary_exception):
        stage.pipeline_root.connected = False

        # Run the original operation
        stage.run_op(op)
        assert not op.completed

        # Complete the newly created ConnectOperation that was sent down the pipeline
        assert stage.send_op_down.call_count == 1
        connect_op = stage.send_op_down.call_args[0][0]
        assert isinstance(connect_op, pipeline_ops_base.ConnectOperation)
        assert not connect_op.completed
        connect_op.complete(error=arbitrary_exception)  # completes with error

        # The original operation has been completed the exception from the ConnectOperation
        assert op.completed
        assert op.error is arbitrary_exception


@pytest.mark.describe(
    "AutoConnectStage - .run_op() -- Called with an Operation that does not require an active connection"
)
class TestAutoConnectStageRunOpWithOpThatDoesNotRequireConnection(
    AutoConnectStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, arbitrary_op):
        assert not arbitrary_op.needs_connection
        return arbitrary_op

    @pytest.mark.it(
        "Sends the operation down the pipeline if the pipeline is in a 'connected' state"
    )
    def test_connected(self, mocker, stage, op):
        stage.pipeline_root.connected = True

        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

    @pytest.mark.it(
        "Sends the operation down the pipeline if the pipeline is in a 'disconnected' state"
    )
    def test_disconnected(self, mocker, stage, op):
        assert not stage.pipeline_root.connected

        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe(
    "AutoConnectStage - .run_op() -- Called while pipeline configured to disable Auto Connect"
)
class TestAutoConnectStageRunOpWithAutoConnectDisabled(
    AutoConnectStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def pl_config(self, mocker):
        pl_cfg = mocker.MagicMock()
        pl_cfg.auto_connect = False
        return pl_cfg

    @pytest.fixture(params=["Op requires connection", "Op does NOT require connection"])
    def op(self, request, arbitrary_op):
        if request.param == "Op requires connection":
            arbitrary_op.needs_connection = True
        else:
            arbitrary_op.needs_connection = False
        return arbitrary_op

    @pytest.mark.it(
        "Sends the operation down the pipeline if the pipeline is in a 'connected' state"
    )
    def test_connected(self, mocker, stage, op):
        stage.pipeline_root.connected = True

        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

    @pytest.mark.it(
        "Sends the operation down the pipeline if the pipeline is in a 'disconnected' state"
    )
    def test_disconnected(self, mocker, stage, op):
        assert not stage.pipeline_root.connected

        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


#########################
# CONNECTION LOCK STAGE #
#########################

# This is a list of operations which can trigger a block on the ConnectionLockStage
connection_ops = [
    pipeline_ops_base.ConnectOperation,
    pipeline_ops_base.DisconnectOperation,
    pipeline_ops_base.ReauthorizeConnectionOperation,
]


class ConnectionLockStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_base.ConnectionLockStage

    @pytest.fixture
    def init_kwargs(self, mocker):
        return {}

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")
        return stage


class ConnectionLockStageInstantiationTests(ConnectionLockStageTestConfig):
    @pytest.mark.it("Initializes 'queue' as an empty Queue object")
    def test_queue(self, init_kwargs):
        stage = pipeline_stages_base.ConnectionLockStage(**init_kwargs)
        assert isinstance(stage.queue, queue.Queue)
        assert stage.queue.empty()

    @pytest.mark.it("Initializes 'blocked' as False")
    def test_blocked(self, init_kwargs):
        stage = pipeline_stages_base.ConnectionLockStage(**init_kwargs)
        assert not stage.blocked


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_base.ConnectionLockStage,
    stage_test_config_class=ConnectionLockStageTestConfig,
    extended_stage_instantiation_test_class=ConnectionLockStageInstantiationTests,
)


@pytest.mark.describe(
    "ConnectionLockStage - .run_op() -- Called with a ConnectOperation while not in a blocking state"
)
class TestConnectionLockStageRunOpWithConnectOpWhileUnblocked(
    ConnectionLockStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())

    @pytest.mark.it("Completes the operation immediately if the pipeline is already connected")
    def test_already_connected(self, mocker, stage, op):
        stage.pipeline_root.connected = True

        # Run the operation
        stage.run_op(op)

        # Operation is completed
        assert op.completed
        assert op.error is None

        # Stage is still not blocked
        assert not stage.blocked

    @pytest.mark.it(
        "Puts the stage in a blocking state and sends the operation down the pipeline, if the pipeline is not currently connected"
    )
    def test_not_connected(self, mocker, stage, op):
        stage.pipeline_root.connected = False

        # Stage is not blocked
        assert not stage.blocked

        # Run the operation
        stage.run_op(op)

        # Stage is now blocked
        assert stage.blocked

        # Operation was passed down
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

        # Operation is not yet completed
        assert not op.completed


@pytest.mark.describe(
    "ConnectionLockStage - .run_op() -- Called with a DisconnectOperation while not in a blocking state"
)
class TestConnectionLockStageRunOpWithDisconnectOpWhileUnblocked(
    ConnectionLockStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())

    @pytest.mark.it("Completes the operation immediately if the pipeline is already disconnected")
    def test_already_disconnected(self, mocker, stage, op):
        stage.pipeline_root.connected = False

        # Run the operation
        stage.run_op(op)

        # Operation is completed
        assert op.completed
        assert op.error is None

        # Stage is still not blocked
        assert not stage.blocked

    @pytest.mark.it(
        "Puts the stage in a blocking state and sends the operation down the pipeline, if the pipeline is currently connected"
    )
    def test_connected(self, mocker, stage, op):
        stage.pipeline_root.connected = True

        # Stage is not blocked
        assert not stage.blocked

        # Run the operation
        stage.run_op(op)

        # Stage is now blocked
        assert stage.blocked

        # Operation was passed down
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

        # Operation is not yet completed
        assert not op.completed


@pytest.mark.describe(
    "ConnectionLockStage - .run_op() -- Called with a ReauthorizeConnectionOperation while not in a blocking state"
)
class TestConnectionLockStageRunOpWithReconnectOpWhileUnblocked(
    ConnectionLockStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ReauthorizeConnectionOperation(callback=mocker.MagicMock())

    @pytest.mark.it("Puts the stage in a blocking state and sends the operation down the pipeline")
    @pytest.mark.parametrize(
        "connected",
        [
            pytest.param(True, id="Pipeline Connected"),
            pytest.param(False, id="Pipeline Disconnected"),
        ],
    )
    def test_not_connected(self, mocker, connected, stage, op):
        stage.pipeline_root.connected = connected

        # Stage is not blocked
        assert not stage.blocked

        # Run the operation
        stage.run_op(op)

        # Stage is now blocked
        assert stage.blocked

        # Operation was passed down
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

        # Operation is not yet completed
        assert not op.completed


@pytest.mark.describe(
    "ConnectionLockStage - .run_op() -- Called with an arbitrary other operation while not in a blocking state"
)
class TestConnectionLockStageRunOpWithArbitraryOpWhileUnblocked(
    ConnectionLockStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down the pipeline")
    @pytest.mark.parametrize(
        "connected",
        [
            pytest.param(True, id="Pipeline Connected"),
            pytest.param(False, id="Pipeline Disconnected"),
        ],
    )
    def test_sends_down(self, mocker, connected, stage, op):
        stage.pipeline_root.connected = connected

        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe("ConnectionLockStage - .run_op() -- Called while in a blocking state")
class TestConnectionLockStageRunOpWhileBlocked(ConnectionLockStageTestConfig, StageRunOpTestBase):
    @pytest.fixture
    def blocking_op(self, mocker):
        return pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())

    @pytest.fixture
    def stage(self, mocker, init_kwargs, blocking_op):
        stage = pipeline_stages_base.ConnectionLockStage(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")
        mocker.spy(stage, "run_op")
        assert not stage.blocked

        # Block the stage by running a blocking operation
        stage.run_op(blocking_op)
        assert stage.blocked

        # Reset the mock for ease of testing
        stage.send_op_down.reset_mock()
        stage.send_event_up.reset_mock()
        stage.report_background_exception.reset_mock()
        stage.run_op.reset_mock()
        return stage

    @pytest.fixture(params=(connection_ops + [ArbitraryOperation]))
    def op(self, mocker, request):
        conn_op_class = request.param
        op = conn_op_class(callback=mocker.MagicMock())
        return op

    @pytest.mark.it(
        "Adds the operation to the queue, pending the completion of the operation on which the stage is blocked"
    )
    def test_adds_to_queue(self, mocker, stage, op):
        assert stage.queue.empty()
        stage.run_op(op)

        # Operation is in queue
        assert not stage.queue.empty()
        assert stage.queue.qsize() == 1
        assert stage.queue.get(block=False) is op

        # Operation was not passed down
        assert stage.send_op_down.call_count == 0

        # Operation has not been completed
        assert not op.completed

    @pytest.mark.it(
        "Adds the operation to the queue, even if the operation's desired pipeline connection state already has been reached"
    )
    @pytest.mark.parametrize(
        "op",
        [pipeline_ops_base.ConnectOperation, pipeline_ops_base.DisconnectOperation],
        indirect=True,
    )
    def test_blocks_ops_ready_for_completion(self, mocker, stage, op):
        # Set the pipeline connection state to be the one desired by the operation.
        # If the stage were unblocked, this would lead to immediate completion of the op.
        if isinstance(op, pipeline_ops_base.ConnectOperation):
            stage.pipeline_root.connected = True
        else:
            stage.pipeline_root.connected = False

        assert stage.queue.empty()

        stage.run_op(op)

        assert not op.completed
        assert stage.queue.qsize() == 1
        assert stage.send_op_down.call_count == 0

    @pytest.mark.it(
        "Can support multiple pending operations if called multiple times during the blocking state"
    )
    def test_multiple_ops_added_to_queue(self, mocker, stage):
        assert stage.queue.empty()

        op1 = pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())
        op2 = pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())
        op3 = pipeline_ops_base.ReauthorizeConnectionOperation(callback=mocker.MagicMock())
        op4 = ArbitraryOperation(callback=mocker.MagicMock())

        stage.run_op(op1)
        stage.run_op(op2)
        stage.run_op(op3)
        stage.run_op(op4)

        # Operations have all been added to the queue
        assert not stage.queue.empty()
        assert stage.queue.qsize() == 4

        # No Operations were passed down
        assert stage.send_op_down.call_count == 0

        # No Operations have been completed
        assert not op1.completed
        assert not op2.completed
        assert not op3.completed
        assert not op4.completed


class ConnectionLockStageBlockingOpCompletedTestConfig(ConnectionLockStageTestConfig):
    @pytest.fixture(params=connection_ops)
    def blocking_op(self, mocker, request):
        op_cls = request.param
        return op_cls(callback=mocker.MagicMock())

    @pytest.fixture
    def pending_ops(self, mocker):
        op1 = ArbitraryOperation(callback=mocker.MagicMock())
        op2 = ArbitraryOperation(callback=mocker.MagicMock())
        op3 = ArbitraryOperation(callback=mocker.MagicMock())
        pending_ops = [op1, op2, op3]
        return pending_ops

    @pytest.fixture
    def blocked_stage(self, mocker, init_kwargs, blocking_op, pending_ops):
        stage = pipeline_stages_base.ConnectionLockStage(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")
        mocker.spy(stage, "run_op")
        assert not stage.blocked

        # Set the pipeline connection state to ensure op will block
        if isinstance(blocking_op, pipeline_ops_base.ConnectOperation):
            stage.pipeline_root.connected = False
        else:
            stage.pipeline_root.connected = True

        # Block the stage by running the blocking operation
        stage.run_op(blocking_op)
        assert stage.blocked

        # Add pending operations
        for op in pending_ops:
            stage.run_op(op)

        # All pending ops should be queued
        assert stage.queue.qsize() == len(pending_ops)

        # Reset the mock for ease of testing
        stage.send_op_down.reset_mock()
        stage.run_op.reset_mock()
        return stage


@pytest.mark.describe(
    "ConnectionLockStage - OCCURRENCE: Operation blocking ConnectionLockStage is completed successfully"
)
class TestConnectionLockStageBlockingOpCompletedNoError(
    ConnectionLockStageBlockingOpCompletedTestConfig
):
    @pytest.mark.it("Re-runs the pending operations in FIFO order")
    def test_blocking_op_completes_successfully(
        self, mocker, blocked_stage, pending_ops, blocking_op
    ):
        stage = blocked_stage
        # .run_op() has not yet been called
        assert stage.run_op.call_count == 0

        # Pending ops are queued in the stage
        assert stage.queue.qsize() == len(pending_ops)

        # Complete blocking op successfully
        blocking_op.complete()

        # .run_op() was called for every pending operation, in FIFO order
        assert stage.run_op.call_count == len(pending_ops)
        assert stage.run_op.call_args_list == [mocker.call(op) for op in pending_ops]

        # Note that this is only true because we are using arbitrary ops. Depending on what occurs during
        # the .run_op() calls, this could end up having items, but that case is covered by a different test
        assert stage.queue.qsize() == 0

    @pytest.mark.it("Unblocks the ConnectionLockStage prior to re-running any pending operations")
    def test_unblocks_before_rerun(self, mocker, blocked_stage, blocking_op, pending_ops):
        stage = blocked_stage
        assert stage.blocked

        def run_op_override(op):
            # Because the .run_op() invocation is called during operation completion,
            # any exceptions, including AssertionErrors will go to the background exception handler

            # Verify that the stage is not blocked during the call to .run_op()
            assert not stage.blocked

        stage.run_op = mocker.MagicMock(side_effect=run_op_override)

        blocking_op.complete()

        # Stage is still unblocked by the end of the blocking op completion
        assert not stage.blocked

        # Verify that the mock .run_op() was indeed called
        assert stage.run_op.call_count == len(pending_ops)

    @pytest.mark.it(
        "Re-queues subsequent operations, retaining their original order, if one of the re-run operations returns the ConnectionLockStage to a blocking state"
    )
    def test_unblocked_op_changes_block_state(self, mocker, stage):
        op1 = pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())
        op2 = ArbitraryOperation(callback=mocker.MagicMock())
        op3 = pipeline_ops_base.ReauthorizeConnectionOperation(callback=mocker.MagicMock())
        op4 = ArbitraryOperation(callback=mocker.MagicMock())
        op5 = ArbitraryOperation(callback=mocker.MagicMock())

        # Block the stage on op1
        assert not stage.pipeline_root.connected
        assert not stage.blocked
        stage.run_op(op1)
        assert stage.blocked
        assert stage.queue.qsize() == 0

        # Run the rest of the ops, which will be added to the queue
        stage.run_op(op2)
        stage.run_op(op3)
        stage.run_op(op4)
        stage.run_op(op5)

        # op1 is the only op that has been passed down so far
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op1)
        assert stage.queue.qsize() == 4

        # Complete op1
        op1.complete()

        # Manually set pipeline to be connected (this doesn't happen naturally due to the scope of this test)
        stage.pipeline_root.connected = True

        # op2 and op3 have now been passed down, but no others
        assert stage.send_op_down.call_count == 3
        assert stage.send_op_down.call_args_list[1] == mocker.call(op2)
        assert stage.send_op_down.call_args_list[2] == mocker.call(op3)
        assert stage.queue.qsize() == 2

        # Complete op3
        op3.complete()

        # op4 and op5 are now also passed down
        assert stage.send_op_down.call_count == 5
        assert stage.send_op_down.call_args_list[3] == mocker.call(op4)
        assert stage.send_op_down.call_args_list[4] == mocker.call(op5)
        assert stage.queue.qsize() == 0


@pytest.mark.describe(
    "ConnectionLockStage - OCCURRENCE: Operation blocking ConnectionLockStage is completed with error"
)
class TestConnectionLockStageBlockingOpCompletedWithError(
    ConnectionLockStageBlockingOpCompletedTestConfig
):
    # CT-TODO: Show that completion occurs in FIFO order
    @pytest.mark.it("Completes all pending operations with the error from the blocking operation")
    def test_blocking_op_completes_with_error(
        self, blocked_stage, pending_ops, blocking_op, arbitrary_exception
    ):
        stage = blocked_stage

        # Pending ops are not yet completed
        for op in pending_ops:
            assert not op.completed

        # Pending ops are queued in the stage
        assert stage.queue.qsize() == len(pending_ops)

        # Complete blocking op with error
        blocking_op.complete(error=arbitrary_exception)

        # Pending ops are now completed with error from blocking op
        for op in pending_ops:
            assert op.completed
            assert op.error is arbitrary_exception

        # No more pending ops in stage queue
        assert stage.queue.empty()

    @pytest.mark.it("Unblocks the ConnectionLockStage prior to completing any pending operations")
    def test_unblocks_before_complete(
        self, mocker, blocked_stage, pending_ops, blocking_op, arbitrary_exception
    ):
        stage = blocked_stage
        assert stage.blocked

        def complete_override(error=None):
            # Because this call to .complete() is called during another op's completion,
            # any exceptions, including AssertionErrors will go to the background exception handler

            # Verify that the stage is not blocked during the call to .complete()
            assert not stage.blocked

        for op in pending_ops:
            op.complete = mocker.MagicMock(side_effect=complete_override)

        # Complete the blocking op with error
        blocking_op.complete(error=arbitrary_exception)

        # Stage is still unblocked at the end of the blocking op completion
        assert not stage.blocked

        # Verify that the mock completion was called for the pending ops
        for op in pending_ops:
            assert op.complete.call_count == 1


#########################################
# COORDINATE REQUEST AND RESPONSE STAGE #
#########################################


@pytest.fixture
def fake_uuid(mocker):
    my_uuid = "0f4f876b-f445-432e-a8de-43bbd66e4668"
    uuid4_mock = mocker.patch.object(uuid, "uuid4")
    uuid4_mock.return_value.__str__.return_value = my_uuid
    return my_uuid


class CoordinateRequestAndResponseStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_base.CoordinateRequestAndResponseStage

    @pytest.fixture
    def init_kwargs(self, mocker):
        return {}

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")
        return stage


class CoordinateRequestAndResponseStageInstantiationTests(
    CoordinateRequestAndResponseStageTestConfig
):
    @pytest.mark.it("Initializes 'pending_responses' as an empty dict")
    def test_pending_responses(self, init_kwargs):
        stage = pipeline_stages_base.CoordinateRequestAndResponseStage(**init_kwargs)
        assert stage.pending_responses == {}


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_base.CoordinateRequestAndResponseStage,
    stage_test_config_class=CoordinateRequestAndResponseStageTestConfig,
    extended_stage_instantiation_test_class=CoordinateRequestAndResponseStageInstantiationTests,
)


@pytest.mark.describe(
    "CoordinateRequestAndResponseStage - .run_op() -- Called with a RequestAndResponseOperation"
)
class TestCoordinateRequestAndResponseStageRunOpWithRequestAndResponseOperation(
    CoordinateRequestAndResponseStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.RequestAndResponseOperation(
            request_type="some_request_type",
            method="SOME_METHOD",
            resource_location="some/resource/location",
            request_body="some_request_body",
            callback=mocker.MagicMock(),
        )

    @pytest.mark.it(
        "Stores the operation in the 'pending_responses' dictionary, mapped with a generated UUID"
    )
    def test_stores_op(self, mocker, stage, op, fake_uuid):
        stage.run_op(op)

        assert stage.pending_responses[fake_uuid] is op
        assert not op.completed

    @pytest.mark.it(
        "Creates and a new RequestOperation using the generated UUID and sends it down the pipeline"
    )
    def test_sends_down_new_request_op(self, mocker, stage, op, fake_uuid):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        request_op = stage.send_op_down.call_args[0][0]
        assert isinstance(request_op, pipeline_ops_base.RequestOperation)
        assert request_op.method == op.method
        assert request_op.resource_location == op.resource_location
        assert request_op.request_body == op.request_body
        assert request_op.request_type == op.request_type
        assert request_op.request_id == fake_uuid

    @pytest.mark.it(
        "Generates a unique UUID for each RequestAndResponseOperation/RequestOperation pair"
    )
    def test_unique_uuid(self, mocker, stage, op):
        op1 = op
        op2 = copy.deepcopy(op)
        op3 = copy.deepcopy(op)

        stage.run_op(op1)
        assert stage.send_op_down.call_count == 1
        uuid1 = stage.send_op_down.call_args[0][0].request_id
        stage.run_op(op2)
        assert stage.send_op_down.call_count == 2
        uuid2 = stage.send_op_down.call_args[0][0].request_id
        stage.run_op(op3)
        assert stage.send_op_down.call_count == 3
        uuid3 = stage.send_op_down.call_args[0][0].request_id

        assert uuid1 != uuid2 != uuid3
        assert stage.pending_responses[uuid1] is op1
        assert stage.pending_responses[uuid2] is op2
        assert stage.pending_responses[uuid3] is op3


@pytest.mark.describe(
    "CoordinateRequestAndResponseStage - .run_op() -- Called with an arbitrary other operation"
)
class TestCoordinateRequestAndResponseStageRunOpWithArbitraryOperation(
    CoordinateRequestAndResponseStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down the pipeline")
    def test_sends_down(self, stage, mocker, op):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe(
    "CoordinateRequestAndResponseStage - OCCURRENCE: RequestOperation tied to a stored RequestAndResponseOperation is completed"
)
class TestCoordinateRequestAndResponseStageRequestOperationCompleted(
    CoordinateRequestAndResponseStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.RequestAndResponseOperation(
            request_type="some_request_type",
            method="SOME_METHOD",
            resource_location="some/resource/location",
            request_body="some_request_body",
            callback=mocker.MagicMock(),
        )

    @pytest.mark.it(
        "Completes the associated RequestAndResponseOperation with the error from the RequestOperation and removes it from the 'pending_responses' dict, if the RequestOperation is completed unsuccessfully"
    )
    def test_request_completed_with_error(self, mocker, stage, op, arbitrary_exception):
        stage.run_op(op)
        request_op = stage.send_op_down.call_args[0][0]

        assert not op.completed
        assert not request_op.completed
        assert stage.pending_responses[request_op.request_id] is op

        request_op.complete(error=arbitrary_exception)

        # RequestAndResponseOperation has been completed with the error from the RequestOperation
        assert request_op.completed
        assert op.completed
        assert op.error is request_op.error is arbitrary_exception

        # RequestAndResponseOperation has been removed from the 'pending_responses' dict
        with pytest.raises(KeyError):
            stage.pending_responses[request_op.request_id]

    @pytest.mark.it(
        "Does not complete or remove the RequestAndResponseOperation from the 'pending_responses' dict if the RequestOperation is completed successfully"
    )
    def test_request_completed_successfully(self, mocker, stage, op, arbitrary_exception):
        stage.run_op(op)
        request_op = stage.send_op_down.call_args[0][0]

        request_op.complete()

        assert request_op.completed
        assert not op.completed
        assert stage.pending_responses[request_op.request_id] is op


@pytest.mark.describe(
    "CoordinateRequestAndResponseStage - .handle_pipeline_event() -- Called with ResponseEvent"
)
class TestCoordinateRequestAndResponseStageHandlePipelineEventWithResponseEvent(
    CoordinateRequestAndResponseStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self, fake_uuid):
        return pipeline_events_base.ResponseEvent(
            request_id=fake_uuid, status_code=200, response_body="response body"
        )

    @pytest.fixture
    def pending_op(self, mocker):
        return pipeline_ops_base.RequestAndResponseOperation(
            request_type="some_request_type",
            method="SOME_METHOD",
            resource_location="some/resource/location",
            request_body="some_request_body",
            callback=mocker.MagicMock(),
        )

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs, fake_uuid, pending_op):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.send_event_up = mocker.MagicMock()
        stage.send_op_down = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")

        # Run the pending op
        stage.run_op(pending_op)
        return stage

    @pytest.mark.it(
        "Successfully completes a pending RequestAndResponseOperation that matches the 'request_id' of the ResponseEvent, and removes it from the 'pending_responses' dictionary"
    )
    def test_completes_matching_request_and_response_operation(
        self, mocker, stage, pending_op, event, fake_uuid
    ):
        assert stage.pending_responses[fake_uuid] is pending_op
        assert not pending_op.completed

        # Handle the ResponseEvent
        assert event.request_id == fake_uuid
        stage.handle_pipeline_event(event)

        # The pending RequestAndResponseOperation is complete
        assert pending_op.completed

        # The RequestAndResponseOperation has been removed from the dictionary
        with pytest.raises(KeyError):
            stage.pending_responses[fake_uuid]

    @pytest.mark.it(
        "Sets the 'status_code' and 'response_body' attributes on the completed RequestAndResponseOperation with values from the ResponseEvent"
    )
    def test_returns_values_in_attributes(self, mocker, stage, pending_op, event):
        assert not pending_op.completed
        assert pending_op.status_code is None
        assert pending_op.response_body is None

        stage.handle_pipeline_event(event)

        assert pending_op.completed
        assert pending_op.status_code == event.status_code
        assert pending_op.response_body == event.response_body

    @pytest.mark.it(
        "Does nothing if there is no pending RequestAndResponseOperation that matches the 'request_id' of the ResponseEvent"
    )
    def test_no_matching_request_id(self, mocker, stage, pending_op, event, fake_uuid):
        assert stage.pending_responses[fake_uuid] is pending_op
        assert not pending_op.completed

        # Use a nonmatching UUID
        event.request_id = "non-matching-uuid"
        assert event.request_id != fake_uuid
        stage.handle_pipeline_event(event)

        # Nothing has changed
        assert stage.pending_responses[fake_uuid] is pending_op
        assert not pending_op.completed


@pytest.mark.describe(
    "CoordinateRequestAndResponseStage - .handle_pipeline_event() -- Called with ConnectedEvent"
)
class TestCoordinateRequestAndResponseStageHandlePipelineEventWithConnectedEvent(
    CoordinateRequestAndResponseStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self):
        return pipeline_events_base.ConnectedEvent()

    def make_new_request_response_op(self, mocker, id):
        return pipeline_ops_base.RequestAndResponseOperation(
            request_type="some_request_type",
            method="SOME_METHOD",
            resource_location="some/resource/location/{}".format(id),
            request_body="some_request_body",
            callback=mocker.MagicMock(),
        )

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.send_event_up = mocker.MagicMock()
        stage.send_op_down = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")

        return stage

    @pytest.mark.it("Sends a RequestOperation down again if that RequestOperation never completed")
    def test_request_never_completed(self, stage, event, mocker):
        op1 = self.make_new_request_response_op(mocker, "op1")

        # send it down but don't complete it
        stage.run_op(op1)
        assert stage.send_op_down.call_count == 1
        op1_guid = stage.send_op_down.call_args[0][0].request_id

        # simulate a connected event
        stage.handle_pipeline_event(event)

        # verify that it got sent again
        assert stage.send_op_down.call_count == 2
        assert isinstance(stage.send_op_down.call_args[0][0], pipeline_ops_base.RequestOperation)
        assert stage.send_op_down.call_args[0][0].request_id == op1_guid

    @pytest.mark.it(
        "Sends a RequestOperation down again if that RequestOperation completed, but no corresponding ResponseEvent was received"
    )
    def test_response_never_received(self, stage, event, mocker):
        op1 = self.make_new_request_response_op(mocker, "op1")

        # send it down and completed the RequestOperation
        stage.run_op(op1)
        assert stage.send_op_down.call_count == 1
        op1_guid = stage.send_op_down.call_args[0][0].request_id
        stage.send_op_down.call_args[0][0].complete()

        # simulate a connected event
        stage.handle_pipeline_event(event)

        # verify that it got sent again
        assert stage.send_op_down.call_count == 2
        assert isinstance(stage.send_op_down.call_args[0][0], pipeline_ops_base.RequestOperation)
        assert stage.send_op_down.call_args[0][0].request_id == op1_guid

    @pytest.mark.it(
        "Sends down multiple RequestOperations again if those RequestOperations never completed"
    )
    def test_multiple_requests_never_completed(self, stage, event, mocker):
        op1 = self.make_new_request_response_op(mocker, "op1")
        op2 = self.make_new_request_response_op(mocker, "op2")

        # send 2 ops down but don't complete them
        stage.run_op(op1)
        assert stage.send_op_down.call_count == 1
        op1_guid = stage.send_op_down.call_args[0][0].request_id

        stage.run_op(op2)
        assert stage.send_op_down.call_count == 2
        op2_guid = stage.send_op_down.call_args[0][0].request_id

        # simulate a connected event
        stage.handle_pipeline_event(event)

        # verify that 2 more RequestOperation ops were send down
        assert stage.send_op_down.call_count == 4
        assert isinstance(
            stage.send_op_down.call_args_list[0][0][0], pipeline_ops_base.RequestOperation
        )
        assert isinstance(
            stage.send_op_down.call_args_list[1][0][0], pipeline_ops_base.RequestOperation
        )

        assert (
            stage.send_op_down.call_args_list[2][0][0].request_id == op1_guid
            and stage.send_op_down.call_args_list[3][0][0].request_id == op2_guid
        ) or (
            stage.send_op_down.call_args_list[2][0][0].request_id == op2_guid
            and stage.send_op_down.call_args_list[3][0][0].request_id == op1_guid
        )

    @pytest.mark.it(
        "Sends down multiple RequestOperations again if those RequestOperations completed, but the correspondig ResponseEvents were never received"
    )
    def test_multiple_responses_never_received(self, stage, event, mocker):
        op1 = self.make_new_request_response_op(mocker, "op1")
        op2 = self.make_new_request_response_op(mocker, "op2")

        # send 2 ops down
        stage.run_op(op1)
        assert stage.send_op_down.call_count == 1
        op1_guid = stage.send_op_down.call_args[0][0].request_id

        stage.run_op(op2)
        assert stage.send_op_down.call_count == 2
        op2_guid = stage.send_op_down.call_args[0][0].request_id

        # complete the 2 RequestOperation ops
        stage.send_op_down.call_arg_list[0][0][0].complete()
        stage.send_op_down.call_arg_list[1][0][0].complete()

        # simulate a connected event
        stage.handle_pipeline_event(event)

        # verify that 2 more RequestOperation ops were send down
        assert stage.send_op_down.call_count == 4
        assert isinstance(
            stage.send_op_down.call_args_list[0][0][0], pipeline_ops_base.RequestOperation
        )
        assert isinstance(
            stage.send_op_down.call_args_list[1][0][0], pipeline_ops_base.RequestOperation
        )

        assert (
            stage.send_op_down.call_args_list[2][0][0].request_id == op1_guid
            and stage.send_op_down.call_args_list[3][0][0].request_id == op2_guid
        ) or (
            stage.send_op_down.call_args_list[2][0][0].request_id == op2_guid
            and stage.send_op_down.call_args_list[3][0][0].request_id == op1_guid
        )

    @pytest.mark.it(
        "Does not send down any RequestOperations if the RequestAndResponseOperation completed"
    )
    def test_request_and_response_completed(self, stage, event, mocker):
        op1 = self.make_new_request_response_op(mocker, "op1")

        # send it down and complete the RequestOperation op
        stage.run_op(op1)
        assert stage.send_op_down.call_count == 1
        op1_guid = stage.send_op_down.call_args[0][0].request_id
        stage.send_op_down.call_args[0][0].complete()

        # simulate the corresponding response
        response_event = pipeline_events_base.ResponseEvent(
            request_id=op1_guid, status_code=200, response_body="response body"
        )
        stage.handle_pipeline_event(response_event)

        # verify that the op is complete
        assert op1.completed

        # simulate a connected event
        stage.handle_pipeline_event(event)

        # verify that nothing else was sent
        assert stage.send_op_down.call_count == 1

    @pytest.mark.it("Can independently track and resend multiple RequestOperations")
    def test_one_completed_one_outstanding(self, stage, event, mocker):
        op1 = self.make_new_request_response_op(mocker, "op1")
        op2 = self.make_new_request_response_op(mocker, "op2")

        # send 2 ops down
        stage.run_op(op1)
        assert stage.send_op_down.call_count == 1
        op1_guid = stage.send_op_down.call_args[0][0].request_id

        stage.run_op(op2)
        assert stage.send_op_down.call_count == 2
        op2_guid = stage.send_op_down.call_args[0][0].request_id

        # complete the 2 RequestOperation ops
        stage.send_op_down.call_arg_list[0][0][0].complete()
        stage.send_op_down.call_arg_list[1][0][0].complete()

        # simulate a response for the first RequestOperation
        response_event = pipeline_events_base.ResponseEvent(
            request_id=op1_guid, status_code=200, response_body="response body"
        )
        stage.handle_pipeline_event(response_event)

        # simulate a connected event
        stage.handle_pipeline_event(event)

        # verify that the re-sent RequestOperation was sent down for the incomplete RequestAndResponseOperation
        assert stage.send_op_down.call_count == 3
        assert isinstance(stage.send_op_down.call_args[0][0], pipeline_ops_base.RequestOperation)
        assert stage.send_op_down.call_args[0][0].request_id == op2_guid

    @pytest.mark.it(
        "Does not send down any RequestOperations if all those RequestAndResponseOperations are complete"
    )
    def test_all_completed(self, stage, event, mocker):
        op1 = self.make_new_request_response_op(mocker, "op1")
        op2 = self.make_new_request_response_op(mocker, "op2")

        # send 2 ops down
        stage.run_op(op1)
        assert stage.send_op_down.call_count == 1
        op1_guid = stage.send_op_down.call_args[0][0].request_id

        stage.run_op(op2)
        assert stage.send_op_down.call_count == 2
        op2_guid = stage.send_op_down.call_args[0][0].request_id

        # complete the 2 RequestOperation ops
        stage.send_op_down.call_arg_list[0][0][0].complete()
        stage.send_op_down.call_arg_list[1][0][0].complete()

        # simulate 2 responses
        stage.handle_pipeline_event(
            pipeline_events_base.ResponseEvent(
                request_id=op1_guid, status_code=200, response_body="response body"
            )
        )
        stage.handle_pipeline_event(
            pipeline_events_base.ResponseEvent(
                request_id=op2_guid, status_code=200, response_body="response body"
            )
        )

        # simulate a connected event
        stage.handle_pipeline_event(event)

        # verify that nothing else was sent down
        assert stage.send_op_down.call_count == 2


@pytest.mark.describe(
    "CoordinateRequestAndResponseStage - .handle_pipeline_event() -- Called with arbitrary other event"
)
class TestCoordinateRequestAndResponseStageHandlePipelineEventWithArbitraryEvent(
    CoordinateRequestAndResponseStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self, arbitrary_event):
        return arbitrary_event

    @pytest.mark.it("Sends the event up the pipeline")
    def test_sends_up(self, mocker, stage, event):
        stage.handle_pipeline_event(event)

        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)


####################
# OP TIMEOUT STAGE #
####################

ops_that_time_out = [
    pipeline_ops_mqtt.MQTTSubscribeOperation,
    pipeline_ops_mqtt.MQTTUnsubscribeOperation,
]


class OpTimeoutStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_base.OpTimeoutStage

    @pytest.fixture
    def init_kwargs(self, mocker):
        return {}

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")
        return stage


class OpTimeoutStageInstantiationTests(OpTimeoutStageTestConfig):
    # TODO: this will no longer be necessary once these are implemented as part of a more robust retry policy
    @pytest.mark.it(
        "Sets default timout intervals to 10 seconds for MQTTSubscribeOperation and MQTTUnsubscribeOperation"
    )
    def test_timeout_intervals(self, init_kwargs):
        stage = pipeline_stages_base.OpTimeoutStage(**init_kwargs)
        assert stage.timeout_intervals[pipeline_ops_mqtt.MQTTSubscribeOperation] == 10
        assert stage.timeout_intervals[pipeline_ops_mqtt.MQTTUnsubscribeOperation] == 10


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_base.OpTimeoutStage,
    stage_test_config_class=OpTimeoutStageTestConfig,
    extended_stage_instantiation_test_class=OpTimeoutStageInstantiationTests,
)


@pytest.mark.describe("OpTimeoutStage - .run_op() -- Called with operation eligible for timeout")
class TestOpTimeoutStageRunOpCalledWithOpThatCanTimeout(
    OpTimeoutStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture(params=ops_that_time_out)
    def op(self, mocker, request):
        op_cls = request.param
        op = op_cls(topic="some/topic", callback=mocker.MagicMock())
        return op

    @pytest.mark.it(
        "Adds a timeout timer with the interval specified in the configuration to the operation, and starts it"
    )
    def test_adds_timer(self, mocker, stage, op, mock_timer):

        stage.run_op(op)

        assert mock_timer.call_count == 1
        assert mock_timer.call_args == mocker.call(stage.timeout_intervals[type(op)], mocker.ANY)
        assert op.timeout_timer is mock_timer.return_value
        assert op.timeout_timer.start.call_count == 1
        assert op.timeout_timer.start.call_args == mocker.call()

    @pytest.mark.it("Sends the operation down the pipeline")
    def test_sends_down(self, mocker, stage, op, mock_timer):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)
        assert op.timeout_timer is mock_timer.return_value


@pytest.mark.describe(
    "OpTimeoutStage - .run_op() -- Called with arbitrary operation that is not eligible for timeout"
)
class TestOpTimeoutStageRunOpCalledWithOpThatDoesNotTimeout(
    OpTimeoutStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down the pipeline without attaching a timeout timer")
    def test_sends_down(self, mocker, stage, op, mock_timer):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)
        assert mock_timer.call_count == 0
        assert not hasattr(op, "timeout_timer")


@pytest.mark.describe(
    "OpTimeoutStage - OCCURRENCE: Operation with a timeout timer times out before completion"
)
class TestOpTimeoutStageOpTimesOut(OpTimeoutStageTestConfig):
    @pytest.fixture(params=ops_that_time_out)
    def op(self, mocker, request):
        op_cls = request.param
        op = op_cls(topic="some/topic", callback=mocker.MagicMock())
        return op

    @pytest.mark.it("Completes the operation unsuccessfully, with a PiplineTimeoutError")
    def test_pipeline_timeout(self, mocker, stage, op, mock_timer):
        # Apply the timer
        stage.run_op(op)
        assert not op.completed
        assert mock_timer.call_count == 1
        on_timer_complete = mock_timer.call_args[0][1]

        # Call timer complete callback (indicating timer completion)
        on_timer_complete()

        # Op is now completed with error
        assert op.completed
        assert isinstance(op.error, pipeline_exceptions.OperationTimeout)


@pytest.mark.describe(
    "OpTimeoutStage - OCCURRENCE: Operation with a timeout timer completes before timeout"
)
class TestOpTimeoutStageOpCompletesBeforeTimeout(OpTimeoutStageTestConfig):
    @pytest.fixture(params=ops_that_time_out)
    def op(self, mocker, request):
        op_cls = request.param
        op = op_cls(topic="some/topic", callback=mocker.MagicMock())
        return op

    @pytest.mark.it("Cancels and clears the operation's timeout timer")
    def test_complete_before_timeout(self, mocker, stage, op, mock_timer):
        # Apply the timer
        stage.run_op(op)
        assert not op.completed
        assert mock_timer.call_count == 1
        mock_timer_inst = op.timeout_timer
        assert mock_timer_inst is mock_timer.return_value
        assert mock_timer_inst.cancel.call_count == 0

        # Complete the operation
        op.complete()

        # Timer is now cancelled and cleared
        assert mock_timer_inst.cancel.call_count == 1
        assert mock_timer_inst.cancel.call_args == mocker.call()
        assert op.timeout_timer is None


###############
# RETRY STAGE #
###############

# Tuples of classname + args
retryable_ops = [
    (pipeline_ops_mqtt.MQTTSubscribeOperation, {"topic": "fake_topic", "callback": fake_callback}),
    (
        pipeline_ops_mqtt.MQTTUnsubscribeOperation,
        {"topic": "fake_topic", "callback": fake_callback},
    ),
]

retryable_exceptions = [pipeline_exceptions.OperationTimeout]


class RetryStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_base.RetryStage

    @pytest.fixture
    def init_kwargs(self, mocker):
        return {}

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        mocker.spy(stage, "run_op")
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")
        return stage


class RetryStageInstantiationTests(RetryStageTestConfig):
    # TODO: this will no longer be necessary once these are implemented as part of a more robust retry policy
    @pytest.mark.it(
        "Sets default retry intervals to 20 seconds for MQTTSubscribeOperation and MQTTUnsubscribeOperation"
    )
    def test_retry_intervals(self, init_kwargs):
        stage = pipeline_stages_base.RetryStage(**init_kwargs)
        assert stage.retry_intervals[pipeline_ops_mqtt.MQTTSubscribeOperation] == 20
        assert stage.retry_intervals[pipeline_ops_mqtt.MQTTUnsubscribeOperation] == 20

    @pytest.mark.it("Initializes 'ops_waiting_to_retry' as an empty list")
    def test_ops_waiting_to_retry(self, init_kwargs):
        stage = pipeline_stages_base.RetryStage(**init_kwargs)
        assert stage.ops_waiting_to_retry == []


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_base.RetryStage,
    stage_test_config_class=RetryStageTestConfig,
    extended_stage_instantiation_test_class=RetryStageInstantiationTests,
)


# NOTE: Although there is a branch in the implementation that distinguishes between
# retryable operations, and non-retryable operations, with retryable operations having
# a callback added, this is not captured in this test, as callback resolution is tested
# in a different unit.
@pytest.mark.describe("RetryStage - .run_op()")
class TestRetryStageRunOp(RetryStageTestConfig, StageRunOpTestBase):
    ops = retryable_ops + [(ArbitraryOperation, {"callback": fake_callback})]

    @pytest.fixture(params=ops, ids=[x[0].__name__ for x in ops])
    def op(self, request, mocker):
        op_cls = request.param[0]
        init_kwargs = request.param[1]
        return op_cls(**init_kwargs)

    @pytest.mark.it("Sends the operation down the pipeline")
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe(
    "RetryStage - OCCURRENCE: Retryable operation completes unsuccessfully with a retryable error after call to .run_op()"
)
class TestRetryStageRetryableOperationCompletedWithRetryableError(RetryStageTestConfig):
    @pytest.fixture(params=retryable_ops, ids=[x[0].__name__ for x in retryable_ops])
    def op(self, request, mocker):
        op_cls = request.param[0]
        init_kwargs = request.param[1]
        return op_cls(**init_kwargs)

    @pytest.fixture(params=retryable_exceptions)
    def error(self, request):
        return request.param()

    @pytest.mark.it("Halts operation completion")
    def test_halt(self, mocker, stage, op, error, mock_timer):
        stage.run_op(op)
        op.complete(error=error)

        assert not op.completed

    @pytest.mark.it(
        "Adds a retry timer to the operation with the interval specified for the operation by the configuration, and starts it"
    )
    def test_timer(self, mocker, stage, op, error, mock_timer):
        stage.run_op(op)
        op.complete(error=error)

        assert mock_timer.call_count == 1
        assert mock_timer.call_args == mocker.call(stage.retry_intervals[type(op)], mocker.ANY)
        assert op.retry_timer is mock_timer.return_value
        assert op.retry_timer.start.call_count == 1
        assert op.retry_timer.start.call_args == mocker.call()

    @pytest.mark.it(
        "Adds the operation to the list of 'ops_waiting_to_retry' only for the duration of the timer"
    )
    def test_adds_to_waiting_list_during_timer(self, mocker, stage, op, error, mock_timer):
        stage.run_op(op)

        # The op is not listed as waiting for retry before completion
        assert op not in stage.ops_waiting_to_retry

        # Completing the op starts the timer
        op.complete(error=error)
        assert mock_timer.call_count == 1
        timer_callback = mock_timer.call_args[0][1]
        assert mock_timer.return_value.start.call_count == 1

        # Once completed and the timer has been started, the op IS listed as waiting for retry
        assert op in stage.ops_waiting_to_retry

        # Simulate timer completion
        timer_callback()

        # Once the timer is completed, the op is no longer listed as waiting for retry
        assert op not in stage.ops_waiting_to_retry

    @pytest.mark.it("Re-runs the operation after the retry timer expires")
    def test_reruns(self, mocker, stage, op, error, mock_timer):
        stage.run_op(op)
        op.complete(error=error)

        assert stage.run_op.call_count == 1
        assert mock_timer.call_count == 1
        timer_callback = mock_timer.call_args[0][1]

        # Simulate timer completion
        timer_callback()

        # run_op was called again
        assert stage.run_op.call_count == 2

    @pytest.mark.it("Cancels and clears the retry timer after the retry timer expires")
    def test_clears_retry_timer(self, mocker, stage, op, error, mock_timer):
        stage.run_op(op)
        op.complete(error=error)
        timer_callback = mock_timer.call_args[0][1]

        assert mock_timer.cancel.call_count == 0
        assert op.retry_timer is mock_timer.return_value

        # Simulate timer completion
        timer_callback()

        assert mock_timer.return_value.cancel.call_count == 1
        assert mock_timer.return_value.cancel.call_args == mocker.call()
        assert op.retry_timer is None

    @pytest.mark.it(
        "Adds a new retry timer to the re-run operation, if it completes unsuccessfully again"
    )
    def test_rerun_op_unsuccessful_again(self, mocker, stage, op, error, mock_timer):
        stage.run_op(op)
        assert stage.run_op.call_count == 1

        # Complete with failure the first time
        op.complete(error=error)

        assert mock_timer.call_count == 1
        assert op.retry_timer is mock_timer.return_value
        timer_callback1 = mock_timer.call_args[0][1]

        # Trigger retry
        timer_callback1()

        assert stage.run_op.call_count == 2
        assert stage.run_op.call_args == mocker.call(op)
        assert op.retry_timer is None

        # Complete with failure the second time
        op.complete(error=error)

        assert mock_timer.call_count == 2
        assert op.retry_timer is mock_timer.return_value
        timer_callback2 = mock_timer.call_args[0][1]

        # Trigger retry again
        timer_callback2()

        assert stage.run_op.call_count == 3
        assert stage.run_op.call_args == mocker.call(op)
        assert op.retry_timer is None

    @pytest.mark.it("Supports multiple simultaneous operations retrying")
    def test_multiple_retries(self, mocker, stage, mock_timer):
        op1 = pipeline_ops_mqtt.MQTTSubscribeOperation(
            topic="fake_topic_1", callback=mocker.MagicMock()
        )
        op2 = pipeline_ops_mqtt.MQTTSubscribeOperation(
            topic="fake_topic_2", callback=mocker.MagicMock()
        )
        op3 = pipeline_ops_mqtt.MQTTUnsubscribeOperation(
            topic="fake_topic_3", callback=mocker.MagicMock()
        )

        stage.run_op(op1)
        stage.run_op(op2)
        stage.run_op(op3)
        assert stage.run_op.call_count == 3

        assert not op1.completed
        assert not op2.completed
        assert not op3.completed

        op1.complete(error=pipeline_exceptions.OperationTimeout())
        op2.complete(error=pipeline_exceptions.OperationTimeout())
        op3.complete(error=pipeline_exceptions.OperationTimeout())

        # Ops halted
        assert not op1.completed
        assert not op2.completed
        assert not op3.completed

        # Timers set
        assert mock_timer.call_count == 3
        assert op1.retry_timer is mock_timer.return_value
        assert op2.retry_timer is mock_timer.return_value
        assert op3.retry_timer is mock_timer.return_value
        assert mock_timer.return_value.start.call_count == 3

        # Operations awaiting retry
        assert op1 in stage.ops_waiting_to_retry
        assert op2 in stage.ops_waiting_to_retry
        assert op3 in stage.ops_waiting_to_retry

        timer1_complete = mock_timer.call_args_list[0][0][1]
        timer2_complete = mock_timer.call_args_list[1][0][1]
        timer3_complete = mock_timer.call_args_list[2][0][1]

        # Trigger op1's timer to complete
        timer1_complete()

        # Only op1 was re-run, and had it's timer removed
        assert mock_timer.return_value.cancel.call_count == 1
        assert op1.retry_timer is None
        assert op1 not in stage.ops_waiting_to_retry
        assert op2.retry_timer is mock_timer.return_value
        assert op2 in stage.ops_waiting_to_retry
        assert op3.retry_timer is mock_timer.return_value
        assert op3 in stage.ops_waiting_to_retry
        assert stage.run_op.call_count == 4
        assert stage.run_op.call_args == mocker.call(op1)

        # Trigger op2's timer to complete
        timer2_complete()

        # Only op2 was re-run and had it's timer removed
        assert mock_timer.return_value.cancel.call_count == 2
        assert op2.retry_timer is None
        assert op2 not in stage.ops_waiting_to_retry
        assert op3.retry_timer is mock_timer.return_value
        assert op3 in stage.ops_waiting_to_retry
        assert stage.run_op.call_count == 5
        assert stage.run_op.call_args == mocker.call(op2)

        # Trigger op3's timer to complete
        timer3_complete()

        # op3 has now also been re-run and had it's timer removed
        assert op3.retry_timer is None
        assert op3 not in stage.ops_waiting_to_retry
        assert stage.run_op.call_count == 6
        assert stage.run_op.call_args == mocker.call(op3)


@pytest.mark.describe(
    "RetryStage - OCCURRENCE: Retryable operation completes unsuccessfully with a non-retryable error after call to .run_op()"
)
class TestRetryStageRetryableOperationCompletedWithNonRetryableError(RetryStageTestConfig):
    @pytest.fixture(params=retryable_ops, ids=[x[0].__name__ for x in retryable_ops])
    def op(self, request, mocker):
        op_cls = request.param[0]
        init_kwargs = request.param[1]
        return op_cls(**init_kwargs)

    @pytest.fixture
    def error(self, arbitrary_exception):
        return arbitrary_exception

    @pytest.mark.it("Completes normally without retry")
    def test_no_retry(self, mocker, stage, op, error, mock_timer):
        stage.run_op(op)
        op.complete(error=error)

        assert op.completed
        assert op not in stage.ops_waiting_to_retry
        assert mock_timer.call_count == 0

    @pytest.mark.it("Cancels and clears the operation's retry timer, if one exists")
    def test_cancels_existing_timer(self, mocker, stage, op, error, mock_timer):
        # NOTE: This shouldn't happen naturally. We have to artificially create this circumstance
        stage.run_op(op)

        # Artificially add a timer. Note that this is already mocked due to the 'mock_timer' fixture
        op.retry_timer = threading.Timer(20, fake_callback)
        assert op.retry_timer is mock_timer.return_value

        op.complete(error=error)

        assert op.completed
        assert mock_timer.return_value.cancel.call_count == 1
        assert op.retry_timer is None


@pytest.mark.describe(
    "RetryStage - OCCURRENCE: Retryable operation completes successfully after call to .run_op()"
)
class TestRetryStageRetryableOperationCompletedSuccessfully(RetryStageTestConfig):
    @pytest.fixture(params=retryable_ops, ids=[x[0].__name__ for x in retryable_ops])
    def op(self, request, mocker):
        op_cls = request.param[0]
        init_kwargs = request.param[1]
        return op_cls(**init_kwargs)

    @pytest.mark.it("Completes normally without retry")
    def test_no_retry(self, mocker, stage, op, mock_timer):
        stage.run_op(op)
        op.complete()

        assert op.completed
        assert op not in stage.ops_waiting_to_retry
        assert mock_timer.call_count == 0

    # NOTE: this isn't doing anything because arb ops don't trigger callback
    @pytest.mark.it("Cancels and clears the operation's retry timer, if one exists")
    def test_cancels_existing_timer(self, mocker, stage, op, mock_timer):
        # NOTE: This shouldn't happen naturally. We have to artificially create this circumstance
        stage.run_op(op)

        # Artificially add a timer. Note that this is already mocked due to the 'mock_timer' fixture
        op.retry_timer = threading.Timer(20, fake_callback)
        assert op.retry_timer is mock_timer.return_value

        op.complete()

        assert op.completed
        assert mock_timer.return_value.cancel.call_count == 1
        assert op.retry_timer is None


@pytest.mark.describe(
    "RetryStage - OCCURRENCE: Non-retryable operation completes after call to .run_op()"
)
class TestRetryStageNonretryableOperationCompleted(RetryStageTestConfig):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Completes normally without retry, if completed successfully")
    def test_successful_completion(self, mocker, stage, op, mock_timer):
        stage.run_op(op)
        op.complete()

        assert op.completed
        assert op not in stage.ops_waiting_to_retry
        assert mock_timer.call_count == 0

    @pytest.mark.it(
        "Completes normally without retry, if completed unsuccessfully with a non-retryable exception"
    )
    def test_unsuccessful_non_retryable_err(
        self, mocker, stage, op, arbitrary_exception, mock_timer
    ):
        stage.run_op(op)
        op.complete(error=arbitrary_exception)

        assert op.completed
        assert op not in stage.ops_waiting_to_retry
        assert mock_timer.call_count == 0

    @pytest.mark.it(
        "Completes normally without retry, if completed unsuccessfully with a retryable exception"
    )
    @pytest.mark.parametrize("exception", retryable_exceptions)
    def test_unsuccessful_retryable_err(self, mocker, stage, op, exception, mock_timer):
        stage.run_op(op)
        op.complete(error=exception)

        assert op.completed
        assert op not in stage.ops_waiting_to_retry
        assert mock_timer.call_count == 0


###################
# RECONNECT STAGE #
###################


class ReconnectStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_base.ReconnectStage

    @pytest.fixture
    def init_kwargs(self, mocker):
        return {}

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        # Majority of tests will want connection retry enabled
        stage.pipeline_root.pipeline_configuration.connection_retry = True
        stage.pipeline_root.pipeline_configuration.connection_retry_interval = 1234
        mocker.spy(stage, "run_op")
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")
        return stage


class ReconnectStageInstantiationTests(ReconnectStageTestConfig):
    @pytest.mark.it("Initializes the 'reconnect_timer' attribute as None")
    def test_reconnect_timer(self, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        assert stage.reconnect_timer is None

    @pytest.mark.it("Initializes the 'state' attribute as 'DISCONNECTED'")
    def test_state(self, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        assert stage.state == ReconnectState.DISCONNECTED

    @pytest.mark.it("Initializes the 'waiting_ops' queue")
    def test_waiting_connect_ops(self, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        assert isinstance(stage.waiting_ops, queue.Queue)
        assert stage.waiting_ops.empty()


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_base.ReconnectStage,
    stage_test_config_class=ReconnectStageTestConfig,
    extended_stage_instantiation_test_class=ReconnectStageInstantiationTests,
)


@pytest.mark.describe(
    "ReconnectStage - .run_op() -- Called with ConnectOperation (Connection Retry/Reconnect enabled)"
)
class TestReconnectStageRunOpWithConnectOperation(ReconnectStageTestConfig, StageRunOpTestBase):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())

    @pytest.mark.it(
        "Adds the operation to the `waiting_ops` queue and does nothing else if the stage is in an intermediate state"
    )
    @pytest.mark.parametrize(
        "state",
        [
            ReconnectState.CONNECTING,
            ReconnectState.DISCONNECTING,
            ReconnectState.REAUTHORIZING,
        ],
    )
    def test_intermediate_state(self, stage, op, state):
        stage.state = state
        assert stage.waiting_ops.empty()

        stage.run_op(op)

        assert not stage.waiting_ops.empty()
        assert stage.waiting_ops.qsize() == 1
        assert stage.waiting_ops.get() is op
        assert stage.send_op_down.call_count == 0

    @pytest.mark.it(
        "Sends the operation down the pipeline without changing the state if the stage is already in a CONNECTED state"
    )
    def test_connected_state_change(self, mocker, stage, op):
        stage.state = ReconnectState.CONNECTED
        stage.run_op(op)
        assert stage.state == ReconnectState.CONNECTED
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

    @pytest.mark.it(
        "Changes the state to CONNECTING and sends the operation down the pipeline if the stage is in a DISCONNECTED state"
    )
    def test_disconnected_state_change(self, mocker, stage, op):
        stage.state = ReconnectState.DISCONNECTED
        stage.run_op(op)
        assert stage.state == ReconnectState.CONNECTING
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

    @pytest.mark.it(
        "Sets the state to DISCONNECTED if the operation sent down the pipeline completes with error"
    )
    @pytest.mark.parametrize(
        "original_state, modified_state",
        [
            pytest.param(
                ReconnectState.CONNECTED, ReconnectState.CONNECTED, id="CONNECTED->CONNECTED"
            ),
            pytest.param(
                ReconnectState.DISCONNECTED,
                ReconnectState.CONNECTING,
                id="DISCONNECTED->CONNECTING",
            ),
        ],
    )
    def test_op_completes_error(
        self, stage, op, original_state, modified_state, arbitrary_exception
    ):
        stage.state = original_state
        stage.run_op(op)
        assert stage.state == modified_state

        op.complete(arbitrary_exception)

        assert stage.state == ReconnectState.DISCONNECTED

    @pytest.mark.it(
        "Does not change the state if the operation sent down the pipeline completes successfully"
    )
    @pytest.mark.parametrize(
        "original_state, modified_state",
        [
            pytest.param(
                ReconnectState.CONNECTED, ReconnectState.CONNECTED, id="CONNECTED->CONNECTED"
            ),
            pytest.param(
                ReconnectState.DISCONNECTED,
                ReconnectState.CONNECTING,
                id="DISCONNECTED->CONNECTING",
            ),
        ],
    )
    def test_op_completes_success(self, stage, op, original_state, modified_state):
        stage.state = original_state
        stage.run_op(op)
        assert stage.state == modified_state

        op.complete()

        # NOTE: This is a very weird test in that this would never happen like this "in the wild"
        # In a real scenario, prior to the operation completing, an event would fire, and that
        # event would cause a state change to the desired state, so the state would actually not
        # still be this in this "modified state" that was a result of the operation running through
        # the pipeline. However, that's kind of the important thing we need to test - that the
        # operation completing DOES NOT change the state, because that's not it's job. So in order
        # to show this, we will NOT emulate the state change that occurs from the event. Just
        # remember that in pracitce, the state would not actually still be the modified state, but
        # instead the desired goal state
        assert stage.state == modified_state

    @pytest.mark.it(
        "Re-runs all of the ops in the `waiting_ops` queue (if any) upon completion of the op after it is sent down"
    )
    @pytest.mark.parametrize(
        "queued_ops",
        [
            pytest.param(
                [pipeline_ops_base.DisconnectOperation(callback=None)], id="Single op waiting"
            ),
            pytest.param(
                [
                    pipeline_ops_base.ReauthorizeConnectionOperation(callback=None),
                    pipeline_ops_base.ConnectOperation(callback=None),
                ],
                id="Multiple ops waiting",
            ),
        ],
    )
    @pytest.mark.parametrize(
        "success",
        [
            pytest.param(True, id="Operation completes with success"),
            pytest.param(False, id="Operation completes with error"),
        ],
    )
    def test_op_completes_causes_waiting_rerun(
        self, mocker, stage, op, queued_ops, success, arbitrary_exception
    ):
        stage.state = ReconnectState.DISCONNECTED
        stage.run_op(op)
        assert stage.state == ReconnectState.CONNECTING
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

        # Before completion, more ops come down and queue up
        for queued_op in queued_ops:
            stage.run_op(queued_op)
        assert stage.waiting_ops.qsize() == len(queued_ops)

        # Now mock out run_op so we can see if it gets called
        stage.run_op = mocker.MagicMock()

        # As mentioned above, before operations complete successfully, an event will be fired,
        # and this event will trigger state change. We need to emulate this one here so that
        # the waiting ops will not end up requeued.
        if success:
            stage.state = ReconnectState.CONNECTED
            op.complete()
        else:
            op.complete(arbitrary_exception)

        # All items were removed from the waiting queue and run on the stage
        assert stage.waiting_ops.qsize() == 0
        assert stage.run_op.call_count == len(queued_ops)
        for i in range(len(queued_ops)):
            assert stage.run_op.call_args_list[i] == mocker.call(queued_ops[i])


@pytest.mark.describe(
    "ReconnectStage - .run_op() -- Called with DisconnectOperation (Connection Retry/Reconnect enabled)"
)
class TestReconnectStageRunOpWithDisconnectOperation(ReconnectStageTestConfig, StageRunOpTestBase):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())

    @pytest.mark.it(
        "Adds the operation to the `waiting_ops` queue and does nothing else if the stage is in an intermediate state"
    )
    @pytest.mark.parametrize(
        "state",
        [
            ReconnectState.CONNECTING,
            ReconnectState.DISCONNECTING,
            ReconnectState.REAUTHORIZING,
        ],
    )
    def test_intermediate_state(self, stage, op, state):
        stage.state = state
        assert stage.waiting_ops.empty()

        stage.run_op(op)

        assert not stage.waiting_ops.empty()
        assert stage.waiting_ops.qsize() == 1
        assert stage.waiting_ops.get() is op
        assert stage.send_op_down.call_count == 0

    @pytest.mark.it(
        "Clears any reconnection timer that may exist if the stage is in a stable state"
    )
    @pytest.mark.parametrize(
        "state",
        [
            ReconnectState.CONNECTED,
            ReconnectState.DISCONNECTED,
        ],
    )
    def test_clears_reconnect_timer(self, mocker, stage, op, state):
        stage.state = state
        timer_mock = mocker.MagicMock()
        stage.reconnect_timer = timer_mock

        stage.run_op(op)

        assert stage.reconnect_timer is None
        assert timer_mock.cancel.call_count == 1

    @pytest.mark.it(
        "Sends the operation down the pipeline without changing the state if the stage is already in a DISCONNECTED state"
    )
    def test_connected_state_change(self, mocker, stage, op):
        stage.state = ReconnectState.DISCONNECTED
        stage.run_op(op)
        assert stage.state == ReconnectState.DISCONNECTED
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

    @pytest.mark.it(
        "Changes the state to DISCONNECTING and sends the operation down the pipeline if the stage is in a CONNECTED state"
    )
    def test_disconnected_state_change(self, mocker, stage, op):
        stage.state = ReconnectState.CONNECTED
        stage.run_op(op)
        assert stage.state == ReconnectState.DISCONNECTING
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

    @pytest.mark.it(
        "Sets the state to DISCONNECTED if the operation sent down the pipeline completes with error"
    )
    @pytest.mark.parametrize(
        "original_state, modified_state",
        [
            pytest.param(
                ReconnectState.DISCONNECTED,
                ReconnectState.DISCONNECTED,
                id="DISCONNECTED->DISCONNECTED",
            ),
            pytest.param(
                ReconnectState.CONNECTED,
                ReconnectState.DISCONNECTING,
                id="CONNECTED->DISCONNECTING",
            ),
        ],
    )
    def test_op_completes_error(
        self, stage, op, original_state, modified_state, arbitrary_exception
    ):
        stage.state = original_state
        stage.run_op(op)
        assert stage.state == modified_state

        op.complete(arbitrary_exception)

        assert stage.state == ReconnectState.DISCONNECTED

    @pytest.mark.it(
        "Does not change the state if the operation sent down the pipeline completes successfully"
    )
    @pytest.mark.parametrize(
        "original_state, modified_state",
        [
            pytest.param(
                ReconnectState.DISCONNECTED,
                ReconnectState.DISCONNECTED,
                id="DISCONNECTED->DISCONNECTED",
            ),
            pytest.param(
                ReconnectState.CONNECTED,
                ReconnectState.DISCONNECTING,
                id="CONNECTED->DISCONNECTING",
            ),
        ],
    )
    def test_op_completes_success(self, stage, op, original_state, modified_state):
        stage.state = original_state
        stage.run_op(op)
        assert stage.state == modified_state

        op.complete()

        # NOTE: This is a very weird test in that this would never happen like this "in the wild"
        # In a real scenario, prior to the operation completing, an event would fire, and that
        # event would cause a state change to the desired state, so the state would actually not
        # still be this in this "modified state" that was a result of the operation running through
        # the pipeline. However, that's kind of the important thing we need to test - that the
        # operation completing DOES NOT change the state, because that's not it's job. So in order
        # to show this, we will NOT emulate the state change that occurs from the event. Just
        # remember that in pracitce, the state would not actually still be the modified state, but
        # instead the desired goal state
        assert stage.state == modified_state

    @pytest.mark.it(
        "Re-runs all the waiting ops in the `waiting_ops` queue (if any) upon completion of the op after it is sent down"
    )
    @pytest.mark.parametrize(
        "queued_ops",
        [
            pytest.param(
                [pipeline_ops_base.DisconnectOperation(callback=None)], id="Single op waiting"
            ),
            pytest.param(
                [
                    pipeline_ops_base.ReauthorizeConnectionOperation(callback=None),
                    pipeline_ops_base.ConnectOperation(callback=None),
                ],
                id="Multiple ops waiting",
            ),
        ],
    )
    @pytest.mark.parametrize(
        "success",
        [
            pytest.param(True, id="Operation completes with success"),
            pytest.param(False, id="Operation completes with error"),
        ],
    )
    def test_op_completes_causes_waiting_rerun(
        self, mocker, stage, op, queued_ops, success, arbitrary_exception
    ):
        stage.state = ReconnectState.CONNECTED
        stage.run_op(op)
        assert stage.state == ReconnectState.DISCONNECTING
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

        # Before completion, more ops come down and queue up
        for queued_op in queued_ops:
            stage.run_op(queued_op)
        assert stage.waiting_ops.qsize() == len(queued_ops)

        # Now mock out run_op so we can see if it gets called
        stage.run_op = mocker.MagicMock()

        # As mentioned above, before operations complete successfully, an event will be fired,
        # and this event will trigger state change. We need to emulate this one here so that
        # the waiting ops will not end up requeued.
        if success:
            stage.state = ReconnectState.DISCONNECTED
            op.complete()
        else:
            op.complete(arbitrary_exception)

        # All items were removed from the waiting queue and run on the stage
        assert stage.waiting_ops.qsize() == 0
        assert stage.run_op.call_count == len(queued_ops)
        for i in range(len(queued_ops)):
            assert stage.run_op.call_args_list[i] == mocker.call(queued_ops[i])


@pytest.mark.describe(
    "ReconnectStage - .run_op() -- Called with ReauthorizeConnectionOperation (Connection Retry/Reconnect enabled)"
)
class TestReconnectStageRunOpWithReauthorizeConnectionOperation(
    ReconnectStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ReauthorizeConnectionOperation(callback=mocker.MagicMock())

    @pytest.mark.it(
        "Adds the operation to the `waiting_ops` queue and does nothing else if the stage is in an intermediate state"
    )
    @pytest.mark.parametrize(
        "state",
        [
            ReconnectState.CONNECTING,
            ReconnectState.DISCONNECTING,
            ReconnectState.REAUTHORIZING,
        ],
    )
    def test_intermediate_state(self, stage, op, state):
        stage.state = state
        assert stage.waiting_ops.empty()

        stage.run_op(op)

        assert not stage.waiting_ops.empty()
        assert stage.waiting_ops.qsize() == 1
        assert stage.waiting_ops.get() is op
        assert stage.send_op_down.call_count == 0

    @pytest.mark.it(
        "Changes the state to REAUTHORIZING and sends the operation down the pipeline if the stage is in a CONNECTED state"
    )
    def test_connected_state_change(self, mocker, stage, op):
        stage.state = ReconnectState.CONNECTED
        stage.run_op(op)
        assert stage.state == ReconnectState.REAUTHORIZING
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

    @pytest.mark.it(
        "Changes the state to REAUTHORIZING and sends the operation down the pipeline if the stage is in a DISCONNECTED state"
    )
    def test_disconnected_state_change(self, mocker, stage, op):
        stage.state = ReconnectState.DISCONNECTED
        stage.run_op(op)
        assert stage.state == ReconnectState.REAUTHORIZING
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

    @pytest.mark.it(
        "Sets the state to DISCONNECTED if the operation sent down the pipeline completes with error"
    )
    @pytest.mark.parametrize(
        "original_state, modified_state",
        [
            pytest.param(
                ReconnectState.CONNECTED,
                ReconnectState.REAUTHORIZING,
                id="CONNECTED->REAUTHORIZING",
            ),
            pytest.param(
                ReconnectState.DISCONNECTED,
                ReconnectState.REAUTHORIZING,
                id="DISCONNECTED->REAUTHORIZING",
            ),
        ],
    )
    def test_op_completes_error(
        self, stage, op, original_state, modified_state, arbitrary_exception
    ):
        stage.state = original_state
        stage.run_op(op)
        assert stage.state == modified_state

        op.complete(arbitrary_exception)

        assert stage.state == ReconnectState.DISCONNECTED

    @pytest.mark.it(
        "Does not change the state if the operation sent down the pipeline completes successfully"
    )
    @pytest.mark.parametrize(
        "original_state, modified_state",
        [
            pytest.param(
                ReconnectState.CONNECTED,
                ReconnectState.REAUTHORIZING,
                id="CONNECTED->REAUTHORIZING",
            ),
            pytest.param(
                ReconnectState.DISCONNECTED,
                ReconnectState.REAUTHORIZING,
                id="DISCONNECTED->REAUTHORIZING",
            ),
        ],
    )
    def test_op_completes_success(self, stage, op, original_state, modified_state):
        stage.state = original_state
        stage.run_op(op)
        assert stage.state == modified_state

        op.complete()

        # NOTE: This is a very weird test in that this would never happen like this "in the wild"
        # In a real scenario, prior to the operation completing, an event would fire, and that
        # event would cause a state change to the desired state, so the state would actually not
        # still be this in this "modified state" that was a result of the operation running through
        # the pipeline. However, that's kind of the important thing we need to test - that the
        # operation completing DOES NOT change the state, because that's not it's job. So in order
        # to show this, we will NOT emulate the state change that occurs from the event. Just
        # remember that in pracitce, the state would not actually still be the modified state, but
        # instead the desired goal state
        assert stage.state == modified_state

    @pytest.mark.it(
        "Re-runs all of the ops in the `waiting_ops` queue (if any) upon completion of the op after it is sent down"
    )
    @pytest.mark.parametrize(
        "queued_ops",
        [
            pytest.param(
                [pipeline_ops_base.DisconnectOperation(callback=None)], id="Single op waiting"
            ),
            pytest.param(
                [
                    pipeline_ops_base.ReauthorizeConnectionOperation(callback=None),
                    pipeline_ops_base.ConnectOperation(callback=None),
                ],
                id="Multiple ops waiting",
            ),
        ],
    )
    @pytest.mark.parametrize(
        "success",
        [
            pytest.param(True, id="Operation completes with success"),
            pytest.param(False, id="Operation completes with error"),
        ],
    )
    def test_op_completes_causes_waiting_rerun(
        self, mocker, stage, op, queued_ops, success, arbitrary_exception
    ):
        stage.state = ReconnectState.CONNECTED
        stage.run_op(op)
        assert stage.state == ReconnectState.REAUTHORIZING
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

        # Before completion, more ops come down and queue up
        for queued_op in queued_ops:
            stage.run_op(queued_op)
        assert stage.waiting_ops.qsize() == len(queued_ops)

        # Now mock out run_op so we can see if it gets called
        stage.run_op = mocker.MagicMock()

        # As mentioned above, before operations complete successfully, an event will be fired,
        # and this event will trigger state change. We need to emulate this one here so that
        # the waiting ops will not end up requeued.
        if success:
            stage.state = ReconnectState.CONNECTED
            op.complete()
        else:
            op.complete(arbitrary_exception)

        # All items were removed from the waiting queue and run on the stage
        assert stage.waiting_ops.qsize() == 0
        assert stage.run_op.call_count == len(queued_ops)
        for i in range(len(queued_ops)):
            assert stage.run_op.call_args_list[i] == mocker.call(queued_ops[i])


@pytest.mark.describe(
    "ReconnectStage - .run_op() -- Called with ShutdownPipelineOperation (Connection Retry/Reconnect enabled)"
)
class TestReconnectStageRunOpWithShutdownPipelineOperation(
    ReconnectStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ShutdownPipelineOperation(callback=mocker.MagicMock())

    @pytest.mark.it("Clears any reconnection timer that may exist")
    @pytest.mark.parametrize(
        "state",
        [
            ReconnectState.CONNECTING,
            ReconnectState.CONNECTED,
            ReconnectState.DISCONNECTING,
            ReconnectState.DISCONNECTED,
            ReconnectState.REAUTHORIZING,
        ],
    )
    def test_timer_clear(self, mocker, op, stage, state):
        stage.state = state
        timer_mock = mocker.MagicMock()
        stage.reconnect_timer = timer_mock

        stage.run_op(op)

        assert timer_mock.cancel.call_count == 1
        assert stage.reconnect_timer is None

    @pytest.mark.it("Cancels any operations in the `waiting_ops` queue")
    @pytest.mark.parametrize(
        "state",
        [
            ReconnectState.CONNECTING,
            ReconnectState.CONNECTED,
            ReconnectState.DISCONNECTING,
            ReconnectState.DISCONNECTED,
            ReconnectState.REAUTHORIZING,
        ],
    )
    def test_waiting_ops_cancellation(self, mocker, op, stage, state):
        stage.state = state
        waiting_op1 = pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())
        waiting_op2 = pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())
        waiting_op3 = pipeline_ops_base.ReauthorizeConnectionOperation(callback=mocker.MagicMock())
        stage.waiting_ops.put_nowait(waiting_op1)
        stage.waiting_ops.put_nowait(waiting_op2)
        stage.waiting_ops.put_nowait(waiting_op3)

        stage.run_op(op)

        assert stage.waiting_ops.empty()
        assert waiting_op1.completed
        assert isinstance(waiting_op1.error, pipeline_exceptions.OperationCancelled)
        assert waiting_op2.completed
        assert isinstance(waiting_op2.error, pipeline_exceptions.OperationCancelled)
        assert waiting_op3.completed
        assert isinstance(waiting_op3.error, pipeline_exceptions.OperationCancelled)

    @pytest.mark.it("Sends the operation down the pipeline without changing the state")
    @pytest.mark.parametrize(
        "state",
        [
            ReconnectState.CONNECTING,
            ReconnectState.CONNECTED,
            ReconnectState.DISCONNECTING,
            ReconnectState.DISCONNECTED,
            ReconnectState.REAUTHORIZING,
        ],
    )
    def test_sends_op_down(self, mocker, op, stage, state):
        stage.state = state

        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)
        assert stage.state is state


@pytest.mark.describe(
    "ReconnectStage - .run_op() -- Called with arbitrary other operation (Connection Retry/Reconnect enabled)"
)
class TestReconnectStageRunOpWithArbitraryOperation(ReconnectStageTestConfig, StageRunOpTestBase):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down the pipeline without changing the state")
    @pytest.mark.parametrize(
        "state",
        [
            ReconnectState.CONNECTING,
            ReconnectState.CONNECTED,
            ReconnectState.DISCONNECTING,
            ReconnectState.DISCONNECTED,
            ReconnectState.REAUTHORIZING,
        ],
    )
    def test_sends_op_down(self, mocker, op, stage, state):
        stage.state = state

        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)
        assert stage.state is state


@pytest.mark.describe("ReconnectStage - .run_op() -- Connection Retry/Reconnect disabled")
class TestReconnectStageRunOpWhileConnectionRetryDisabled(
    ReconnectStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        # Override fixture to set connecty retry to False
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.pipeline_root.pipeline_configuration.connection_retry = False
        mocker.spy(stage, "run_op")
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")
        return stage

    @pytest.fixture(
        params=[
            pipeline_ops_base.ConnectOperation,
            pipeline_ops_base.DisconnectOperation,
            pipeline_ops_base.ReauthorizeConnectionOperation,
            pipeline_ops_base.ShutdownPipelineOperation,
            ArbitraryOperation,
        ]
    )
    def op(self, request, mocker):
        return request.param(mocker.MagicMock())

    @pytest.mark.it("Sends the operation down the pipeline without changing the state")
    @pytest.mark.parametrize(
        "state",
        [
            ReconnectState.CONNECTING,
            ReconnectState.CONNECTED,
            ReconnectState.DISCONNECTING,
            ReconnectState.DISCONNECTED,
            ReconnectState.REAUTHORIZING,
        ],
    )
    def test_sends_op_down(self, mocker, stage, op, state):
        stage.state = state
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)
        assert stage.state is state


@pytest.mark.describe(
    "ReconnectStage - .handle_pipeline_event() -- Called with ConnectedEvent (Connection Retry/Reconnect enabled)"
)
class TestReconnectStageHandlePipelineEventCalledWithConnectedEvent(
    ReconnectStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self):
        return pipeline_events_base.ConnectedEvent()

    @pytest.mark.it("Clears any reconnect timer that may exist")
    @pytest.mark.parametrize(
        "state",
        [
            # Valid states
            ReconnectState.CONNECTING,
            ReconnectState.REAUTHORIZING,
            # Invalid states (still test tho)
            ReconnectState.DISCONNECTING,
            ReconnectState.CONNECTED,
            ReconnectState.DISCONNECTED,
        ],
    )
    def test_clears_reconnect_timer(self, mocker, stage, event, state):
        stage.state = state
        mock_timer = mocker.MagicMock()
        stage.reconnect_timer = mock_timer

        stage.handle_pipeline_event(event)

        assert stage.reconnect_timer is None
        assert mock_timer.cancel.call_count == 1

    @pytest.mark.it(
        "Changes the state to CONNECTED and sends the event up the pipeline if in a CONNECTING state"
    )
    def test_connecting_state(self, mocker, stage, event):
        stage.state = ReconnectState.CONNECTING

        stage.handle_pipeline_event(event)

        assert stage.state is ReconnectState.CONNECTED
        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)

    @pytest.mark.it(
        "Changes the state to CONNECTED and sends the event up the pipeline if in a REAUTHORIZING state"
    )
    def test_reauthorizing_state(self, mocker, stage, event):
        stage.state = ReconnectState.REAUTHORIZING

        stage.handle_pipeline_event(event)

        assert stage.state is ReconnectState.CONNECTED
        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)

    @pytest.mark.it(
        "Changes the state to CONNECTED and sends the event up the pipeline if in an invalid state"
    )
    @pytest.mark.parametrize(
        "state",
        [
            ReconnectState.DISCONNECTING,
            ReconnectState.CONNECTED,
            ReconnectState.DISCONNECTED,
        ],
    )
    def test_invalid_states(self, mocker, stage, event, state):
        # NOTE: This should never happen in practice
        stage.state = state

        stage.handle_pipeline_event(event)

        assert stage.state is ReconnectState.CONNECTED
        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)


@pytest.mark.describe(
    "ReconnectStage - .handle_pipeline_event() -- Called with DisconnectedEvent (Connection Retry/Reconnect enabled)"
)
class TestReconnectStageHandlePipelineEventCalledWithDisconnectedEvent(
    ReconnectStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self):
        return pipeline_events_base.DisconnectedEvent()

    @pytest.mark.it(
        "Changes the state to DISCONNECTED, starts a immediate reconnect timer, and sends the event up the pipeline if in a CONNECTED state (i.e. Unexpected Disconnect)"
    )
    def test_connected_state(self, mocker, stage, event, mock_timer):
        stage.state = ReconnectState.CONNECTED
        assert stage.reconnect_timer is None

        stage.handle_pipeline_event(event)

        assert stage.state is ReconnectState.DISCONNECTED
        assert stage.reconnect_timer is mock_timer.return_value
        assert mock_timer.call_count == 1
        assert mock_timer.call_args == mocker.call(0.01, mocker.ANY)
        assert mock_timer.return_value.start.call_count == 1
        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)

    @pytest.mark.it(
        "Changes the state to DISCONNECTED, does NOT start a reconnect timer, but sends the event up the pipeline if in a DISCONNECTING state (i.e. Expected Disconnect - Disconnection process)"
    )
    def test_disconnecting_state(self, mocker, stage, event):
        stage.state = ReconnectState.DISCONNECTING
        assert stage.reconnect_timer is None

        stage.handle_pipeline_event(event)

        assert stage.state is ReconnectState.DISCONNECTED
        assert stage.reconnect_timer is None
        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)

    @pytest.mark.it(
        "Does NOT change the state or start a reconnect timer, but sends the event up the pipeline if in a REAUTHORIZING state (i.e. Expected Disconnect - Reauthorization process)"
    )
    def test_reauthorizing_state(self, mocker, stage, event):
        stage.state = ReconnectState.REAUTHORIZING
        assert stage.reconnect_timer is None

        stage.handle_pipeline_event(event)

        assert stage.state is ReconnectState.REAUTHORIZING
        assert stage.reconnect_timer is None
        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)

    @pytest.mark.it(
        "Changes the state to DISCONNECTED, does NOT start a reconnect timer, but sends the event up the pipeline if in an invalid state"
    )
    @pytest.mark.parametrize("state", [ReconnectState.DISCONNECTED, ReconnectState.CONNECTING])
    def test_invalid_states(self, mocker, stage, event, state):
        # NOTE: This should never happen in practice
        stage.state = state
        assert stage.reconnect_timer is None

        stage.handle_pipeline_event(event)

        assert stage.state is ReconnectState.DISCONNECTED
        assert stage.reconnect_timer is None
        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)


@pytest.mark.describe(
    "ReconnectStage - .handle_pipeline_event() -- Called with arbitrary other event (Connection Retry/Reconnect enabled)"
)
class TestReconnectStageHandlePipelineEventCalledWithArbitraryEvent(
    ReconnectStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self, arbitrary_event):
        return arbitrary_event

    @pytest.mark.it(
        "Sends the event up the pipeline without changing the state or starting a reconnect timer"
    )
    @pytest.mark.parametrize(
        "state",
        [
            ReconnectState.CONNECTING,
            ReconnectState.CONNECTED,
            ReconnectState.DISCONNECTING,
            ReconnectState.DISCONNECTED,
            ReconnectState.REAUTHORIZING,
        ],
    )
    def test_sends_event_up(self, mocker, stage, event, state):
        stage.state = state
        assert stage.reconnect_timer is None

        stage.handle_pipeline_event(event)

        assert stage.state is state
        assert stage.reconnect_timer is None
        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)


@pytest.mark.describe(
    "ReconnectStage -.handle_pipeline_event() -- Connection Retry/Reconnect disabled"
)
class TestReconnectStageHandlePipelineEventConnectionRetryDisabled(
    ReconnectStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        # Override fixture to set connecty retry to False
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.pipeline_root.pipeline_configuration.connection_retry = False
        mocker.spy(stage, "run_op")
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")
        return stage

    @pytest.fixture(
        params=[
            pipeline_events_base.ConnectedEvent,
            pipeline_events_base.DisconnectedEvent,
            ArbitraryEvent,
        ]
    )
    def event(self, request):
        return request.param()

    @pytest.mark.it(
        "Sends the event up the pipeline without changing the state or starting a reconnect timer"
    )
    @pytest.mark.parametrize(
        "state",
        [
            ReconnectState.CONNECTING,
            ReconnectState.CONNECTED,
            ReconnectState.DISCONNECTING,
            ReconnectState.DISCONNECTED,
            ReconnectState.REAUTHORIZING,
        ],
    )
    def test_sends_event_up(self, mocker, stage, event, state):
        stage.state = state
        assert stage.reconnect_timer is None

        stage.handle_pipeline_event(event)

        assert stage.state is state
        assert stage.reconnect_timer is None
        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)


@pytest.mark.describe("ReconnectStage - OCCURRENCE: Reconnect Timer Expires")
class TestReconnectStageOCCURRENCEReconnectTimerExpires(ReconnectStageTestConfig):
    @pytest.fixture(
        params=[
            "Timer created by unexpected disconnect",
            "Timer created by reconnect punting due to in-progress op",
            "Timer created by failed reconnection attempt",
        ]
    )
    def trigger_stage_retry_timer_completion(self, request, stage, mock_timer):
        """This fixture is parametrized to get the retry timer completion trigger for every
        possible way a reconnect timer could have been made. This may seem redundant given that
        in the implementation it's pretty clear they all work the same, but ensuring that is true
        is the point of parametrizing the fixture"""

        # The stage must be connected in order to set a reconnect timer
        stage.state = ReconnectState.CONNECTED
        # Send a DisconnectedEvent to the stage in order to set up the timer
        stage.handle_pipeline_event(pipeline_events_base.DisconnectedEvent())

        if request.param == "Timer created by unexpected disconnect":
            # Get timer completion callback
            assert mock_timer.call_count == 1
            timer_callback = mock_timer.call_args[0][1]
            assert stage.state is ReconnectState.DISCONNECTED

        elif request.param == "Timer created by reconnect punting due to in-progress op":
            # Get first timer completion callback
            assert mock_timer.call_count == 1
            timer_callback = mock_timer.call_args[0][1]
            assert stage.state is ReconnectState.DISCONNECTED

            # Make the stage have an in-progress op going
            stage.state = ReconnectState.REAUTHORIZING

            # Invoke the timer completion (which will cause another timer to create)
            timer_callback()

            # Get second timer completion callback
            assert mock_timer.call_count == 2
            timer_callback = mock_timer.call_args[0][1]
        elif request.param == "Timer created by failed reconnection attempt":
            # Get first timer completion callback
            assert mock_timer.call_count == 1
            timer_callback = mock_timer.call_args[0][1]
            assert stage.state is ReconnectState.DISCONNECTED

            # Complete the callback, triggering a reconnection
            timer_callback()

            # Get the op that was sent down
            assert stage.send_op_down.call_count == 1
            op = stage.send_op_down.call_args[0][0]

            # Fail the op with a transient error
            op.complete(error=transport_exceptions.ConnectionFailedError())

            # Get second timer completion callback
            assert mock_timer.call_count == 2
            timer_callback = mock_timer.call_args[0][1]

        # Reset mock so none of this stuff counts in the test
        mock_timer.reset_mock()
        stage.send_op_down.reset_mock()
        stage.send_event_up.reset_mock()
        return timer_callback

    @pytest.mark.it(
        "Sends a new ConnectOperation down the pipeline, changes the state to CONNECTING and clears the reconnect timer if timer expires and the state is DISCONNECTED (i.e. do a reconnect)"
    )
    def test_disconnected_state(self, stage, trigger_stage_retry_timer_completion):
        stage.state = ReconnectState.DISCONNECTED
        assert stage.reconnect_timer is not None

        trigger_stage_retry_timer_completion()

        assert stage.state is ReconnectState.CONNECTING
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.ConnectOperation)
        assert stage.reconnect_timer is None

    @pytest.mark.it(
        "Start a new reconnect timer for the interval specified by the pipeline config, but do not change the state or send anything down the pipeline, if the timer expires and the state is an intermediate state (i.e. punt until later)"
    )
    @pytest.mark.parametrize(
        "state",
        [
            ReconnectState.CONNECTING,
            ReconnectState.DISCONNECTING,
            ReconnectState.REAUTHORIZING,
        ],
    )
    def test_intermediate_state(
        self, mocker, stage, trigger_stage_retry_timer_completion, state, mock_timer
    ):
        stage.state = state
        # Have to replace the timer with a manual mock here because mocked classes always
        # return the same object, but we want to show that the object is replaced, so need
        # to make something different.
        stage.reconnect_timer = mocker.MagicMock()
        old_reconnect_timer = stage.reconnect_timer

        trigger_stage_retry_timer_completion()

        assert stage.state is state
        assert stage.send_op_down.call_count == 0
        assert mock_timer.call_count == 1
        assert mock_timer.call_args == mocker.call(
            stage.pipeline_root.pipeline_configuration.connection_retry_interval, mocker.ANY
        )
        assert stage.reconnect_timer is mock_timer.return_value
        assert stage.reconnect_timer is not old_reconnect_timer

    @pytest.mark.it(
        "Does not change the state or send anything down the pipeline or start any timers if in an invalid state"
    )
    @pytest.mark.parametrize("state", [ReconnectState.CONNECTED])
    def test_invalid_states(self, stage, trigger_stage_retry_timer_completion, state, mock_timer):
        # This should never happen in practice
        stage.state = state

        trigger_stage_retry_timer_completion()

        assert stage.state is state
        assert stage.send_op_down.call_count == 0
        assert mock_timer.call_count == 0
        assert stage.reconnect_timer is None


@pytest.mark.describe("ReconnectStage - OCCURRENCE: Reconnection Completes")
class TestReconnectStageOCCURRENCEReconnectionCompletes(ReconnectStageTestConfig):
    @pytest.fixture(
        params=[
            "Reconnect after unexpected disconnect",
            "Reconnect after punted reconnection",
            "Reconnect after failed reconnection",
        ]
    )
    def reconnect_op(self, request, stage, mock_timer):
        """This fixture is parametrized to cover all possible sources of a reconnection to show
        that reconnections behave the same, no matter how they are generated.
        """
        # The stage must be connected and then lose connection in order to set
        # the initial reconnect timer
        assert mock_timer.call_count == 0
        stage.state = ReconnectState.CONNECTED
        stage.handle_pipeline_event(pipeline_events_base.DisconnectedEvent())
        if request.param == "Reconnect after unexpected disconnect":
            # Invoke the callback passed to the reconnect timer to spawn op
            assert mock_timer.call_count == 1
            assert stage.send_op_down.call_count == 0
            timer_callback = mock_timer.call_args[0][1]
            timer_callback()
            # Get the reconnect op
            assert stage.send_op_down.call_count == 1
            reconnect_op = stage.send_op_down.call_args[0][0]
        elif request.param == "Reconnect after punted reconnection":
            # Change the state to an in-progress one so that reconnect will punt
            stage.state = ReconnectState.CONNECTING
            # Invoke the callback passed to the reconnect timer
            assert mock_timer.call_count == 1
            assert stage.send_op_down.call_count == 0
            timer_callback = mock_timer.call_args[0][1]
            timer_callback()
            # Reconnection punted (set a new timer)
            assert stage.send_op_down.call_count == 0
            assert mock_timer.call_count == 2
            # Change state so next reconnect will not punt
            stage.state = ReconnectState.DISCONNECTED
            # Invoke the callback passed to the new reconnect timer
            timer_callback = mock_timer.call_args[0][1]
            timer_callback()
            # Get the reconnect op
            assert stage.send_op_down.call_count == 1
            reconnect_op = stage.send_op_down.call_args[0][0]
        elif request.param == "Reconnect after failed reconnection":
            # Invoke the callback passed to the reconnect timer to spawn op
            assert mock_timer.call_count == 1
            assert stage.send_op_down.call_count == 0
            timer_callback = mock_timer.call_args[0][1]
            timer_callback()
            # Fail the resulting reconnect op with a transient error
            assert stage.send_op_down.call_count == 1
            assert stage.report_background_exception.call_count == 0
            reconnect_op = stage.send_op_down.call_args[0][0]
            reconnect_op.complete(error=transport_exceptions.ConnectionFailedError())
            # New reconnect timer set
            assert mock_timer.call_count == 2
            assert stage.send_op_down.call_count == 1
            assert stage.report_background_exception.call_count == 1
            # Invoke the callback passed to the new reconnect timer to spawn op
            timer_callback = mock_timer.call_args[0][1]
            timer_callback()
            # Get the reconnect op for this second attempt
            assert stage.send_op_down.call_count == 2
            reconnect_op = stage.send_op_down.call_args[0][0]

        # Clean up mocks
        mock_timer.reset_mock()
        stage.send_op_down.reset_mock()
        stage.send_event_up.reset_mock()
        stage.report_background_exception.reset_mock()
        return reconnect_op

    @pytest.mark.it("Re-runs all of the ops in the `waiting_ops` queue (if any)")
    @pytest.mark.parametrize(
        "queued_ops",
        [
            pytest.param(
                [pipeline_ops_base.DisconnectOperation(callback=None)], id="Single op waiting"
            ),
            pytest.param(
                [
                    pipeline_ops_base.ReauthorizeConnectionOperation(callback=None),
                    pipeline_ops_base.ConnectOperation(callback=None),
                ],
                id="Multiple ops waiting",
            ),
        ],
    )
    @pytest.mark.parametrize(
        "success",
        [
            pytest.param(True, id="Operation completes with success"),
            pytest.param(False, id="Operation completes with error"),
        ],
    )
    def test_waiting_rerun(
        self, mocker, stage, reconnect_op, queued_ops, success, arbitrary_exception
    ):
        # Before completion, more ops come down and queue up
        for queued_op in queued_ops:
            stage.run_op(queued_op)
        assert stage.waiting_ops.qsize() == len(queued_ops)

        # Now mock out run_op so we can see if it gets called
        stage.run_op = mocker.MagicMock()

        # Before operations complete successfully, an event will be fired, and this event will
        # trigger state change. We need to emulate this here so that the waiting ops will
        # not end up requeued.
        if success:
            stage.state = ReconnectState.CONNECTED
            reconnect_op.complete()
        else:
            reconnect_op.complete(arbitrary_exception)

        # All items were removed from the waiting queue and run on the stage
        assert stage.waiting_ops.qsize() == 0
        assert stage.run_op.call_count == len(queued_ops)
        for i in range(len(queued_ops)):
            assert stage.run_op.call_args_list[i] == mocker.call(queued_ops[i])

    @pytest.mark.it("Reports the error as a background exception if completed with error")
    def test_failure_report_background_exception(
        self, mocker, stage, reconnect_op, arbitrary_exception
    ):
        assert stage.report_background_exception.call_count == 0

        reconnect_op.complete(error=arbitrary_exception)

        assert stage.report_background_exception.call_count == 1
        assert stage.report_background_exception.call_args == mocker.call(arbitrary_exception)

    @pytest.mark.it("Changes the state to DISCONNECTED if completed with error")
    def test_failure_state_change(self, stage, reconnect_op, arbitrary_exception):
        assert stage.state is ReconnectState.CONNECTING

        reconnect_op.complete(error=arbitrary_exception)

        assert stage.state is ReconnectState.DISCONNECTED

    @pytest.mark.it("Does not change the state if completed successfully")
    def test_success_state_change(self, stage, reconnect_op):
        assert stage.state is ReconnectState.CONNECTING

        # emulate state change from the ConnectedEvent firing
        stage.state = ReconnectState.CONNECTED
        # complete the op
        reconnect_op.complete()

        assert stage.state is ReconnectState.CONNECTED

    @pytest.mark.it(
        "Starts a new reconnect timer if the operation completed with a transient error"
    )
    @pytest.mark.parametrize(
        "error",
        [
            pytest.param(pipeline_exceptions.OperationCancelled(), id="OperationCancelled"),
            pytest.param(pipeline_exceptions.OperationTimeout(), id="OperationTimeout"),
            pytest.param(pipeline_exceptions.OperationError(), id="OperationError"),
            pytest.param(transport_exceptions.ConnectionFailedError(), id="ConnectionFailedError"),
            pytest.param(
                transport_exceptions.ConnectionDroppedError(), id="ConnectionDroppedError"
            ),
        ],
    )
    def test_transient_error_completion(self, mocker, stage, reconnect_op, mock_timer, error):
        assert stage.reconnect_timer is None
        assert mock_timer.call_count == 0

        reconnect_op.complete(error=error)

        assert mock_timer.call_count == 1
        assert mock_timer.call_args == mocker.call(
            stage.pipeline_root.pipeline_configuration.connection_retry_interval, mocker.ANY
        )
        assert stage.reconnect_timer is mock_timer.return_value

    @pytest.mark.it(
        "Does not start a new reconnect timer if the operation completed with a non-transient (i.e. non-recoverable) error"
    )
    def test_non_transient_error_completion(
        self, stage, reconnect_op, mock_timer, arbitrary_exception
    ):
        assert stage.reconnect_timer is None
        assert mock_timer.call_count == 0

        reconnect_op.complete(error=arbitrary_exception)

        assert mock_timer.call_count == 0
        assert stage.reconnect_timer is None
