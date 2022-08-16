# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import urllib
import time
import unittest.mock as mock
from azure.iot.device.common import handle_exceptions
from azure.iot.device.common.pipeline.pipeline_exceptions import OperationTimeout
from azure.iot.device.common.pipeline.pipeline_nucleus import ConnectionState
from azure.iot.device.common.auth.sastoken import RenewableSasToken, NonRenewableSasToken
from azure.iot.device.common.models import X509
from azure.iot.device.iothub.pipeline import MQTTPipeline, IoTHubPipelineConfig
from azure.iot.device.iothub.models import Message

# Fixture Constants #
DEVICE_CLIENT = "Device Client"
MODULE_CLIENT = "Module Client"
RENEWABLE_SAS = "Renewable SAS"
NONRENEWABLE_SAS = "Non-Renewable SAS"
X509_CERT = "X509"
OPTIONS_ENABLED = "All Pipeline Options Enabled"
OPTIONS_DISABLED = "All Pipeline Options Disabled"
EDP_OPTION_DISABLED = "Ensure Desired Properties Disabled"
AC_OPTION_DISABLED = "Auto Connect Disabled"
CR_OPTION_DISABLED = "Connection Retry Disabled"


# Fake data #
fake_hostname = "fake_hostname"
fake_device_id = "fake_device"
fake_module_id = "fake_module"
fake_uri = "some/resource/location"
fake_signed_data = "ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI="
fake_expiry = 12321312
fake_cert_file = "fake_cert_file"
fake_key_file = "fake_key_file"
sastoken_format = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}"


# Helpers #
class CallbackMock(mock.MagicMock):
    def completed(self):
        if self.call_count == 1:
            return True
        else:
            return False

    def completed_successfully(self):
        if self.call_count == 1 and self.call_args == mock.call(error=None):
            return True
        else:
            return False

    def completed_with_error(self, specific_error=None):
        if self.call_count == 1 and not self.call_args == mock.call(error=None):
            if not specific_error:
                return True
            # Exception instance
            elif isinstance(specific_error, Exception):
                if self.call_args[1]["error"] is specific_error:
                    return True
            # Exception type
            elif isinstance(specific_error, type):
                if isinstance(self.call_args[1]["error"], specific_error):
                    return True
        return False


def get_pipeline_stage(pipeline, stage_type):
    curr_stage = pipeline._pipeline
    while curr_stage:
        if isinstance(curr_stage, stage_type):
            return curr_stage
        else:
            curr_stage = curr_stage.next


def connect_pipeline(pipeline, mock_transport):
    initial_connect_call_count = mock_transport.connect.call_count

    # Start connect
    mock_cb = mock.MagicMock()
    pipeline.connect(mock_cb)
    # Connection process has begun
    assert mock_transport.connect.call_count == initial_connect_call_count + 1
    assert mock_cb.call_count == 0
    assert not pipeline.connected

    # Finish connect
    mock_transport.on_mqtt_connected_handler()
    wait_for_pl_thread()
    # Connection process has completed
    assert mock_transport.connect.call_count == initial_connect_call_count + 1
    assert mock_cb.call_count == 1
    assert pipeline.connected


def wait_for_pl_thread():
    time.sleep(0.02)


# Fixtures #
@pytest.fixture
def message():
    return Message("Some message")


@pytest.fixture
def mock_callback(mocker):
    return mocker.MagicMock()


@pytest.fixture(autouse=True)
def mock_transport(mocker):
    constructor_mock = mocker.patch(
        "azure.iot.device.common.pipeline.pipeline_stages_mqtt.MQTTTransport", autospec=True
    )
    return constructor_mock.return_value


@pytest.fixture(autouse=True)
def mock_exception_handler(mocker):
    mocker.spy(handle_exceptions, "swallow_unraised_exception")
    mocker.spy(handle_exceptions, "handle_background_exception")
    # return mocker.spy(azure.iot.device.common, "handle_exceptions")


@pytest.fixture
def mock_signing_mechanism(mocker):
    mechanism = mocker.MagicMock()
    mechanism.sign.return_value = fake_signed_data
    return mechanism


@pytest.fixture(params=[DEVICE_CLIENT, MODULE_CLIENT])
def client_config_kwargs(request):
    if request.param == DEVICE_CLIENT:
        return {"device_id": fake_device_id}
    elif request.param == MODULE_CLIENT:
        return {"device_id": fake_device_id, "module_id": fake_module_id}
    else:
        # shouldn't happen
        raise Exception("Bad fixture: client_config_kwargs")


