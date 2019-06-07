# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from mock import MagicMock, patch
from azure.iot.device.provisioning.security.sk_security_client import SymmetricKeySecurityClient
from azure.iot.device.provisioning.pipeline.provisioning_pipeline import ProvisioningPipeline

send_msg_qos = 1

fake_symmetric_key = "Zm9vYmFy"
fake_registration_id = "MyPensieve"
fake_id_scope = "Enchanted0000Ceiling7898"
fake_provisioning_host = "beauxbatons.academy-net"
fake_device_id = "elder_wand"
fake_registration_id = "registered_remembrall"
fake_provisioning_host = "hogwarts.com"
fake_id_scope = "weasley_wizard_wheezes"
fake_ca_cert = "fake_certificate"
fake_sas_token = "horcrux_token"
fake_security_client = "secure_via_muffliato"
fake_request_id = "fake_request_1234"
fake_mqtt_payload = "hello hogwarts"
fake_operation_id = "fake_operation_9876"
fake_sub_unsub_topic = "$dps/registrations/res/#"


@pytest.fixture(scope="function")
def security_client():
    return SymmetricKeySecurityClient(
        provisioning_host=fake_provisioning_host,
        registration_id=fake_registration_id,
        id_scope=fake_id_scope,
        symmetric_key=fake_symmetric_key,
    )


@pytest.fixture(scope="function")
def sas_token(security_client):
    return security_client.get_current_sas_token()


@pytest.fixture(scope="function")
def mock_provisioning_pipeline(security_client):
    with patch(
        "azure.iot.device.provisioning.pipeline.provisioning_pipeline.pipeline_stages_mqtt.MQTTProvider"
    ):
        provisioning_pipeline = ProvisioningPipeline(security_client)
    provisioning_pipeline.on_provisioning_pipeline_connected = MagicMock()
    provisioning_pipeline.on_provisioning_pipeline_disconnected = MagicMock()
    provisioning_pipeline.on_provisioning_pipeline_message_received = MagicMock()
    yield provisioning_pipeline
    provisioning_pipeline.disconnect()


class TestInstantiation(object):
    def test_instantiates_correctly(self, security_client):
        provisioning_pipeline = ProvisioningPipeline(security_client)
        assert provisioning_pipeline._pipeline is not None


class TestConnect:
    def test_connect_calls_connect_on_provider(self, mocker, mock_provisioning_pipeline, sas_token):
        mock_mqtt_provider = mock_provisioning_pipeline._pipeline.provider
        mock_provisioning_pipeline.connect()

        assert mock_mqtt_provider.connect.call_count == 1
        "SharedAccessSignature" in mock_mqtt_provider.connect.call_args[0][0]
        assert "skn=registration" in mock_mqtt_provider.connect.call_args[0][0]
        assert fake_id_scope in mock_mqtt_provider.connect.call_args[0][0]
        assert fake_registration_id in mock_mqtt_provider.connect.call_args[0][0]

        mock_mqtt_provider.on_mqtt_connected()

    def test_connected_state_handler_called_wth_new_state_once_provider_gets_connected(
        self, mock_provisioning_pipeline
    ):
        mock_mqtt_provider = mock_provisioning_pipeline._pipeline.provider

        mock_provisioning_pipeline.connect()
        mock_mqtt_provider.on_mqtt_connected()

        mock_provisioning_pipeline.on_provisioning_pipeline_connected.assert_called_once_with(
            "connected"
        )

    def test_connect_ignored_if_waiting_for_connect_complete(
        self, mock_provisioning_pipeline, sas_token
    ):
        mock_mqtt_provider = mock_provisioning_pipeline._pipeline.provider

        mock_provisioning_pipeline.connect()
        mock_provisioning_pipeline.connect()
        mock_mqtt_provider.on_mqtt_connected()

        assert mock_mqtt_provider.connect.call_count == 1
        "SharedAccessSignature" in mock_mqtt_provider.connect.call_args[0][0]
        assert "skn=registration" in mock_mqtt_provider.connect.call_args[0][0]
        assert fake_id_scope in mock_mqtt_provider.connect.call_args[0][0]
        assert fake_registration_id in mock_mqtt_provider.connect.call_args[0][0]

        mock_provisioning_pipeline.on_provisioning_pipeline_connected.assert_called_once_with(
            "connected"
        )

    def test_connect_ignored_if_waiting_for_send_complete(self, mock_provisioning_pipeline):
        mock_mqtt_provider = mock_provisioning_pipeline._pipeline.provider

        mock_provisioning_pipeline.connect()
        mock_mqtt_provider.on_mqtt_connected()

        mock_mqtt_provider.reset_mock()
        mock_provisioning_pipeline.on_provisioning_pipeline_connected.reset_mock()

        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id, request_payload=fake_mqtt_payload
        )
        mock_provisioning_pipeline.connect()

        mock_mqtt_provider.connect.assert_not_called()
        mock_provisioning_pipeline.on_provisioning_pipeline_connected.assert_not_called()

        mock_mqtt_provider.on_mqtt_published(0)

        mock_mqtt_provider.connect.assert_not_called()
        mock_provisioning_pipeline.on_provisioning_pipeline_connected.assert_not_called()


