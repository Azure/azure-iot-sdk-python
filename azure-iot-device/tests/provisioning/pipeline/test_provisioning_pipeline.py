# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from mock import MagicMock, patch
from azure.iot.device.common.models import X509
from azure.iot.device.provisioning.security.sk_security_client import SymmetricKeySecurityClient
from azure.iot.device.provisioning.security.x509_security_client import X509SecurityClient
from azure.iot.device.provisioning.pipeline.provisioning_pipeline import ProvisioningPipeline
from tests.common.pipeline import helpers

logging.basicConfig(level=logging.INFO)

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
fake_x509_cert_file = "fantastic_beasts"
fake_x509_cert_key_file = "where_to_find_them"
fake_pass_phrase = "alohomora"


def mock_x509():
    return X509(fake_x509_cert_file, fake_x509_cert_key_file, fake_pass_phrase)


def create_x509_security_client():
    return X509SecurityClient(
        provisioning_host=fake_provisioning_host,
        registration_id=fake_registration_id,
        id_scope=fake_id_scope,
        x509=mock_x509,
    )


def create_symmetric_key_security_client():
    return SymmetricKeySecurityClient(
        provisioning_host=fake_provisioning_host,
        registration_id=fake_registration_id,
        id_scope=fake_id_scope,
        symmetric_key=fake_symmetric_key,
    )


different_security_clients = [
    pytest.param(
        {
            "client_class": SymmetricKeySecurityClient,
            "init_kwargs": {
                "provisioning_host": fake_provisioning_host,
                "registration_id": fake_registration_id,
                "id_scope": fake_id_scope,
                "symmetric_key": fake_symmetric_key,
            },
        },
        id="Symmetric",
    ),
    pytest.param(
        {
            "client_class": X509SecurityClient,
            "init_kwargs": {
                "provisioning_host": fake_provisioning_host,
                "registration_id": fake_registration_id,
                "id_scope": fake_id_scope,
                "x509": mock_x509(),
            },
        },
        id="X509",
    ),
]


def assert_for_symmetric_key(password):
    password is not None
    "SharedAccessSignature" in password
    assert "skn=registration" in password
    assert fake_id_scope in password
    assert fake_registration_id in password


def assert_for_client_x509(x509):
    x509 is not None
    assert x509.certificate_file == fake_x509_cert_file
    assert x509.key_file == fake_x509_cert_key_file
    assert x509.pass_phrase == fake_pass_phrase


@pytest.fixture(scope="function")
def mock_provisioning_pipeline(params_security_clients):
    input_security_client = params_security_clients["client_class"](
        **params_security_clients["init_kwargs"]
    )
    with patch(
        "azure.iot.device.provisioning.pipeline.provisioning_pipeline.pipeline_stages_mqtt.MQTTTransport"
    ):
        provisioning_pipeline = ProvisioningPipeline(input_security_client)
    provisioning_pipeline.on_connected = MagicMock()
    provisioning_pipeline.on_disconnected = MagicMock()
    provisioning_pipeline.on_message_received = MagicMock()
    helpers.add_mock_method_waiter(provisioning_pipeline, "on_connected")
    helpers.add_mock_method_waiter(provisioning_pipeline, "on_disconnected")
    helpers.add_mock_method_waiter(provisioning_pipeline._pipeline.transport, "publish")

    yield provisioning_pipeline
    provisioning_pipeline.disconnect()


class TestInit(object):
    @pytest.mark.parametrize(
        "input_security_client",
        [
            pytest.param(create_symmetric_key_security_client(), id="Symmetric Key"),
            pytest.param(create_x509_security_client(), id="X509 Certificate"),
        ],
    )
    @pytest.mark.it("Happens correctly with the specific security client")
    def test_instantiates_correctly(self, input_security_client):
        provisioning_pipeline = ProvisioningPipeline(input_security_client)
        assert provisioning_pipeline._pipeline is not None