@pytest.fixture(params=[RENEWABLE_SAS, NONRENEWABLE_SAS, X509_CERT])
def auth_config_kwargs(request, mock_signing_mechanism):
    if request.param == RENEWABLE_SAS:
        token = RenewableSasToken(uri=fake_uri, signing_mechanism=mock_signing_mechanism)
        return {"sastoken": token}
    elif request.param == NONRENEWABLE_SAS:
        token_str = sastoken_format.format(
            resource=urllib.parse.quote(fake_uri, safe=""),
            signature=urllib.parse.quote(fake_signed_data, safe=""),
            expiry=fake_expiry,
        )
        return {"sastoken": NonRenewableSasToken(token_str)}
    elif request.param == X509_CERT:
        return {"x509": X509(cert_file=fake_cert_file, key_file=fake_key_file)}
    else:
        # shouldn't happen
        raise Exception("Bad fixture: auth_config_kwargs")


@pytest.fixture(params=[OPTIONS_ENABLED, OPTIONS_DISABLED])
def option_config_kwargs(request):
    if request.param == OPTIONS_ENABLED:
        # All options enabled by default
        return {}
    elif request.param == OPTIONS_DISABLED:
        return {
            "ensure_desired_properties": False,
            "connection_retry": False,
            "auto_connect": False,
        }
    else:
        # shouldn't happen
        raise Exception("Bad fixture: option_config_kwargs")


@pytest.fixture
def pipeline_config(client_config_kwargs, auth_config_kwargs, option_config_kwargs):
    kwargs = {**client_config_kwargs, **auth_config_kwargs, **option_config_kwargs}
    kwargs["hostname"] = fake_hostname
    return IoTHubPipelineConfig(**kwargs)


@pytest.fixture
def pipeline(pipeline_config):
    return MQTTPipeline(pipeline_config)


# Tests #


class TestManualConnect:
    @pytest.mark.integration_test
    def test_manual_connect_while_disconnected(self, pipeline, mock_transport):
        assert mock_transport.connect.call_count == 0
        assert not pipeline.connected
        # Start connect
        cb_mock = CallbackMock()
        pipeline.connect(cb_mock)
        # Connection process has begun
        assert mock_transport.connect.call_count == 1
        assert not cb_mock.completed()
        assert not pipeline.connected
        # Finish connect
        mock_transport.on_mqtt_connected_handler()
        wait_for_pl_thread()
        # Connection process has finished
        assert mock_transport.connect.call_count == 1
        assert cb_mock.completed_successfully()
        assert pipeline.connected

    @pytest.mark.integration_test
    def test_manual_connect_while_connected(self, pipeline, mock_transport):
        connect_pipeline(pipeline, mock_transport)
        assert mock_transport.connect.call_count == 1
        assert pipeline.connected
        # Connect
        mock_cb = CallbackMock()
        pipeline.connect(mock_cb)
        wait_for_pl_thread()
        # Operation has completed with no additional connect actually happening,
        # or any change to the pipeline state
        assert mock_transport.connect.call_count == 1
        assert mock_cb.completed_successfully()
        assert pipeline.connected

    @pytest.mark.integration_test
    def test_transport_raises_exception_while_connecting(
        self, pipeline, mock_transport, arbitrary_exception
    ):
        assert mock_transport.connect.call_count == 0
        assert not pipeline.connected
        # Set transport to raise exception
        mock_transport.connect.side_effect = arbitrary_exception
        # Connect attempt
        mock_cb = CallbackMock()
        pipeline.connect(mock_cb)
        wait_for_pl_thread()
        # Transport was called
        assert mock_transport.connect.call_count == 1
        # Failure should be indicated by callback
        assert mock_cb.completed_with_error(arbitrary_exception)
        assert not pipeline.connected

    @pytest.mark.integration_test
    def test_transport_connection_failure_rejected(
        self, pipeline, mock_transport, arbitrary_exception
    ):
        assert mock_transport.connect.call_count == 0
        assert not pipeline.connected
        # Connect
        mock_cb = CallbackMock()
        pipeline.connect(mock_cb)
        # Connection process has begun
        assert mock_transport.connect.call_count == 1
        assert not mock_cb.completed()
        assert not pipeline.connected
        # Trigger connection failure
        mock_transport.on_mqtt_connection_failure_handler(arbitrary_exception)
        wait_for_pl_thread()
        # Failure should be indicated by callback
        assert mock_cb.completed_with_error(arbitrary_exception)
        assert not pipeline.connected

    @pytest.mark.slow_integration_test
    def test_hanging_connect(self, pipeline, mock_transport):
        assert mock_transport.connect.call_count == 0
        assert not pipeline.connected
        # Connect
        mock_cb = CallbackMock()
        pipeline.connect(mock_cb)
        # Connection process has begun
        assert mock_transport.connect.call_count == 1
        assert not mock_cb.completed()
        assert not pipeline.connected
        # Wait for timeout (60 seconds)
        time.sleep(61)
        # Failure should be indicated by callback
        assert mock_cb.completed_with_error(OperationTimeout)
        assert not pipeline.connected