class TestSendRegister:
    def test_send_request_calls_publish_on_provider(self, mock_provisioning_pipeline, sas_token):
        mock_mqtt_provider = mock_provisioning_pipeline._pipeline.provider

        mock_provisioning_pipeline.connect()
        mock_mqtt_provider.on_mqtt_connected()
        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id, request_payload=fake_mqtt_payload
        )

        assert mock_mqtt_provider.connect.call_count == 1
        "SharedAccessSignature" in mock_mqtt_provider.connect.call_args[0][0]
        assert "skn=registration" in mock_mqtt_provider.connect.call_args[0][0]
        assert fake_id_scope in mock_mqtt_provider.connect.call_args[0][0]
        assert fake_registration_id in mock_mqtt_provider.connect.call_args[0][0]

        fake_publish_topic = "$dps/registrations/PUT/iotdps-register/?$rid={}".format(
            fake_request_id
        )

        assert mock_mqtt_provider.publish.call_count == 1
        assert mock_mqtt_provider.publish.call_args[1]["topic"] == fake_publish_topic
        assert mock_mqtt_provider.publish.call_args[1]["payload"] == fake_mqtt_payload

    #
    def test_send_request_queues_and_connects_before_sending(
        self, mock_provisioning_pipeline, sas_token
    ):
        mock_mqtt_provider = mock_provisioning_pipeline._pipeline.provider

        # send an event
        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id, request_payload=fake_mqtt_payload
        )

        # verify that we called connect
        assert mock_mqtt_provider.connect.call_count == 1
        "SharedAccessSignature" in mock_mqtt_provider.connect.call_args[0][0]
        assert "skn=registration" in mock_mqtt_provider.connect.call_args[0][0]
        assert fake_id_scope in mock_mqtt_provider.connect.call_args[0][0]
        assert fake_registration_id in mock_mqtt_provider.connect.call_args[0][0]

        # verify that we're not connected yet and verify that we havent't published yet
        mock_provisioning_pipeline.on_provisioning_pipeline_connected.assert_not_called()
        mock_mqtt_provider.publish.assert_not_called()

        # finish the connection
        mock_mqtt_provider.on_mqtt_connected()

        # verify that our connected callback was called and verify that we published the event
        mock_provisioning_pipeline.on_provisioning_pipeline_connected.assert_called_once_with(
            "connected"
        )

        fake_publish_topic = "$dps/registrations/PUT/iotdps-register/?$rid={}".format(
            fake_request_id
        )

        assert mock_mqtt_provider.publish.call_count == 1
        assert mock_mqtt_provider.publish.call_args[1]["topic"] == fake_publish_topic
        assert mock_mqtt_provider.publish.call_args[1]["payload"] == fake_mqtt_payload

    def test_send_request_queues_if_waiting_for_connect_complete(
        self, mock_provisioning_pipeline, sas_token
    ):
        mock_mqtt_provider = mock_provisioning_pipeline._pipeline.provider

        # start connecting and verify that we've called into the provider
        mock_provisioning_pipeline.connect()
        assert mock_mqtt_provider.connect.call_count == 1
        "SharedAccessSignature" in mock_mqtt_provider.connect.call_args[0][0]
        assert "skn=registration" in mock_mqtt_provider.connect.call_args[0][0]
        assert fake_id_scope in mock_mqtt_provider.connect.call_args[0][0]
        assert fake_registration_id in mock_mqtt_provider.connect.call_args[0][0]

        # send an event
        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id, request_payload=fake_mqtt_payload
        )

        # verify that we're not connected yet and verify that we havent't published yet
        mock_provisioning_pipeline.on_provisioning_pipeline_connected.assert_not_called()
        mock_mqtt_provider.publish.assert_not_called()

        # finish the connection
        mock_mqtt_provider.on_mqtt_connected()

        # verify that our connected callback was called and verify that we published the event
        mock_provisioning_pipeline.on_provisioning_pipeline_connected.assert_called_once_with(
            "connected"
        )
        fake_publish_topic = "$dps/registrations/PUT/iotdps-register/?$rid={}".format(
            fake_request_id
        )
        assert mock_mqtt_provider.publish.call_count == 1
        assert mock_mqtt_provider.publish.call_args[1]["topic"] == fake_publish_topic
        assert mock_mqtt_provider.publish.call_args[1]["payload"] == fake_mqtt_payload

    def test_send_event_sends_overlapped_events(self, mock_provisioning_pipeline):
        fake_request_id_1 = fake_request_id
        fake_msg_1 = fake_mqtt_payload
        fake_request_id_2 = "request_4567"
        fake_msg_2 = "Petrificus Totalus"

        mock_mqtt_provider = mock_provisioning_pipeline._pipeline.provider

        # connect
        mock_provisioning_pipeline.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # send an event
        callback_1 = MagicMock()
        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id_1, request_payload=fake_msg_1, callback=callback_1
        )

        fake_publish_topic = "$dps/registrations/PUT/iotdps-register/?$rid={}".format(
            fake_request_id_1
        )
        assert mock_mqtt_provider.publish.call_count == 1
        assert mock_mqtt_provider.publish.call_args[1]["topic"] == fake_publish_topic
        assert mock_mqtt_provider.publish.call_args[1]["payload"] == fake_msg_1

        # while we're waiting for that send to complete, send another event
        callback_2 = MagicMock()
        # provisioning_pipeline.send_event(fake_msg_2, callback_2)
        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id_2, request_payload=fake_msg_2, callback=callback_2
        )

        # verify that we've called publish twice and verify that neither send_event
        # has completed (because we didn't do anything here to complete it).
        assert mock_mqtt_provider.publish.call_count == 2
        callback_1.assert_not_called()
        callback_2.assert_not_called()

    def test_connect_send_disconnect(self, mock_provisioning_pipeline):
        mock_mqtt_provider = mock_provisioning_pipeline._pipeline.provider

        # connect
        mock_provisioning_pipeline.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # send an event
        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id, request_payload=fake_mqtt_payload
        )
        mock_mqtt_provider.on_mqtt_published(0)

        # disconnect
        mock_provisioning_pipeline.disconnect()
        mock_mqtt_provider.disconnect.assert_called_once_with()


