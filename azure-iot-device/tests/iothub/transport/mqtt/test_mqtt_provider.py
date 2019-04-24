# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from azure.iot.device.iothub.transport.mqtt.mqtt_provider import MQTTProvider
import paho.mqtt.client as mqtt
import ssl
import pytest


fake_hostname = "beauxbatons.academy-net"
fake_device_id = "MyFirebolt"
fake_password = "Fortuna Major"
fake_username = fake_hostname + "/" + fake_device_id
new_fake_password = "new fake password"
fake_topic = "fake_topic"
fake_payload = "Tarantallegra"
fake_qos = 1
fake_mid = 52
fake_rc = 0


class DummyException(Exception):
    pass


@pytest.fixture
def mock_mqtt_client(mocker):
    mock = mocker.patch.object(mqtt, "Client")
    mock_mqtt_client = mock.return_value
    mock_mqtt_client.subscribe = mocker.MagicMock(return_value=(fake_rc, fake_mid))
    mock_mqtt_client.unsubscribe = mocker.MagicMock(return_value=(fake_rc, fake_mid))
    return mock_mqtt_client


@pytest.fixture
def provider(mock_mqtt_client):
    # Implicitly imports the mocked Paho MQTT Client from mock_mqtt_client
    return MQTTProvider(client_id=fake_device_id, hostname=fake_hostname, username=fake_username)


@pytest.mark.describe("MQTT Provider - Instantiation")
class TestInstantiation(object):
    @pytest.mark.it("Creates an instance of the Paho MQTT Client")
    def test_instantiates_mqtt_client(self, mocker):
        mock_mqtt_client_constructor = mocker.patch.object(mqtt, "Client")

        MQTTProvider(client_id=fake_device_id, hostname=fake_hostname, username=fake_username)

        assert mock_mqtt_client_constructor.call_count == 1
        assert mock_mqtt_client_constructor.call_args == mocker.call(
            client_id=fake_device_id, clean_session=False, protocol=mqtt.MQTTv311
        )

    @pytest.mark.it("Sets Paho MQTT Client callbacks")
    def test_sets_paho_callbacks(self, mocker):
        mock_mqtt_client = mocker.patch.object(mqtt, "Client").return_value

        MQTTProvider(client_id=fake_device_id, hostname=fake_hostname, username=fake_username)

        assert callable(mock_mqtt_client.on_connect)
        assert callable(mock_mqtt_client.on_disconnect)
        assert callable(mock_mqtt_client.on_subscribe)
        assert callable(mock_mqtt_client.on_unsubscribe)
        assert callable(mock_mqtt_client.on_publish)
        assert callable(mock_mqtt_client.on_message)

    @pytest.mark.it("Initializes event handler callbacks to 'None'")
    def test_handler_callbacks_set_to_none(self, mocker):
        mocker.patch.object(mqtt, "Client")

        provider = MQTTProvider(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )

        assert provider.on_mqtt_connected is None
        assert provider.on_mqtt_disconnected is None
        assert provider.on_mqtt_message_received is None

    @pytest.mark.it("Initializes internal operation tracking structures")
    def test_operation_infrastructure_set_up(self, mocker):
        provider = MQTTProvider(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )

        assert provider._pending_operation_callbacks == {}
        assert provider._unknown_operation_responses == {}


