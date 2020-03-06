# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.protocol.models import AuthenticationMechanism
from azure.iot.hub.iothub_http_runtime_manager import IoTHubHttpRuntimeManager

"""---Constants---"""

fake_hostname = "beauxbatons.academy-net"
fake_device_id = "MyPensieve"
fake_shared_access_key_name = "alohomora"
fake_shared_access_key = "Zm9vYmFy"
fake_lock_token = "fake_lock_token"


"""----Shared fixtures----"""


@pytest.fixture(scope="function", autouse=True)
def mock_http_runtime_operations(mocker):
    mock_http_runtime_operations_init = mocker.patch(
        "azure.iot.hub.protocol.iot_hub_gateway_service_ap_is.HttpRuntimeOperations"
    )
    return mock_http_runtime_operations_init.return_value


@pytest.fixture(scope="function")
def iothub_http_runtime_manager():
    connection_string = "HostName={hostname};DeviceId={device_id};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
        hostname=fake_hostname,
        device_id=fake_device_id,
        skn=fake_shared_access_key_name,
        sk=fake_shared_access_key,
    )
    iothub_http_runtime_manager = IoTHubHttpRuntimeManager(connection_string)
    return iothub_http_runtime_manager


@pytest.mark.describe("IoTHubHttpRuntimeManager - .receive_feedback_notification()")
class TestReceiveFeedbackNotification(object):
    @pytest.mark.it("Receive feedback notification")
    def test_receive_feedback_notification(
        self, mocker, mock_http_runtime_operations, iothub_http_runtime_manager
    ):
        iothub_http_runtime_manager.receive_feedback_notification()
        assert mock_http_runtime_operations.receive_feedback_notification.call_count == 1
        assert mock_http_runtime_operations.receive_feedback_notification.call_args == mocker.call()


@pytest.mark.describe("IoTHubHttpRuntimeManager - .complete_feedback_notification()")
class TestCompleteFeedbackNotification(object):
    @pytest.mark.it("Complete feedback notification")
    def test_complete_feedback_notification(
        self, mocker, mock_http_runtime_operations, iothub_http_runtime_manager
    ):
        iothub_http_runtime_manager.complete_feedback_notification(fake_lock_token)
        assert mock_http_runtime_operations.complete_feedback_notification.call_count == 1
        assert mock_http_runtime_operations.complete_feedback_notification.call_args == mocker.call(
            fake_lock_token
        )


@pytest.mark.describe("IoTHubHttpRuntimeManager - .abandon_feedback_notification()")
class TestAbandonFeedbackNotification(object):
    @pytest.mark.it("Abandon feedback notification")
    def test_abandon_feedback_notification(
        self, mocker, mock_http_runtime_operations, iothub_http_runtime_manager
    ):
        iothub_http_runtime_manager.abandon_feedback_notification(fake_lock_token)
        assert mock_http_runtime_operations.abandon_feedback_notification.call_count == 1
        assert mock_http_runtime_operations.abandon_feedback_notification.call_args == mocker.call(
            fake_lock_token
        )