class TestManualDisconnect:
    @pytest.mark.integration_test
    def test_manual_disconnect_while_connected(self, pipeline, mock_transport):
        connect_pipeline(pipeline, mock_transport)
        assert mock_transport.disconnect.call_count == 0
        assert pipeline.connected

        # Start disconnect
        mock_cb = CallbackMock()
        pipeline.disconnect(mock_cb)
        # Disconnection process has begun
        assert mock_transport.disconnect.call_count == 1
        assert not mock_cb.completed()
        assert pipeline._nucleus.connection_state == ConnectionState.DISCONNECTING

        # Finish disconnect
        mock_transport.on_mqtt_disconnected_handler()
        wait_for_pl_thread()
        # Disconnection process has finished
        assert mock_transport.disconnect.call_count == 1
        assert mock_cb.completed_successfully()
        assert not pipeline.connected
        assert pipeline._nucleus.connection_state == ConnectionState.DISCONNECTED

    @pytest.mark.integration_test
    def test_manual_disconnect_while_disconnected(self, pipeline, mock_transport):
        assert mock_transport.disconnect.call_count == 0
        assert not pipeline.connected

        # Start disconnect
        mock_cb = CallbackMock()
        pipeline.disconnect(mock_cb)
        wait_for_pl_thread()
        # Disconnect process completed without a disconnect actually happening
        assert mock_transport.disconnect.call_count == 0
        assert mock_transport.connect.call_count == 0
        assert mock_cb.completed_successfully()
        assert not pipeline.connected