@pytest.mark.describe("MQTT Provider - Connect")
class TestConnect(object):
    @pytest.mark.it("Configures TLS/SSL context")
    def test_configures_tls_context(self, mocker, mock_mqtt_client, provider):
        mock_ssl_context_constructor = mocker.patch.object(ssl, "SSLContext")
        mock_ssl_context = mock_ssl_context_constructor.return_value

        provider.connect(fake_password)

        # Verify correctness of TLS/SSL Context
        assert mock_ssl_context_constructor.call_count == 1
        assert mock_ssl_context_constructor.call_args == mocker.call(protocol=ssl.PROTOCOL_TLSv1_2)
        assert mock_ssl_context.check_hostname is True
        assert mock_ssl_context.verify_mode == ssl.CERT_REQUIRED

        # Verify correctness of MQTT Client TLS config
        assert mock_mqtt_client.tls_set_context.call_count == 1
        assert mock_mqtt_client.tls_set_context.call_args == mocker.call(context=mock_ssl_context)
        assert mock_mqtt_client.tls_insecure_set.call_count == 1
        assert mock_mqtt_client.tls_insecure_set.call_args == mocker.call(False)

    @pytest.mark.it(
        "Configures TLS/SSL context using default certificates if Provider not instantiated with a CA certificate"
    )
    def test_configures_tls_context_with_default_certs(self, mocker, mock_mqtt_client, provider):
        mock_ssl_context_constructor = mocker.patch.object(ssl, "SSLContext")
        mock_ssl_context = mock_ssl_context_constructor.return_value

        provider = MQTTProvider(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )
        provider.connect(fake_password)

        assert mock_ssl_context.load_default_certs.call_count == 1
        assert mock_ssl_context.load_default_certs.call_args == mocker.call()

    @pytest.mark.it(
        "Configures TLS/SSL context with provided CA certificates if Provider instantiated with a CA certificate"
    )
    def test_configures_tls_context_with_ca_certs(self, mocker, mock_mqtt_client, provider):
        mock_ssl_context_constructor = mocker.patch.object(ssl, "SSLContext")
        mock_ssl_context = mock_ssl_context_constructor.return_value
        ca_cert = "dummy_certificate"

        provider = MQTTProvider(
            client_id=fake_device_id,
            hostname=fake_hostname,
            username=fake_username,
            ca_cert=ca_cert,
        )
        provider.connect(fake_password)

        assert mock_ssl_context.load_verify_locations.call_count == 1
        assert mock_ssl_context.load_verify_locations.call_args == mocker.call(cadata=ca_cert)

    @pytest.mark.it("Sets username and password")
    def test_sets_username_and_password(self, mocker, mock_mqtt_client, provider):
        provider.connect(fake_password)

        assert mock_mqtt_client.username_pw_set.call_count == 1
        assert mock_mqtt_client.username_pw_set.call_args == mocker.call(
            username=fake_username, password=fake_password
        )

    @pytest.mark.it("Connects via Paho")
    def test_calls_paho_connect(self, mocker, mock_mqtt_client, provider):
        provider.connect(fake_password)

        assert mock_mqtt_client.connect.call_count == 1
        assert mock_mqtt_client.connect.call_args == mocker.call(host=fake_hostname, port=8883)

    @pytest.mark.it("Starts MQTT Network Loop")
    def test_calls_loop_start(self, mocker, mock_mqtt_client, provider):
        provider.connect(fake_password)

        assert mock_mqtt_client.loop_start.call_count == 1
        assert mock_mqtt_client.loop_start.call_args == mocker.call()

    @pytest.mark.it("Triggers on_mqtt_connected event handler callback upon connect completion")
    def test_calls_event_handler_callback(self, mocker, mock_mqtt_client, provider):
        callback = mocker.MagicMock()
        provider.on_mqtt_connected = callback

        # Initiate connect
        provider.connect(fake_password)

        # Manually trigger Paho on_connect event_handler
        mock_mqtt_client.on_connect(client=mock_mqtt_client, userdata=None, flags=None, rc=fake_rc)

        # Verify provider.on_mqtt_connected was called
        assert callback.call_count == 1
        assert callback.call_args == mocker.call()

    @pytest.mark.it(
        "Skips on_mqtt_connected event handler callback if set to 'None' upon connect completion"
    )
    def test_skips_none_event_handler_callback(self, mocker, mock_mqtt_client, provider):
        assert provider.on_mqtt_connected is None

        provider.connect(fake_password)

        mock_mqtt_client.on_connect(client=mock_mqtt_client, userdata=None, flags=None, rc=fake_rc)

        # No further asserts required - this is a test to show that it skips a callback.
        # Not raising an exception == test passed

    @pytest.mark.it("Recovers from exception in on_mqtt_connected event handler callback")
    def test_event_handler_callback_raises_exception(self, mocker, mock_mqtt_client, provider):
        event_cb = mocker.MagicMock(side_effect=DummyException)
        provider.on_mqtt_connected = event_cb

        provider.connect(fake_password)
        mock_mqtt_client.on_connect(client=mock_mqtt_client, userdata=None, flags=None, rc=fake_rc)

        # Callback was called, but exception did not propagate
        assert event_cb.call_count == 1


@pytest.mark.describe("MQTT Provider - Reconnect")
class TestReconnect(object):
    @pytest.mark.it("Sets username and password")
    def test_sets_username_and_password(self, mocker, mock_mqtt_client, provider):
        provider.reconnect(fake_password)

        assert mock_mqtt_client.username_pw_set.call_count == 1
        assert mock_mqtt_client.username_pw_set.call_args == mocker.call(
            username=fake_username, password=fake_password
        )

    @pytest.mark.it("Reconnects with Paho")
    def test_calls_paho_reconnect(self, mocker, mock_mqtt_client, provider):
        provider.reconnect(fake_password)

        assert mock_mqtt_client.reconnect.call_count == 1
        assert mock_mqtt_client.reconnect.call_args == mocker.call()

    @pytest.mark.it(
        "Triggers on_mqtt_connected event handler callback upon completion of user-driven reconnect"
    )
    def test_calls_event_handler_callback_user_driven(self, mocker, mock_mqtt_client, provider):
        callback = mocker.MagicMock()
        provider.on_mqtt_connected = callback

        # Initiate reconnect
        provider.reconnect(fake_password)

        # Manually trigger Paho on_connect event_handler
        mock_mqtt_client.on_connect(client=mock_mqtt_client, userdata=None, flags=None, rc=fake_rc)

        # Verify provider.on_mqtt_connected was called
        assert callback.call_count == 1
        assert callback.call_args == mocker.call()

    @pytest.mark.it(
        "Triggers on_mqtt_connected event handler callback upon completion of externally-driven reconnect"
    )
    def test_calls_event_handler_callback_externally_driven(
        self, mocker, mock_mqtt_client, provider
    ):
        callback = mocker.MagicMock()
        provider.on_mqtt_connected = callback

        # Manually trigger Paho on_connect event_handler
        mock_mqtt_client.on_connect(client=mock_mqtt_client, userdata=None, flags=None, rc=fake_rc)

        # Verify provider.on_mqtt_connected was called
        assert callback.call_count == 1
        assert callback.call_args == mocker.call()

    @pytest.mark.it(
        "Skips on_mqtt_connected event handler callback if set to 'None' upon reconnect completion"
    )
    def test_skips_none_event_handler_callback(self, mocker, mock_mqtt_client, provider):
        assert provider.on_mqtt_connected is None

        provider.reconnect(fake_password)

        mock_mqtt_client.on_connect(client=mock_mqtt_client, userdata=None, flags=None, rc=fake_rc)

        # No further asserts required - this is a test to show that it skips a callback.
        # Not raising an exception == test passed

    @pytest.mark.it("Recovers from exception in on_mqtt_connected event handler callback")
    def test_event_handler_callback_raises_exception(self, mocker, mock_mqtt_client, provider):
        event_cb = mocker.MagicMock(side_effect=DummyException)
        provider.on_mqtt_connected = event_cb

        provider.reconnect(fake_password)
        mock_mqtt_client.on_connect(client=mock_mqtt_client, userdata=None, flags=None, rc=fake_rc)

        # Callback was called, but exception did not propagate
        assert event_cb.call_count == 1