@pytest.mark.parametrize("params_security_clients", different_security_clients)
@pytest.mark.describe("Provisioning pipeline - Connect")
class TestConnect(object):
    @pytest.mark.it("Calls connect on transport")
    def test_connect_calls_connect_on_provider(
        self, params_security_clients, mock_provisioning_pipeline
    ):
        mock_mqtt_transport = mock_provisioning_pipeline._pipeline.transport
        mock_provisioning_pipeline.connect()

        assert mock_mqtt_transport.connect.call_count == 1

        if params_security_clients["client_class"].__name__ == "SymmetricKeySecurityClient":
            assert mock_mqtt_transport.connect.call_args[1]["password"] is not None
            assert_for_symmetric_key(mock_mqtt_transport.connect.call_args[1]["password"])
        elif params_security_clients["client_class"].__name__ == "X509SecurityClient":
            assert mock_mqtt_transport.connect.call_args[1]["password"] is None

        mock_mqtt_transport.on_mqtt_connected()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()

    @pytest.mark.it("After complete calls handler with new state")
    def test_connected_state_handler_called_wth_new_state_once_provider_gets_connected(
        self, mock_provisioning_pipeline
    ):
        mock_mqtt_transport = mock_provisioning_pipeline._pipeline.transport

        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()

        mock_provisioning_pipeline.on_connected.assert_called_once_with("connected")

    @pytest.mark.it("Is ignored if waiting for completion of previous one")
    def test_connect_ignored_if_waiting_for_connect_complete(
        self, mock_provisioning_pipeline, params_security_clients
    ):
        mock_mqtt_transport = mock_provisioning_pipeline._pipeline.transport

        mock_provisioning_pipeline.connect()
        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()

        assert mock_mqtt_transport.connect.call_count == 1

        if params_security_clients["client_class"].__name__ == "SymmetricKeySecurityClient":
            assert mock_mqtt_transport.connect.call_args[1]["password"] is not None
            assert_for_symmetric_key(mock_mqtt_transport.connect.call_args[1]["password"])
        elif params_security_clients["client_class"].__name__ == "X509SecurityClient":
            assert mock_mqtt_transport.connect.call_args[1]["password"] is None

        mock_provisioning_pipeline.on_connected.assert_called_once_with("connected")

    @pytest.mark.it("Is ignored if waiting for completion of send")
    def test_connect_ignored_if_waiting_for_send_complete(self, mock_provisioning_pipeline):
        mock_mqtt_transport = mock_provisioning_pipeline._pipeline.transport

        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()

        mock_mqtt_transport.reset_mock()
        mock_provisioning_pipeline.on_connected.reset_mock()

        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id, request_payload=fake_mqtt_payload
        )
        mock_provisioning_pipeline.connect()

        mock_mqtt_transport.connect.assert_not_called()
        mock_provisioning_pipeline.wait_for_on_connected_to_not_be_called()
        mock_provisioning_pipeline.on_connected.assert_not_called()

        mock_mqtt_transport.on_mqtt_published(0)

        mock_mqtt_transport.connect.assert_not_called()
        mock_provisioning_pipeline.wait_for_on_connected_to_not_be_called()
        mock_provisioning_pipeline.on_connected.assert_not_called()