class TestQueuedPipelineOperations:
    @pytest.mark.integration_test
    def test_multiple_connects_queued(self, pipeline, mock_transport):
        assert mock_transport.connect.call_count == 0
        assert not pipeline.connected

        # Start connect 1
        mock_cb1 = CallbackMock()
        pipeline.connect(mock_cb1)
        # Connection process has begun
        assert mock_transport.connect.call_count == 1
        assert not mock_cb1.completed()
        assert not pipeline.connected

        # Start connect 2
        mock_cb2 = CallbackMock()
        pipeline.connect(mock_cb2)
        # Start connect 3
        mock_cb3 = CallbackMock()
        pipeline.connect(mock_cb3)
        # No changes since connect 1 began
        assert mock_transport.connect.call_count == 1
        assert not mock_cb1.completed()
        assert not mock_cb2.completed()
        assert not mock_cb3.completed()
        assert not pipeline.connected

        # Complete the first connection
        mock_transport.on_mqtt_connected_handler()
        wait_for_pl_thread()
        # Connection process has been completed
        assert mock_transport.connect.call_count == 1
        assert mock_cb1.completed_successfully()
        assert pipeline.connected
        # Connects 2 and 3 are now also completed
        assert mock_cb2.completed_successfully()
        assert mock_cb3.completed_successfully()

    @pytest.mark.integration_test
    def test_multiple_disconnects_queued(self, pipeline, mock_transport):
        connect_pipeline(pipeline, mock_transport)
        assert mock_transport.disconnect.call_count == 0
        assert pipeline.connected

        # Start disconnect 1
        mock_cb1 = CallbackMock()
        pipeline.disconnect(mock_cb1)
        # Disconnection process has begun
        assert mock_transport.disconnect.call_count == 1
        assert not mock_cb1.completed()
        assert pipeline._nucleus.connection_state == ConnectionState.DISCONNECTING
        # Start disconnect 2
        mock_cb2 = CallbackMock()
        pipeline.disconnect(mock_cb2)
        # Start disconnect 3
        mock_cb3 = CallbackMock()
        pipeline.disconnect(mock_cb3)
        # No changes since disconnect 1
        assert mock_transport.disconnect.call_count == 1
        assert not mock_cb1.completed()
        assert not mock_cb2.completed()
        assert not mock_cb3.completed()
        assert pipeline._nucleus.connection_state == ConnectionState.DISCONNECTING

        # Complete the first disconnect
        mock_transport.on_mqtt_disconnected_handler()
        wait_for_pl_thread()
        # Disconnection has been completed
        assert mock_transport.disconnect.call_count == 1
        assert mock_cb1.completed_successfully()
        assert pipeline._nucleus.connection_state == ConnectionState.DISCONNECTED
        assert not pipeline.connected
        # Disconnects 2 and 3 are also completed
        assert mock_cb2.completed_successfully()
        assert mock_cb3.completed_successfully()

    @pytest.mark.integration_test
    def test_alternating_connects_and_disconnects_queued(self, pipeline, mock_transport):
        """CONNECT DISCONNECT CONNECT DISCONNECT"""
        assert mock_transport.connect.call_count == 0
        assert mock_transport.disconnect.call_count == 0
        assert pipeline._nucleus.connection_state == ConnectionState.DISCONNECTED

        # Start connect 1
        c1_cb_mock = CallbackMock()
        pipeline.connect(c1_cb_mock)
        # Connect 1 process has begun
        assert mock_transport.connect.call_count == 1
        assert mock_transport.disconnect.call_count == 0
        assert not c1_cb_mock.completed()
        assert pipeline._nucleus.connection_state == ConnectionState.CONNECTING

        # Start disconnect 1
        d1_cb_mock = CallbackMock()
        pipeline.disconnect(d1_cb_mock)
        # Start connect 2
        c2_cb_mock = CallbackMock()
        pipeline.connect(c2_cb_mock)
        # Start disconnect 2
        d2_cb_mock = CallbackMock()
        pipeline.disconnect(d2_cb_mock)
        # No changes since connect 1 began
        assert mock_transport.connect.call_count == 1
        assert mock_transport.disconnect.call_count == 0
        assert not c1_cb_mock.completed()
        assert not d1_cb_mock.completed()
        assert not c2_cb_mock.completed()
        assert not d2_cb_mock.completed()
        assert pipeline._nucleus.connection_state == ConnectionState.CONNECTING

        # Complete connect 1
        mock_transport.on_mqtt_connected_handler()
        wait_for_pl_thread()
        # Connection process has been completed
        assert mock_transport.connect.call_count == 1
        assert c1_cb_mock.completed_successfully()
        # Disconnect 1 has begun process
        assert mock_transport.disconnect.call_count == 1
        assert pipeline._nucleus.connection_state == ConnectionState.DISCONNECTING
        assert not d1_cb_mock.completed()
        assert not c2_cb_mock.completed()
        assert not d2_cb_mock.completed()

        # Complete disconnect 1
        mock_transport.on_mqtt_disconnected_handler()
        wait_for_pl_thread()
        # Disconnection process has been completed
        assert mock_transport.disconnect.call_count == 1
        assert d1_cb_mock.completed_successfully()
        # Connect 2 has begun process
        assert mock_transport.connect.call_count == 2
        assert pipeline._nucleus.connection_state == ConnectionState.CONNECTING
        assert not c2_cb_mock.completed()
        assert not d2_cb_mock.completed()

        # Complete connect 2
        mock_transport.on_mqtt_connected_handler()
        wait_for_pl_thread()
        # Connection process has been completed
        assert mock_transport.connect.call_count == 2
        assert c2_cb_mock.completed_successfully()
        # Disconnect 2 has begun process
        assert mock_transport.disconnect.call_count == 2
        assert pipeline._nucleus.connection_state == ConnectionState.DISCONNECTING
        assert not d2_cb_mock.completed()

        # Complete disconnect 2
        mock_transport.on_mqtt_disconnected_handler()
        wait_for_pl_thread()
        # Disconnect 2 has been completed
        assert mock_transport.disconnect.call_count == 2
        assert mock_transport.connect.call_count == 2
        assert d2_cb_mock.completed_successfully()
        assert pipeline._nucleus.connection_state == ConnectionState.DISCONNECTED

    @pytest.mark.integration_test
    def test_mixed_connects_and_disconnects_queued(self, pipeline, mock_transport):
        """CONNECT CONNECT DISCONNECT DISCONNECT CONNECT"""
        assert mock_transport.connect.call_count == 0
        assert mock_transport.disconnect.call_count == 0
        assert pipeline._nucleus.connection_state == ConnectionState.DISCONNECTED

        # Start connect 1
        c1_cb_mock = CallbackMock()
        pipeline.connect(c1_cb_mock)
        # Connection process has begun
        assert mock_transport.connect.call_count == 1
        assert mock_transport.disconnect.call_count == 0
        assert not c1_cb_mock.completed()
        assert pipeline._nucleus.connection_state == ConnectionState.CONNECTING

        # Start connect 2
        c2_cb_mock = CallbackMock()
        pipeline.connect(c2_cb_mock)
        # Start disconnect 1
        d1_cb_mock = CallbackMock()
        pipeline.disconnect(d1_cb_mock)
        # Start disconnect 2
        d2_cb_mock = CallbackMock()
        pipeline.disconnect(d2_cb_mock)
        # Start connect 3
        c3_cb_mock = CallbackMock()
        pipeline.connect(c3_cb_mock)
        # No changes since connect 1 began
        assert mock_transport.connect.call_count == 1
        assert mock_transport.disconnect.call_count == 0
        assert not c1_cb_mock.completed()
        assert not c2_cb_mock.completed()
        assert not d1_cb_mock.completed()
        assert not d2_cb_mock.completed()
        assert not c3_cb_mock.completed()
        assert pipeline._nucleus.connection_state == ConnectionState.CONNECTING

        # Complete connect 1
        mock_transport.on_mqtt_connected_handler()
        wait_for_pl_thread()
        # Connect 1 process has been completed
        assert c1_cb_mock.completed_successfully()
        # Connect 2 has now also been completed
        assert c2_cb_mock.completed_successfully()
        # Disconnect 1 has begun process
        assert mock_transport.connect.call_count == 1
        assert mock_transport.disconnect.call_count == 1
        assert pipeline._nucleus.connection_state == ConnectionState.DISCONNECTING
        assert not d1_cb_mock.completed()
        assert not d2_cb_mock.completed()
        assert not c3_cb_mock.completed()

        # Complete disconnect 1
        mock_transport.on_mqtt_disconnected_handler()
        wait_for_pl_thread()
        # Disconnect 1 process has been completed
        assert d1_cb_mock.completed_successfully()
        # Disconnect 2 process has also been completed
        assert d2_cb_mock.completed_successfully()
        # Connect 3 has begun process
        assert mock_transport.connect.call_count == 2
        assert mock_transport.disconnect.call_count == 1
        assert pipeline._nucleus.connection_state == ConnectionState.CONNECTING
        assert not c3_cb_mock.completed()

        # Complete connect 3
        mock_transport.on_mqtt_connected_handler()
        wait_for_pl_thread()
        # Connect 3 process has been completed
        assert c3_cb_mock.completed_successfully()
        assert mock_transport.connect.call_count == 2
        assert mock_transport.disconnect.call_count == 1
        assert pipeline._nucleus.connection_state == ConnectionState.CONNECTED