@pytest.mark.describe("MQTT Provider - Disconnect")
class TestDisconnect(object):
    @pytest.mark.it("Disconnects with Paho")
    def test_calls_paho_disconnect(self, mocker, mock_mqtt_client, provider):
        provider.disconnect()

        assert mock_mqtt_client.disconnect.call_count == 1
        assert mock_mqtt_client.disconnect.call_args == mocker.call()

    @pytest.mark.it("Stops MQTT Network Loop")
    def test_calls_loop_stop(self, mocker, mock_mqtt_client, provider):
        provider.disconnect()

        assert mock_mqtt_client.loop_stop.call_count == 1
        assert mock_mqtt_client.loop_stop.call_args == mocker.call()

    @pytest.mark.it(
        "Triggers on_mqtt_disconnected event handler callback upon completion of user-driven disconnect "
    )
    def test_calls_event_handler_callback_user_driven(self, mocker, mock_mqtt_client, provider):
        callback = mocker.MagicMock()
        provider.on_mqtt_disconnected = callback

        # Initiate disconnect
        provider.disconnect()

        # Manually trigger Paho on_disconnect event_handler
        mock_mqtt_client.on_disconnect(client=mock_mqtt_client, userdata=None, rc=fake_rc)

        # Verify provider.on_mqtt_disconnected was called
        assert callback.call_count == 1
        assert callback.call_args == mocker.call()

    @pytest.mark.it(
        "Triggers on_mqtt_disconnected event handler callback upon completion of externally-driven disconnect"
    )
    def test_calls_event_handler_callback_externally_driven(
        self, mocker, mock_mqtt_client, provider
    ):
        callback = mocker.MagicMock()
        provider.on_mqtt_disconnected = callback

        # Initiate disconnect
        provider.disconnect()

        # Manually trigger Paho on_connect event_handler
        mock_mqtt_client.on_disconnect(client=mock_mqtt_client, userdata=None, rc=fake_rc)

        # Verify provider.on_mqtt_connected was called
        assert callback.call_count == 1
        assert callback.call_args == mocker.call()

    @pytest.mark.it(
        "Skips on_mqtt_disconnected event handler callback if set to 'None' upon disconnect completion"
    )
    def test_skips_none_event_handler_callback(self, mocker, mock_mqtt_client, provider):
        assert provider.on_mqtt_disconnected is None

        provider.disconnect()

        mock_mqtt_client.on_disconnect(client=mock_mqtt_client, userdata=None, rc=fake_rc)

        # No further asserts required - this is a test to show that it skips a callback.
        # Not raising an exception == test passed

    @pytest.mark.it("Recovers from exception in on_mqtt_disconnected event handler callback")
    def test_event_handler_callback_raises_exception(self, mocker, mock_mqtt_client, provider):
        event_cb = mocker.MagicMock(side_effect=DummyException)
        provider.on_mqtt_disconnected = event_cb

        provider.disconnect()
        mock_mqtt_client.on_disconnect(client=mock_mqtt_client, userdata=None, rc=fake_rc)

        # Callback was called, but exception did not propagate
        assert event_cb.call_count == 1


