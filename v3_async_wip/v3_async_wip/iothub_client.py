# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import ssl
import urllib
from typing import Optional, Dict, Any
from . import constant, mqtt_client
from azure.iot.device import user_agent  # TODO: clean up this import for V3
from azure.iot.device.iothub.pipeline import (
    mqtt_topic_iothub as mqtt_topic,
)  # TODO: clean up this import for V3
from .options import ClientOptions
from .models import Message, MethodResponse

logger = logging.getLogger(__name__)

# TODO: enable/disable feature
# TODO: SAS renewal
# TODO: Data receive

# TODO: should this be just for MQTT, or both MQTT and HTTP? Leaning towards the latter


class IoTHubClient:
    def __init__(
        self, client_options: ClientOptions, device_id: str, module_id: Optional[str] = None
    ) -> None:
        self._device_id = device_id
        self._module_id = module_id

        self._mqtt_client = _create_mqtt_client(client_options, device_id, module_id)

        # TODO: do we need to track what features are enabled?

    async def connect(self) -> None:
        await self._mqtt_client.connect()

    async def disconnect(self) -> None:
        await self._mqtt_client.disconnect()

    async def enable_feature(self, feature: str) -> None:  # TODO: can we use enum?
        pass

    async def disable_feature(self, feature: str) -> None:  # TODO: can we use enum?
        pass

    async def send_message(self, message: Message) -> None:
        telemetry_topic = mqtt_topic.get_telemetry_topic_for_publish(
            self._device_id, self._module_id
        )
        topic = mqtt_topic.encode_message_properties_in_topic(message, telemetry_topic)
        await self._mqtt_client.publish(topic, message.data)

    async def send_method_response(self, method_response: MethodResponse):
        pass

    async def send_twin_patch(
        self, patch: Dict[Any, Any]
    ) -> None:  # TODO: is this typing accurate?
        pass

    async def get_twin(self) -> Dict[Any, Any]:  # TODO: is this typing accurate?
        pass


def _create_mqtt_client(
    client_options: ClientOptions, device_id: str, module_id: Optional[str]
) -> mqtt_client.MQTTClient:
    logger.debug("Creating MQTTClient")

    if module_id:
        client_id = "{}/{}".format(device_id, module_id)
        logger.debug("Using IoTHub Module. Client ID is {}".format(client_id))
    else:
        client_id = device_id
        logger.debug("Using IoTHub Device. Client ID is {}".format(client_id))

    if client_options.gateway_hostname:
        logger.debug("Gateway Hostname is present. Using Gateway Hostname as Hostname")
        hostname = client_options.gateway_hostname
    else:
        logger.debug("Gateway Hostname not present. Using Hostname as Hostname")
        hostname = client_options.hostname

    if client_options.websockets:
        logger.debug("Using MQTT over websockets")
        transport = "websockets"
        port = 443
        websockets_path = "/$iothub/websocket"
    else:
        logger.debug("Using MQTT over TCP")
        transport = "tcp"
        port = 8883
        websockets_path = None

    ssl_context = _create_ssl_context(client_options)

    client = mqtt_client.MQTTClient(
        client_id=client_id,
        hostname=hostname,
        port=port,
        transport=transport,
        keep_alive=client_options.keep_alive,
        auto_reconnect=client_options.auto_reconnect,
        reconnect_interval=client_options.auto_reconnect_interval,
        ssl_context=ssl_context,
        websockets_path=websockets_path,
        proxy_options=client_options.proxy_options,
    )

    # NOTE: we use the original hostname here, even if gateway hostname is set
    username = _create_username(
        hostname=client_options.hostname,
        client_id=client_id,
        product_info=client_options.product_info,
    )
    logger.debug("Using {} as username".format(username))

    if client_options.sastoken:
        logger.debug("Using SASToken as password")
        password = client_options.sastoken
    else:
        logger.debug("No password used")
        password = None

    client.set_credentials(username, password)

    return client


# TODO: ensure client_id is str with sanitization in the options object, if that's where it belongs
def _create_username(hostname: str, client_id: str, product_info: Optional[str]) -> str:
    query_param_seq = []

    # Apply query parameters (i.e. key1=value1&key2=value2...&keyN=valueN format)
    if product_info.startswith(constant.DIGITAL_TWIN_PREFIX):  # Digital Twin Stuff
        # TODO: do we need this in V3?
        query_param_seq.append(("api-version", constant.DIGITAL_TWIN_API_VERSION))
        query_param_seq.append(("DeviceClientType", user_agent.get_iothub_user_agent()))
        query_param_seq.append((constant.DIGITAL_TWIN_QUERY_HEADER, product_info))
    else:
        query_param_seq.append(("api-version", constant.IOTHUB_API_VERSION))
        query_param_seq.append(
            ("DeviceClientType", user_agent.get_iothub_user_agent() + product_info)
        )

    # NOTE: Client ID (including the device and/or module ids that are in it)
    # is NOT url encoded as part of the username. Neither is the hostname.
    # The sequence of key/value property pairs (query_param_seq) however, MUST have all
    # keys and values URL encoded.
    # See the repo wiki article for details:
    # https://github.com/Azure/azure-iot-sdk-python/wiki/URL-Encoding-(MQTT)
    username = "{hostname}/{client_id}/?{query_params}".format(
        hostname=hostname,
        client_id=client_id,
        query_params=urllib.parse.urlencode(query_param_seq, quote_via=urllib.parse.quote),
    )
    return username


def _create_ssl_context(client_options: ClientOptions) -> ssl.SSLContext:
    ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.check_hostname = True

    if client_options.server_verification_cert:
        logger.debug("Configuring SSLContext with custom server verification cert")
        ssl_context.load_verify_locations(cadata=client_options.server_verification_cert)
    else:
        logger.debug("Configuring SSLContext with default certs")
        ssl_context.load_default_certs()

    if client_options.cipher:
        logger.debug("Configuring SSLContext with cipher suites")
        ssl_context.set_ciphers(client_options.cipher)
    else:
        logger.debug("Not using cipher suites")

    if client_options.x509_cert:
        logger.debug("Configuring SSLContext with client-side X509 certificate and key")
        ssl_context.load_cert_chain(
            client_options.x509_cert.certificate_file,
            client_options.x509_cert.key_file,
            client_options.x509_cert.pass_phrase,
        )
    else:
        logger.debug("Not using X509 certificates")

    return ssl_context