class TestUnexpectedTransportBehavior:
    """
    This test suite is for simulating transport behaviors that ideally wouldn't happen, but
    in practice, could
    """

    @pytest.mark.integration_test
    def test_transport_connection_failure_unexpected(
        self, pipeline, mock_transport, arbitrary_exception
    ):
        assert mock_transport.connect.call_count == 0
        assert not pipeline.connected
        # Trigger connection failure
        mock_transport.on_mqtt_connection_failure_handler(arbitrary_exception)
        wait_for_pl_thread()
        # Exception handler was used
        assert handle_exceptions.swallow_unraised_exception.call_count == 1
        assert not pipeline.connected


# def test_auto_connect(pipeline, mock_transport, mock_callback, message):
#     assert mock_transport.connect.call_count == 0
#     assert mock_transport.publish.call_count == 0
#     assert not pipeline.connected

#     pipeline.send_message(message, mock_callback)

#     assert mock_transport.connect.call_count == 1
#     assert mock_transport.publish.call_count == 0
#     assert not pipeline.connected

#     mock_transport.on_mqtt_connected_handler()
#     wait_for_pl_thread()    # the above handler is a nowait so it returns before it completes

#     assert mock_transport.connect.call_count == 1
#     assert mock_transport.publish.call_count == 1
#     assert pipeline.connected