@pytest.mark.describe("MQTT Provider - Subscribe")
class TestSubscribe(object):
    @pytest.mark.it("Subscribes with Paho")
    @pytest.mark.parametrize(
        "qos",
        [pytest.param(0, id="QoS 0"), pytest.param(1, id="QoS 1"), pytest.param(2, id="QoS 2")],
    )
    def test_calls_paho_subscribe(self, mocker, mock_mqtt_client, provider, qos):
        provider.subscribe(fake_topic, qos=qos)

        assert mock_mqtt_client.subscribe.call_count == 1
        assert mock_mqtt_client.subscribe.call_args == mocker.call(fake_topic, qos=qos)

    @pytest.mark.it("Raises ValueError on invalid QoS")
    @pytest.mark.parametrize("qos", [pytest.param(-1, id="QoS < 0"), pytest.param(3, id="QoS > 2")])
    def test_raises_value_error_invalid_qos(self, qos):
        # Manually instantiate Provider, do NOT mock paho client (paho generates this error)
        provider = MQTTProvider(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )
        with pytest.raises(ValueError):
            provider.subscribe(fake_topic, qos=qos)

    @pytest.mark.it("Raises ValueError on invalid topic string")
    @pytest.mark.parametrize("topic", [pytest.param(None), pytest.param("", id="Empty string")])
    def test_raises_value_error_invalid_topic(self, topic):
        # Manually instantiate Provider, do NOT mock paho client (paho generates this error)
        provider = MQTTProvider(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )
        with pytest.raises(ValueError):
            provider.subscribe(topic, qos=fake_qos)

    @pytest.mark.it("Triggers callback upon subscribe completion")
    def test_triggers_callback_upon_paho_on_subscribe_event(
        self, mocker, mock_mqtt_client, provider
    ):
        callback = mocker.MagicMock()
        mock_mqtt_client.subscribe.return_value = (fake_rc, fake_mid)

        # Initiate subscribe
        provider.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)

        # Check callback is stored as pending, but not called
        assert callback.call_count == 0
        assert provider._pending_operation_callbacks == {fake_mid: callback}
        assert provider._unknown_operation_responses == {}

        # Manually trigger Paho on_subscribe event handler
        mock_mqtt_client.on_subscribe(
            client=mock_mqtt_client, userdata=None, mid=fake_mid, granted_qos=fake_qos
        )

        # Check callback has now been called, and stored values cleared
        assert callback.call_count == 1
        assert provider._pending_operation_callbacks == {}
        assert provider._unknown_operation_responses == {}

    @pytest.mark.it(
        "Triggers callback upon subscribe completion when Paho event handler triggered early"
    )
    def test_triggers_callback_when_paho_on_subscribe_event_called_early(
        self, mocker, mock_mqtt_client, provider
    ):
        callback = mocker.MagicMock()

        def trigger_early_on_subscribe(topic, qos):

            # Trigger on_subscribe before returning mid
            mock_mqtt_client.on_subscribe(
                client=mock_mqtt_client, userdata=None, mid=fake_mid, granted_qos=fake_qos
            )

            # Check mid has been stored as an unknown response, callback not yet called
            assert callback.call_count == 0
            assert provider._pending_operation_callbacks == {}
            assert provider._unknown_operation_responses == {fake_mid: fake_mid}

            return (fake_rc, fake_mid)

        mock_mqtt_client.subscribe.side_effect = trigger_early_on_subscribe

        # Initiate subscribe
        provider.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)

        # Check callback has now been called, and stored values cleared
        assert callback.call_count == 1
        assert provider._pending_operation_callbacks == {}
        assert provider._unknown_operation_responses == {}

    @pytest.mark.it("Skips callback that is set to 'None' upon subscribe completion")
    def test_none_callback_upon_paho_on_subscribe_event(self, mocker, mock_mqtt_client, provider):
        callback = None
        mock_mqtt_client.subscribe.return_value = (fake_rc, fake_mid)

        # Initiate subscribe
        provider.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)

        # Check that callback (None) has been stored
        assert provider._pending_operation_callbacks == {fake_mid: callback}
        assert provider._unknown_operation_responses == {}

        # Manually trigger Paho on_subscribe event handler
        mock_mqtt_client.on_subscribe(
            client=mock_mqtt_client, userdata=None, mid=fake_mid, granted_qos=fake_qos
        )

        # Check that callback (None) has now been cleared
        assert provider._pending_operation_callbacks == {}
        assert provider._unknown_operation_responses == {}

    @pytest.mark.it(
        "Skips callback that is set to 'None' upon subscribe completion when Paho event handler triggered early"
    )
    def test_none_callback_when_paho_on_subscribe_event_called_early(
        self, mocker, mock_mqtt_client, provider
    ):
        callback = None

        def trigger_early_on_subscribe(topic, qos):

            # Trigger on_subscribe before returning mid
            mock_mqtt_client.on_subscribe(
                client=mock_mqtt_client, userdata=None, mid=fake_mid, granted_qos=fake_qos
            )

            # Check mid has been stored as an unknown response, callback not yet called
            assert provider._pending_operation_callbacks == {}
            assert provider._unknown_operation_responses == {fake_mid: fake_mid}

            return (fake_rc, fake_mid)

        mock_mqtt_client.subscribe.side_effect = trigger_early_on_subscribe

        # Initiate subscribe
        provider.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)

        # Check callback (None) has now been cleared
        assert provider._pending_operation_callbacks == {}
        assert provider._unknown_operation_responses == {}

    @pytest.mark.it(
        "Handles multiple callbacks from multiple subscribe operations that complete out of order"
    )
    def test_multiple_callbacks(self, mocker, mock_mqtt_client, provider):
        callback1 = mocker.MagicMock()
        callback2 = mocker.MagicMock()
        callback3 = mocker.MagicMock()

        mid1 = 1
        mid2 = 2
        mid3 = 3

        mock_mqtt_client.subscribe.side_effect = [(fake_rc, mid1), (fake_rc, mid2), (fake_rc, mid3)]

        # Initiate subscribe (1 -> 2 -> 3)
        provider.subscribe(topic=fake_topic, qos=fake_qos, callback=callback1)
        provider.subscribe(topic=fake_topic, qos=fake_qos, callback=callback2)
        provider.subscribe(topic=fake_topic, qos=fake_qos, callback=callback3)

        # Check callbacks have not yet been called
        assert callback1.call_count == 0
        assert callback2.call_count == 0
        assert callback3.call_count == 0

        # Manually trigger Paho on_subscribe event handler (2 -> 3 -> 1)
        mock_mqtt_client.on_subscribe(
            client=mock_mqtt_client, userdata=None, mid=mid2, granted_qos=fake_qos
        )
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 0

        mock_mqtt_client.on_subscribe(
            client=mock_mqtt_client, userdata=None, mid=mid3, granted_qos=fake_qos
        )
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 1

        mock_mqtt_client.on_subscribe(
            client=mock_mqtt_client, userdata=None, mid=mid1, granted_qos=fake_qos
        )
        assert callback1.call_count == 1
        assert callback2.call_count == 1
        assert callback3.call_count == 1

    @pytest.mark.it("Recovers from exception in callback")
    def test_callback_raises_exception(self, mocker, mock_mqtt_client, provider):
        callback = mocker.MagicMock(side_effect=DummyException)
        mock_mqtt_client.subscribe.return_value = (fake_rc, fake_mid)

        provider.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)
        mock_mqtt_client.on_subscribe(
            client=mock_mqtt_client, userdata=None, mid=fake_mid, granted_qos=fake_qos
        )

        # Callback was called, but exception did not propagate
        assert callback.call_count == 1

    @pytest.mark.it("Recovers from exception in callback when Paho event handler triggered early")
    def test_callback_rasies_exception_when_paho_on_subscribe_triggered_early(
        self, mocker, mock_mqtt_client, provider
    ):
        callback = mocker.MagicMock(side_effect=DummyException)

        def trigger_early_on_subscribe(topic, qos):
            mock_mqtt_client.on_subscribe(
                client=mock_mqtt_client, userdata=None, mid=fake_mid, granted_qos=fake_qos
            )

            # Should not have yet called callback
            assert callback.call_count == 0

            return (fake_rc, fake_mid)

        mock_mqtt_client.subscribe.side_effect = trigger_early_on_subscribe

        # Initiate subscribe
        provider.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)

        # Callback was called, but exception did not propagate
        assert callback.call_count == 1