class TestSendQuery:
    def test_send_query_calls_publish_on_provider(self, mock_provisioning_pipeline, sas_token):
        mock_mqtt_provider = mock_provisioning_pipeline._pipeline.provider

        mock_provisioning_pipeline.connect()
        mock_mqtt_provider.on_mqtt_connected()
        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id,
            request_payload=fake_mqtt_payload,
            operation_id=fake_operation_id,
        )

        assert mock_mqtt_provider.connect.call_count == 1
        "SharedAccessSignature" in mock_mqtt_provider.connect.call_args[0][0]
        assert "skn=registration" in mock_mqtt_provider.connect.call_args[0][0]
        assert fake_id_scope in mock_mqtt_provider.connect.call_args[0][0]
        assert fake_registration_id in mock_mqtt_provider.connect.call_args[0][0]

        fake_publish_topic = "$dps/registrations/GET/iotdps-get-operationstatus/?$rid={}&operationId={}".format(
            fake_request_id, fake_operation_id
        )

        assert mock_mqtt_provider.publish.call_count == 1
        assert mock_mqtt_provider.publish.call_args[1]["topic"] == fake_publish_topic
        assert mock_mqtt_provider.publish.call_args[1]["payload"] == fake_mqtt_payload


class TestDisconnect:
    def test_disconnect_calls_disconnect_on_provider(self, mock_provisioning_pipeline):
        mock_mqtt_provider = mock_provisioning_pipeline._pipeline.provider

        mock_provisioning_pipeline.connect()
        mock_mqtt_provider.on_mqtt_connected()
        mock_provisioning_pipeline.disconnect()

        mock_mqtt_provider.disconnect.assert_called_once_with()

    def test_disconnect_ignored_if_already_disconnected(self, mock_provisioning_pipeline):
        mock_mqtt_provider = mock_provisioning_pipeline._pipeline.provider

        mock_provisioning_pipeline.disconnect(None)

        mock_mqtt_provider.disconnect.assert_not_called()

    def test_disconnect_calls_client_disconnect_callback(self, mock_provisioning_pipeline):
        mock_mqtt_provider = mock_provisioning_pipeline._pipeline.provider

        mock_provisioning_pipeline.connect()
        mock_mqtt_provider.on_mqtt_connected()

        mock_provisioning_pipeline.disconnect()
        mock_mqtt_provider.on_mqtt_disconnected()

        mock_provisioning_pipeline.on_provisioning_pipeline_disconnected.assert_called_once_with(
            "disconnected"
        )


class TestEnable:
    def test_subscribe_calls_subscribe_on_provider(self, mock_provisioning_pipeline):
        mock_mqtt_provider = mock_provisioning_pipeline._pipeline.provider

        mock_provisioning_pipeline.connect()
        mock_mqtt_provider.on_mqtt_connected()
        mock_provisioning_pipeline.enable_responses()

        assert mock_mqtt_provider.subscribe.call_count == 1
        assert mock_mqtt_provider.subscribe.call_args[1]["topic"] == fake_sub_unsub_topic


class TestDisable:
    def test_unsubscribe_calls_unsubscribe_on_provider(self, mock_provisioning_pipeline):
        mock_mqtt_provider = mock_provisioning_pipeline._pipeline.provider

        mock_provisioning_pipeline.connect()
        mock_mqtt_provider.on_mqtt_connected()
        mock_provisioning_pipeline.disable_responses(None)

        assert mock_mqtt_provider.unsubscribe.call_count == 1
        assert mock_mqtt_provider.unsubscribe.call_args[1]["topic"] == fake_sub_unsub_topic