@pytest.mark.parametrize("params_security_clients", different_security_clients)
@pytest.mark.describe("Provisioning pipeline - Send Register")
class TestSendRegister(object):
    @pytest.mark.it("Request calls publish on provider")
    def test_send_register_request_calls_publish_on_provider(
        self, mock_provisioning_pipeline, params_security_clients
    ):
        mock_mqtt_transport = mock_provisioning_pipeline._pipeline.transport

        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()
        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id, request_payload=fake_mqtt_payload
        )

        assert mock_mqtt_transport.connect.call_count == 1

        if params_security_clients["client_class"].__name__ == "SymmetricKeySecurityClient":
            assert mock_mqtt_transport.connect.call_args[1]["password"] is not None
            assert_for_symmetric_key(mock_mqtt_transport.connect.call_args[1]["password"])
        elif params_security_clients["client_class"].__name__ == "X509SecurityClient":
            assert mock_mqtt_transport.connect.call_args[1]["password"] is None

        fake_publish_topic = "$dps/registrations/PUT/iotdps-register/?$rid={}".format(
            fake_request_id
        )

        mock_mqtt_transport.wait_for_publish_to_be_called()
        assert mock_mqtt_transport.publish.call_count == 1
        assert mock_mqtt_transport.publish.call_args[1]["topic"] == fake_publish_topic
        assert mock_mqtt_transport.publish.call_args[1]["payload"] == fake_mqtt_payload

    @pytest.mark.it("Request queues and connects before calling publish on provider")
    def test_send_request_queues_and_connects_before_sending(
        self, mock_provisioning_pipeline, params_security_clients
    ):
        mock_mqtt_transport = mock_provisioning_pipeline._pipeline.transport

        # send an event
        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id, request_payload=fake_mqtt_payload
        )

        # verify that we called connect
        assert mock_mqtt_transport.connect.call_count == 1

        if params_security_clients["client_class"].__name__ == "SymmetricKeySecurityClient":
            assert mock_mqtt_transport.connect.call_args[1]["password"] is not None
            assert_for_symmetric_key(mock_mqtt_transport.connect.call_args[1]["password"])
        elif params_security_clients["client_class"].__name__ == "X509SecurityClient":
            assert mock_mqtt_transport.connect.call_args[1]["password"] is None

        # verify that we're not connected yet and verify that we havent't published yet
        mock_provisioning_pipeline.wait_for_on_connected_to_not_be_called()
        mock_provisioning_pipeline.on_connected.assert_not_called()
        mock_mqtt_transport.wait_for_publish_to_not_be_called()
        mock_mqtt_transport.publish.assert_not_called()

        # finish the connection
        mock_mqtt_transport.on_mqtt_connected()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()

        # verify that our connected callback was called and verify that we published the event
        mock_provisioning_pipeline.on_connected.assert_called_once_with("connected")

        fake_publish_topic = "$dps/registrations/PUT/iotdps-register/?$rid={}".format(
            fake_request_id
        )

        mock_mqtt_transport.wait_for_publish_to_be_called()
        assert mock_mqtt_transport.publish.call_count == 1
        assert mock_mqtt_transport.publish.call_args[1]["topic"] == fake_publish_topic
        assert mock_mqtt_transport.publish.call_args[1]["payload"] == fake_mqtt_payload

    @pytest.mark.it("Request queues and waits for connect to be completed")
    def test_send_request_queues_if_waiting_for_connect_complete(
        self, mock_provisioning_pipeline, params_security_clients
    ):
        mock_mqtt_transport = mock_provisioning_pipeline._pipeline.transport

        # start connecting and verify that we've called into the transport
        mock_provisioning_pipeline.connect()
        assert mock_mqtt_transport.connect.call_count == 1

        if params_security_clients["client_class"].__name__ == "SymmetricKeySecurityClient":
            assert mock_mqtt_transport.connect.call_args[1]["password"] is not None
            assert_for_symmetric_key(mock_mqtt_transport.connect.call_args[1]["password"])
        elif params_security_clients["client_class"].__name__ == "X509SecurityClient":
            assert mock_mqtt_transport.connect.call_args[1]["password"] is None

        # send an event
        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id, request_payload=fake_mqtt_payload
        )

        # verify that we're not connected yet and verify that we havent't published yet
        mock_provisioning_pipeline.wait_for_on_connected_to_not_be_called()
        mock_provisioning_pipeline.on_connected.assert_not_called()
        mock_mqtt_transport.wait_for_publish_to_not_be_called()
        mock_mqtt_transport.publish.assert_not_called()

        # finish the connection
        mock_mqtt_transport.on_mqtt_connected()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()

        # verify that our connected callback was called and verify that we published the event
        mock_provisioning_pipeline.on_connected.assert_called_once_with("connected")
        fake_publish_topic = "$dps/registrations/PUT/iotdps-register/?$rid={}".format(
            fake_request_id
        )
        mock_mqtt_transport.wait_for_publish_to_be_called()
        assert mock_mqtt_transport.publish.call_count == 1
        assert mock_mqtt_transport.publish.call_args[1]["topic"] == fake_publish_topic
        assert mock_mqtt_transport.publish.call_args[1]["payload"] == fake_mqtt_payload

    @pytest.mark.it("Request can be sent multiple times overlapping each other")
    def test_send_request_sends_overlapped_events(self, mock_provisioning_pipeline):
        fake_request_id_1 = fake_request_id
        fake_msg_1 = fake_mqtt_payload
        fake_request_id_2 = "request_4567"
        fake_msg_2 = "Petrificus Totalus"

        mock_mqtt_transport = mock_provisioning_pipeline._pipeline.transport

        # connect
        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()

        # send an event
        callback_1 = MagicMock()
        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id_1, request_payload=fake_msg_1, callback=callback_1
        )

        fake_publish_topic = "$dps/registrations/PUT/iotdps-register/?$rid={}".format(
            fake_request_id_1
        )
        mock_mqtt_transport.wait_for_publish_to_be_called()
        assert mock_mqtt_transport.publish.call_count == 1
        assert mock_mqtt_transport.publish.call_args[1]["topic"] == fake_publish_topic
        assert mock_mqtt_transport.publish.call_args[1]["payload"] == fake_msg_1

        # while we're waiting for that send to complete, send another event
        callback_2 = MagicMock()
        # provisioning_pipeline.send_d2c_message(fake_msg_2, callback_2)
        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id_2, request_payload=fake_msg_2, callback=callback_2
        )

        # verify that we've called publish twice and verify that neither send_d2c_message
        # has completed (because we didn't do anything here to complete it).
        mock_mqtt_transport.wait_for_publish_to_be_called()
        assert mock_mqtt_transport.publish.call_count == 2
        callback_1.assert_not_called()
        callback_2.assert_not_called()

    @pytest.mark.it("Connects , sends request queues and then disconnects")
    def test_connect_send_disconnect(self, mock_provisioning_pipeline):
        mock_mqtt_transport = mock_provisioning_pipeline._pipeline.transport

        # connect
        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()

        # send an event
        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id, request_payload=fake_mqtt_payload
        )
        mock_mqtt_transport.on_mqtt_published(0)

        # disconnect
        mock_provisioning_pipeline.disconnect()
        mock_mqtt_transport.disconnect.assert_called_once_with()