@pytest.mark.describe("MQTT Provider - Unsubscribe")
class TestUnsubscribe(object):
    @pytest.mark.it("Unsubscribes with Paho")
    def test_calls_paho_unsubscribe(self, mocker, mock_mqtt_client, provider):
        provider.unsubscribe(fake_topic)

        assert mock_mqtt_client.unsubscribe.call_count == 1
        assert mock_mqtt_client.unsubscribe.call_args == mocker.call(fake_topic)

    @pytest.mark.it("Raises ValueError on invalid topic string")
    @pytest.mark.parametrize("topic", [pytest.param(None), pytest.param("", id="Empty string")])
    def test_raises_value_error_invalid_topic(self, topic):
        # Manually instantiate Provider, do NOT mock paho client (paho generates this error)
        provider = MQTTProvider(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )
        with pytest.raises(ValueError):
            provider.unsubscribe(topic)

    @pytest.mark.it("Triggers callback upon unsubscribe completion")
    def test_triggers_callback_upon_paho_on_unsubscribe_event(
        self, mocker, mock_mqtt_client, provider
    ):
        callback = mocker.MagicMock()
        mock_mqtt_client.unsubscribe.return_value = (fake_rc, fake_mid)

        # Initiate unsubscribe
        provider.unsubscribe(topic=fake_topic, callback=callback)

        # Check callback is stored as pending, but not called
        assert callback.call_count == 0
        assert provider._pending_operation_callbacks == {fake_mid: callback}
        assert provider._unknown_operation_responses == {}

        # Manually trigger Paho on_unsubscribe event handler
        mock_mqtt_client.on_unsubscribe(client=mock_mqtt_client, userdata=None, mid=fake_mid)

        # Check callback has now been called, and stored values cleared
        assert callback.call_count == 1
        assert provider._pending_operation_callbacks == {}
        assert provider._unknown_operation_responses == {}

    @pytest.mark.it(
        "Triggers callback upon unsubscribe completion when Paho event handler triggered early"
    )
    def test_triggers_callback_when_paho_on_unsubscribe_event_called_early(
        self, mocker, mock_mqtt_client, provider
    ):
        callback = mocker.MagicMock()

        def trigger_early_on_unsubscribe(topic):

            # Trigger on_unsubscribe before returning mid
            mock_mqtt_client.on_unsubscribe(client=mock_mqtt_client, userdata=None, mid=fake_mid)

            # Check mid has been stored as an unknown response, callback not yet called
            assert callback.call_count == 0
            assert provider._pending_operation_callbacks == {}
            assert provider._unknown_operation_responses == {fake_mid: fake_mid}

            return (fake_rc, fake_mid)

        mock_mqtt_client.unsubscribe.side_effect = trigger_early_on_unsubscribe

        # Initiate unsubscribe
        provider.unsubscribe(topic=fake_topic, callback=callback)

        # Check callback has now been called, and stored values cleared
        assert callback.call_count == 1
        assert provider._pending_operation_callbacks == {}
        assert provider._unknown_operation_responses == {}

    @pytest.mark.it("Skips callback that is set to 'None' upon unsubscribe completion")
    def test_none_callback_upon_paho_on_unsubscribe_event(self, mocker, mock_mqtt_client, provider):
        callback = None
        mock_mqtt_client.unsubscribe.return_value = (fake_rc, fake_mid)

        # Initiate unsubscribe
        provider.unsubscribe(topic=fake_topic, callback=callback)

        # Check that callback (None) has been stored
        assert provider._pending_operation_callbacks == {fake_mid: callback}
        assert provider._unknown_operation_responses == {}

        # Manually trigger Paho on_unsubscribe event handler
        mock_mqtt_client.on_unsubscribe(client=mock_mqtt_client, userdata=None, mid=fake_mid)

        # Check that callback (None) has now been cleared
        assert provider._pending_operation_callbacks == {}
        assert provider._unknown_operation_responses == {}

    @pytest.mark.it(
        "Skips callback that is set to 'None' upon unsubscribe completion when Paho event handler triggered early"
    )
    def test_none_callback_when_paho_on_unsubscribe_event_called_early(
        self, mocker, mock_mqtt_client, provider
    ):
        callback = None

        def trigger_early_on_unsubscribe(topic):

            # Trigger on_unsubscribe before returning mid
            mock_mqtt_client.on_unsubscribe(client=mock_mqtt_client, userdata=None, mid=fake_mid)

            # Check mid has been stored as an unknown response, callback not yet called
            assert provider._pending_operation_callbacks == {}
            assert provider._unknown_operation_responses == {fake_mid: fake_mid}

            return (fake_rc, fake_mid)

        mock_mqtt_client.unsubscribe.side_effect = trigger_early_on_unsubscribe

        # Initiate unsubscribe
        provider.unsubscribe(topic=fake_topic, callback=callback)

        # Check callback (None) has now been cleared
        assert provider._pending_operation_callbacks == {}
        assert provider._unknown_operation_responses == {}

    @pytest.mark.it(
        "Handles multiple callbacks from multiple unsubscribe operations that complete out of order"
    )
    def test_multiple_callbacks(self, mocker, mock_mqtt_client, provider):
        callback1 = mocker.MagicMock()
        callback2 = mocker.MagicMock()
        callback3 = mocker.MagicMock()

        mid1 = 1
        mid2 = 2
        mid3 = 3

        mock_mqtt_client.unsubscribe.side_effect = [
            (fake_rc, mid1),
            (fake_rc, mid2),
            (fake_rc, mid3),
        ]

        # Initiate unsubscribe (1 -> 2 -> 3)
        provider.unsubscribe(topic=fake_topic, callback=callback1)
        provider.unsubscribe(topic=fake_topic, callback=callback2)
        provider.unsubscribe(topic=fake_topic, callback=callback3)

        # Check callbacks have not yet been called
        assert callback1.call_count == 0
        assert callback2.call_count == 0
        assert callback3.call_count == 0

        # Manually trigger Paho on_unsubscribe event handler (2 -> 3 -> 1)
        mock_mqtt_client.on_unsubscribe(client=mock_mqtt_client, userdata=None, mid=mid2)
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 0

        mock_mqtt_client.on_unsubscribe(client=mock_mqtt_client, userdata=None, mid=mid3)
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 1

        mock_mqtt_client.on_unsubscribe(client=mock_mqtt_client, userdata=None, mid=mid1)
        assert callback1.call_count == 1
        assert callback2.call_count == 1
        assert callback3.call_count == 1

    @pytest.mark.it("Recovers from exception in callback")
    def test_callback_raises_exception(self, mocker, mock_mqtt_client, provider):
        callback = mocker.MagicMock(side_effect=DummyException)
        mock_mqtt_client.unsubscribe.return_value = (fake_rc, fake_mid)

        provider.unsubscribe(topic=fake_topic, callback=callback)
        mock_mqtt_client.on_unsubscribe(client=mock_mqtt_client, userdata=None, mid=fake_mid)

        # Callback was called, but exception did not propagate
        assert callback.call_count == 1

    @pytest.mark.it("Recovers from exception in callback when Paho event handler triggered early")
    def test_callback_rasies_exception_when_paho_on_unsubscribe_triggered_early(
        self, mocker, mock_mqtt_client, provider
    ):
        callback = mocker.MagicMock(side_effect=DummyException)

        def trigger_early_on_unsubscribe(topic):
            mock_mqtt_client.on_unsubscribe(client=mock_mqtt_client, userdata=None, mid=fake_mid)

            # Should not have yet called callback
            assert callback.call_count == 0

            return (fake_rc, fake_mid)

        mock_mqtt_client.unsubscribe.side_effect = trigger_early_on_unsubscribe

        # Initiate unsubscribe
        provider.unsubscribe(topic=fake_topic, callback=callback)

        # Callback was called, but exception did not propagate
        assert callback.call_count == 1


@pytest.mark.describe("MQTT Provider - Publish")
class TestPublish(object):
    @pytest.fixture
    def message_info(self, mocker):
        mi = mqtt.MQTTMessageInfo(fake_mid)
        mi.rc = fake_rc
        return mi

    @pytest.mark.it("Publishes with Paho")
    @pytest.mark.parametrize(
        "qos",
        [pytest.param(0, id="QoS 0"), pytest.param(1, id="QoS 1"), pytest.param(2, id="QoS 2")],
    )
    def test_calls_paho_publish(self, mocker, mock_mqtt_client, provider, qos):
        provider.publish(topic=fake_topic, payload=fake_payload, qos=qos)

        assert mock_mqtt_client.publish.call_count == 1
        assert mock_mqtt_client.publish.call_args == mocker.call(
            topic=fake_topic, payload=fake_payload, qos=qos
        )

    @pytest.mark.it("Raises ValueError on invalid QoS")
    @pytest.mark.parametrize("qos", [pytest.param(-1, id="QoS < 0"), pytest.param(3, id="Qos > 2")])
    def test_raises_value_error_invalid_qos(self, qos):
        # Manually instantiate Provider, do NOT mock paho client (paho generates this error)
        provider = MQTTProvider(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )
        with pytest.raises(ValueError):
            provider.publish(topic=fake_topic, payload=fake_payload, qos=qos)

    @pytest.mark.it("Raises ValueError on invalid topic string")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param(None),
            pytest.param("", id="Empty string"),
            pytest.param("+", id="Contains wildcard (+)"),
        ],
    )
    def test_raises_value_error_invalid_topic(self, topic):
        # Manually instantiate Provider, do NOT mock paho client (paho generates this error)
        provider = MQTTProvider(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )
        with pytest.raises(ValueError):
            provider.publish(topic=topic, payload=fake_payload, qos=fake_qos)

    @pytest.mark.it("Raises ValueError on invalid payload")
    @pytest.mark.parametrize("payload", [str(b"0" * 268435456)], ids=["Payload > 268435455 bytes"])
    def test_raises_value_error_invalid_payload(self, payload):
        # Manually instantiate Provider, do NOT mock paho client (paho generates this error)
        provider = MQTTProvider(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )
        with pytest.raises(ValueError):
            provider.publish(topic=fake_topic, payload=payload, qos=fake_qos)

    @pytest.mark.it("Triggers callback upon publish completion")
    def test_triggers_callback_upon_paho_on_publish_event(
        self, mocker, mock_mqtt_client, provider, message_info
    ):
        callback = mocker.MagicMock()
        mock_mqtt_client.publish.return_value = message_info

        # Initiate publish
        provider.publish(topic=fake_topic, payload=fake_payload, callback=callback)

        # Check callback is stored as pending, but not called
        assert callback.call_count == 0
        assert provider._pending_operation_callbacks == {message_info.mid: callback}
        assert provider._unknown_operation_responses == {}

        # Manually trigger Paho on_publish event handler
        mock_mqtt_client.on_publish(client=mock_mqtt_client, userdata=None, mid=message_info.mid)

        # Check callback has now been called, and stored values cleared
        assert callback.call_count == 1
        assert provider._pending_operation_callbacks == {}
        assert provider._unknown_operation_responses == {}

    @pytest.mark.it(
        "Triggers callback upon publish completion when Paho event handler triggered early"
    )
    def test_triggers_callback_when_paho_on_publish_event_called_early(
        self, mocker, mock_mqtt_client, provider, message_info
    ):
        callback = mocker.MagicMock()

        def trigger_early_on_publish(topic, payload, qos):

            # Trigger on_publish before returning message_info
            mock_mqtt_client.on_publish(
                client=mock_mqtt_client, userdata=None, mid=message_info.mid
            )

            # Check mid has been stored as an unknown response, callback not yet called
            assert callback.call_count == 0
            assert provider._pending_operation_callbacks == {}
            assert provider._unknown_operation_responses == {message_info.mid: message_info.mid}

            return message_info

        mock_mqtt_client.publish.side_effect = trigger_early_on_publish

        # Initiate publish
        provider.publish(topic=fake_topic, payload=fake_payload, callback=callback)

        # Check callback has now been called, and stored values cleared
        assert callback.call_count == 1
        assert provider._pending_operation_callbacks == {}
        assert provider._unknown_operation_responses == {}

    @pytest.mark.it("Skips callback that is set to 'None' upon publish completion")
    def test_none_callback_upon_paho_on_publish_event(
        self, mocker, mock_mqtt_client, provider, message_info
    ):
        mock_mqtt_client.publish.return_value = message_info
        callback = None

        # Initiate publish
        provider.publish(topic=fake_topic, payload=fake_payload, callback=callback)

        # Check that callback (None) has been stored
        assert provider._pending_operation_callbacks == {message_info.mid: callback}
        assert provider._unknown_operation_responses == {}

        # Manually trigger Paho on_publish event handler
        mock_mqtt_client.on_publish(client=mock_mqtt_client, userdata=None, mid=message_info.mid)

        # Check that callback (None) has now been cleared
        assert provider._pending_operation_callbacks == {}
        assert provider._unknown_operation_responses == {}

    @pytest.mark.it(
        "Skips callback that is set to 'None' upon publish completion when Paho event handler triggered early"
    )
    def test_none_callback_when_paho_on_publish_event_called_early(
        self, mocker, mock_mqtt_client, provider, message_info
    ):
        callback = None

        def trigger_early_on_publish(topic, payload, qos):

            # Trigger on_publish before returning message_info
            mock_mqtt_client.on_publish(
                client=mock_mqtt_client, userdata=None, mid=message_info.mid
            )

            # Check mid has been stored as an unknown response, callback not yet called
            assert provider._pending_operation_callbacks == {}
            assert provider._unknown_operation_responses == {message_info.mid: message_info.mid}

            return message_info

        mock_mqtt_client.publish.side_effect = trigger_early_on_publish

        # Initiate publish
        provider.publish(topic=fake_topic, payload=fake_payload, callback=callback)

        # Check callback (None) has now been cleared
        assert provider._pending_operation_callbacks == {}
        assert provider._unknown_operation_responses == {}

    @pytest.mark.it(
        "Handles multiple callbacks from multiple publish operations that complete out of order"
    )
    def test_multiple_callbacks(self, mocker, mock_mqtt_client, provider):
        callback1 = mocker.MagicMock()
        callback2 = mocker.MagicMock()
        callback3 = mocker.MagicMock()

        mid1 = 1
        mid2 = 2
        mid3 = 3

        mock_mqtt_client.publish.side_effect = [
            mqtt.MQTTMessageInfo(mid1),
            mqtt.MQTTMessageInfo(mid2),
            mqtt.MQTTMessageInfo(mid3),
        ]

        # Initiate publish (1 -> 2 -> 3)
        provider.publish(topic=fake_topic, payload=fake_payload, callback=callback1)
        provider.publish(topic=fake_topic, payload=fake_payload, callback=callback2)
        provider.publish(topic=fake_topic, payload=fake_payload, callback=callback3)

        # Check callbacks have not yet been called
        assert callback1.call_count == 0
        assert callback2.call_count == 0
        assert callback3.call_count == 0

        # Manually trigger Paho on_publish event handler (2 -> 3 -> 1)
        mock_mqtt_client.on_publish(client=mock_mqtt_client, userdata=None, mid=mid2)
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 0

        mock_mqtt_client.on_publish(client=mock_mqtt_client, userdata=None, mid=mid3)
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 1

        mock_mqtt_client.on_publish(client=mock_mqtt_client, userdata=None, mid=mid1)
        assert callback1.call_count == 1
        assert callback2.call_count == 1
        assert callback3.call_count == 1

    @pytest.mark.it("Recovers from exception in callback")
    def test_callback_raises_exception(self, mocker, mock_mqtt_client, provider, message_info):
        callback = mocker.MagicMock(side_effect=DummyException)
        mock_mqtt_client.publish.return_value = message_info

        provider.publish(topic=fake_topic, payload=fake_payload, callback=callback)
        mock_mqtt_client.on_publish(client=mock_mqtt_client, userdata=None, mid=message_info.mid)

        # Callback was called, but exception did not propagate
        assert callback.call_count == 1

    @pytest.mark.it("Recovers from exception in callback when Paho event handler triggered early")
    def test_callback_rasies_exception_when_paho_on_publish_triggered_early(
        self, mocker, mock_mqtt_client, provider, message_info
    ):
        callback = mocker.MagicMock(side_effect=DummyException)

        def trigger_early_on_publish(topic, payload, qos):
            mock_mqtt_client.on_publish(
                client=mock_mqtt_client, userdata=None, mid=message_info.mid
            )

            # Should not have yet called callback
            assert callback.call_count == 0

            return message_info

        mock_mqtt_client.publish.side_effect = trigger_early_on_publish

        # Initiate publish
        provider.publish(topic=fake_topic, payload=fake_payload, callback=callback)

        # Callback was called, but exception did not propagate
        assert callback.call_count == 1