@pytest.mark.parametrize("params_security_clients", different_security_clients)
@pytest.mark.describe("Provisioning pipeline - Send Query")
class TestSendQuery(object):
    @pytest.mark.it("Request calls publish on provider")
    def test_send_query_calls_publish_on_provider(
        self, mock_provisioning_pipeline, params_security_clients
    ):
        mock_mqtt_transport = mock_provisioning_pipeline._pipeline.transport

        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()
        mock_provisioning_pipeline.send_request(
            request_id=fake_request_id,
            request_payload=fake_mqtt_payload,
            operation_id=fake_operation_id,
        )

        assert mock_mqtt_transport.connect.call_count == 1

        if params_security_clients["client_class"].__name__ == "SymmetricKeySecurityClient":
            assert mock_mqtt_transport.connect.call_args[1]["password"] is not None
            assert_for_symmetric_key(mock_mqtt_transport.connect.call_args[1]["password"])
        elif params_security_clients["client_class"].__name__ == "X509SecurityClient":
            assert mock_mqtt_transport.connect.call_args[1]["password"] is None

        fake_publish_topic = "$dps/registrations/GET/iotdps-get-operationstatus/?$rid={}&operationId={}".format(
            fake_request_id, fake_operation_id
        )

        mock_mqtt_transport.wait_for_publish_to_be_called()
        assert mock_mqtt_transport.publish.call_count == 1
        assert mock_mqtt_transport.publish.call_args[1]["topic"] == fake_publish_topic
        assert mock_mqtt_transport.publish.call_args[1]["payload"] == fake_mqtt_payload


@pytest.mark.parametrize("params_security_clients", different_security_clients)
@pytest.mark.describe("Provisioning pipeline - Disconnect")
class TestDisconnect(object):
    @pytest.mark.it("Calls disconnect on provider")
    def test_disconnect_calls_disconnect_on_provider(self, mock_provisioning_pipeline):
        mock_mqtt_transport = mock_provisioning_pipeline._pipeline.transport

        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()
        mock_provisioning_pipeline.disconnect()

        mock_mqtt_transport.disconnect.assert_called_once_with()

    @pytest.mark.it("Is ignored if already disconnected")
    def test_disconnect_ignored_if_already_disconnected(self, mock_provisioning_pipeline):
        mock_mqtt_transport = mock_provisioning_pipeline._pipeline.transport

        mock_provisioning_pipeline.disconnect(None)

        mock_mqtt_transport.disconnect.assert_not_called()

    @pytest.mark.it("After complete calls handler with `disconnected` state")
    def test_disconnect_calls_client_disconnect_callback(self, mock_provisioning_pipeline):
        mock_mqtt_transport = mock_provisioning_pipeline._pipeline.transport

        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()

        mock_provisioning_pipeline.disconnect()
        mock_mqtt_transport.on_mqtt_disconnected()

        mock_provisioning_pipeline.wait_for_on_disconnected_to_be_called()
        mock_provisioning_pipeline.on_disconnected.assert_called_once_with("disconnected")


@pytest.mark.parametrize("params_security_clients", different_security_clients)
@pytest.mark.describe("Provisioning pipeline - Enable")
class TestEnable(object):
    @pytest.mark.it("Calls subscribe on provider")
    def test_subscribe_calls_subscribe_on_provider(self, mock_provisioning_pipeline):
        mock_mqtt_transport = mock_provisioning_pipeline._pipeline.transport

        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()
        mock_provisioning_pipeline.enable_responses()

        assert mock_mqtt_transport.subscribe.call_count == 1
        assert mock_mqtt_transport.subscribe.call_args[1]["topic"] == fake_sub_unsub_topic


@pytest.mark.parametrize("params_security_clients", different_security_clients)
@pytest.mark.describe("Provisioning pipeline - Disable")
class TestDisable(object):
    @pytest.mark.it("Calls unsubscribe on provider")
    def test_unsubscribe_calls_unsubscribe_on_provider(self, mock_provisioning_pipeline):
        mock_mqtt_transport = mock_provisioning_pipeline._pipeline.transport

        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()
        mock_provisioning_pipeline.disable_responses(None)

        assert mock_mqtt_transport.unsubscribe.call_count == 1
        assert mock_mqtt_transport.unsubscribe.call_args[1]["topic"] == fake_sub_unsub_topic