@pytest.mark.describe("MQTT Provider - Message Received")
class TestMessageReceived(object):
    @pytest.fixture()
    def message(self):
        message = mqtt.MQTTMessage(mid=fake_mid, topic=fake_topic.encode())
        message.payload = fake_payload
        message.qos = fake_qos
        return message

    @pytest.mark.it(
        "Triggers on_mqtt_message_received event handler callback upon receiving message"
    )
    def test_calls_event_handler_callback(self, mocker, mock_mqtt_client, provider, message):
        callback = mocker.MagicMock()
        provider.on_mqtt_message_received = callback

        # Manually trigger Paho on_message event_handler
        mock_mqtt_client.on_message(client=mock_mqtt_client, userdata=None, mqtt_message=message)

        # Verify provider.on_mqtt_message_received was called
        assert callback.call_count == 1
        assert callback.call_args == mocker.call(message.topic, message.payload)

    @pytest.mark.it(
        "Skips on_mqtt_message_received event handler callback if set to 'None' upon receiving message"
    )
    def test_skips_none_event_handler_callback(self, mocker, mock_mqtt_client, provider, message):
        assert provider.on_mqtt_message_received is None

        # Manually trigger Paho on_message event_handler
        mock_mqtt_client.on_message(client=mock_mqtt_client, userdata=None, mqtt_message=message)

        # No further asserts required - this is a test to show that it skips a callback.
        # Not raising an exception == test passed

    @pytest.mark.it("Recovers from exception in on_mqtt_message_received event handler callback")
    def test_event_handler_callback_raises_exception(
        self, mocker, mock_mqtt_client, provider, message
    ):
        event_cb = mocker.MagicMock(side_effect=DummyException)
        provider.on_mqtt_message_received = event_cb

        mock_mqtt_client.on_message(client=mock_mqtt_client, userdata=None, mqtt_message=message)

        # Callback was called, but exception did not propagate
        assert event_cb.call_count == 1


@pytest.mark.describe("MQTT Provider - Misc.")
class TestMisc(object):
    @pytest.mark.it(
        "Handles multiple callbacks from multiple different types of operations that complete out of order"
    )
    def test_multiple_callbacks_multiple_ops(self, mocker, mock_mqtt_client, provider):
        callback1 = mocker.MagicMock()
        callback2 = mocker.MagicMock()
        callback3 = mocker.MagicMock()

        mid1 = 1
        mid2 = 2
        mid3 = 3

        topic1 = "topic1"
        topic2 = "topic2"
        topic3 = "topic3"

        mock_mqtt_client.subscribe.return_value = (fake_rc, mid1)
        mock_mqtt_client.publish.return_value = mqtt.MQTTMessageInfo(mid2)
        mock_mqtt_client.unsubscribe.return_value = (fake_rc, mid3)

        # Initiate operations (1 -> 2 -> 3)
        provider.subscribe(topic=topic1, qos=fake_qos, callback=callback1)
        provider.publish(topic=topic2, payload="payload", qos=fake_qos, callback=callback2)
        provider.unsubscribe(topic=topic3, callback=callback3)

        # Check callbacks have not yet been called
        assert callback1.call_count == 0
        assert callback2.call_count == 0
        assert callback3.call_count == 0

        # Manually trigger Paho on_unsubscribe event handler (2 -> 3 -> 1)
        mock_mqtt_client.on_publish(client=mock_mqtt_client, userdata=None, mid=mid2)
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 0

        mock_mqtt_client.on_unsubscribe(client=mock_mqtt_client, userdata=None, mid=mid3)
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 1

        mock_mqtt_client.on_subscribe(
            client=mock_mqtt_client, userdata=None, mid=mid1, granted_qos=fake_qos
        )
        assert callback1.call_count == 1
        assert callback2.call_count == 1
        assert callback3.call_count == 1
