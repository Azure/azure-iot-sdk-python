# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import json
import logging
import urllib.parse
from typing import Optional, Union, AsyncGenerator
from .custom_typing import TwinPatch, Twin
from .iot_exceptions import IoTHubError, IoTHubClientError
from .models import Message, MethodResponse, MethodRequest
from . import config, constant, user_agent
from . import request_response as rr
from . import mqtt_client as mqtt
from . import mqtt_topic_iothub as mqtt_topic

# TODO: update docstrings with correct class paths once repo structured better

logger = logging.getLogger(__name__)

DEFAULT_RECONNECT_INTERVAL: int = 10

# TODO: add exceptions to docstring
# TODO: background exceptions how
# TODO: non-background exceptions
# TODO: error handling in generators


class IoTHubMQTTClient:
    def __init__(
        self,
        client_config: config.IoTHubClientConfig,
    ) -> None:
        """
        Instantiate the client

        :param client_config: The config object for the client
        :type client_config: :class:`IoTHubClientConfig`
        """
        # Identity
        self._device_id = client_config.device_id
        self._module_id = client_config.module_id
        self._client_id = _format_client_id(self._device_id, self._module_id)
        self._username = _format_username(
            # NOTE: Always use the original hostname, even if gateway hostname is set
            hostname=client_config.hostname,
            client_id=self._client_id,
            product_info=client_config.product_info,
        )

        # SAS (Optional)
        self._sastoken_provider = client_config.sastoken_provider

        # MQTT Configuration
        self._mqtt_client = _create_mqtt_client(self._client_id, client_config)
        if self._sastoken_provider:
            logger.debug("Using SASToken as password")
            password = str(self._sastoken_provider.get_current_sastoken())
        else:
            logger.debug("No password used")
            password = None
        self._mqtt_client.set_credentials(self._username, password)

        # Create incoming IoTHub data generators
        # TODO: expose these via method to make the device/module split cleaner
        self.incoming_c2d_messages: AsyncGenerator[Message, None] = _create_c2d_message_generator(
            self._device_id, self._mqtt_client
        )
        self.incoming_input_messages: Optional[
            AsyncGenerator[Message, None]
        ] = _create_input_message_generator(self._device_id, self._module_id, self._mqtt_client)
        self.incoming_method_requests: AsyncGenerator[
            MethodRequest, None
        ] = _create_method_request_generator(self._mqtt_client)
        self.incoming_twin_patches: AsyncGenerator[TwinPatch, None] = _create_twin_patch_generator(
            self._mqtt_client
        )

        # Internal request/response infrastructure
        self._request_ledger = rr.RequestLedger()
        self._twin_responses_enabled = False

        # Background Tasks
        self._process_twin_responses_bg_task: asyncio.Task[None] = asyncio.create_task(
            self._process_twin_responses()
        )
        self._keep_credentials_fresh_bg_task: Optional[asyncio.Task[None]]
        if self._sastoken_provider:
            self._keep_credentials_fresh_bg_task = asyncio.create_task(
                self._keep_credentials_fresh()
            )
        else:
            self._keep_credentials_fresh_bg_task = None

    async def _enable_twin_responses(self) -> None:
        """Enable receiving of twin responses (for twin requests, or twin patches) from IoTHub"""
        logger.debug("Enabling receive of twin responses...")
        topic = mqtt_topic.get_twin_response_topic_for_subscribe()
        await self._mqtt_client.subscribe(topic)
        self._twin_responses_enabled = True
        logger.debug("Twin responses receive enabled")

    # TODO: add background exception handling
    async def _process_twin_responses(self) -> None:
        """Run indefinitely, matching twin responses with request ID"""
        logger.debug("Starting the 'process_twin_responses' background task")
        twin_response_topic = mqtt_topic.get_twin_response_topic_for_subscribe()
        twin_responses = self._mqtt_client.get_incoming_message_generator(twin_response_topic)

        async for mqtt_message in twin_responses:
            request_id = mqtt_topic.extract_request_id_from_twin_response_topic(mqtt_message.topic)
            status_code = int(
                mqtt_topic.extract_status_code_from_twin_response_topic(mqtt_message.topic)
            )
            # NOTE: We don't know what the content of the body is until we match the rid, so don't
            # do more than just decode it here - leave interpreting the string to the coroutine
            # waiting for the response.
            response_body = mqtt_message.payload.decode("utf-8")
            logger.debug("Twin response received (rid: {})".format(request_id))
            response = rr.Response(request_id=request_id, status=status_code, body=response_body)
            try:
                await self._request_ledger.match_response(response)
            except KeyError:
                # NOTE: This should only happen in edge cases involving cancellation of
                # in-flight operations
                logger.warning("Twin response (rid: {}) does not match any request")

    async def _keep_credentials_fresh(self) -> None:
        """Run indefinitely, updating MQTT credentials when new SAS Token is available"""
        logger.debug("Starting the 'keep_credentials_fresh' background task")
        while True:
            if self._sastoken_provider:
                logger.debug("Waiting for new SAS Token to become available")
                new_sastoken = await self._sastoken_provider.wait_for_new_sastoken()
                logger.debug("New SAS Token available, updating MQTTClient credentials")
                self._mqtt_client.set_credentials(self._username, str(new_sastoken))
                # TODO: should we reconnect here? Or just wait for drop?
            else:
                # NOTE: This should never execute, it's mostly just here to keep the
                # type checker happy
                logger.error("No SasTokenProvider. Cannot update credentials")
                break

    async def shutdown(self) -> None:
        """
        Shut down the client.

        Invoke only when completely finished with the client for graceful exit.
        Cannot be cancelled - if you try, the client will still fully shut down as much as
        possible.
        """
        # NOTE: .disconnect() really shouldn't fail, but if it does, we temporarily suppress
        # the exception so we can still do as much cleanup as possible.
        cached_exception: Optional[Union[Exception, asyncio.CancelledError]] = None
        logger.debug("Attempting disconnect in shutdown")
        try:
            await self.disconnect()
        except asyncio.CancelledError as e:
            logger.warning("Cancellation during shutdown. Still attempting to clean up.")
            cached_exception = e
        except Exception as e:
            logger.warning("Unexpected error disconnecting. Continuing shutdown procedure")
            cached_exception = e

        cancelled_tasks = []

        logger.debug("Cancelling 'process_twin_responses' background task")
        self._process_twin_responses_bg_task.cancel()
        cancelled_tasks.append(self._process_twin_responses_bg_task)

        if self._keep_credentials_fresh_bg_task:
            logger.debug("Cancelling 'keep_credentials_fresh' background task")
            self._keep_credentials_fresh_bg_task.cancel()
            cancelled_tasks.append(self._keep_credentials_fresh_bg_task)

        # Wait for the cancellation to complete before returning
        # NOTE: If cancelled while awaiting here, all tasks in gather will still be cancelled
        # because the cancellations have already been issued.
        # NOTE: Also, cancelling a gather implicitly cancels all the tasks that are gathered anyway
        await asyncio.gather(*cancelled_tasks, return_exceptions=True)

        if cached_exception:
            raise cached_exception

    async def connect(self) -> None:
        """Connect to IoTHub

        :raises: MQTTConnectionFailedError if there is a failure connecting
        """
        logger.debug("Connecting to IoTHub...")
        await self._mqtt_client.connect()
        logger.debug("Connect succeeded")

    async def disconnect(self) -> None:
        """Disconnect from IoTHub"""
        logger.debug("Disconnecting from IoTHub...")
        await self._mqtt_client.disconnect()
        logger.debug("Disconnect succeeded")

    async def send_message(self, message: Message) -> None:
        """Send a telemetry message to IoTHub.

        :param message: The Message to be sent
        :type message: :class:`models.Message`

        :raises: MQTTError if there is an error sending the Message
        :raises: ValueError if the size of the Message payload is too large
        """
        # Format topic with message properties
        telemetry_topic = mqtt_topic.get_telemetry_topic_for_publish(
            self._device_id, self._module_id
        )
        topic = mqtt_topic.insert_message_properties_in_topic(
            topic=telemetry_topic,
            system_properties=message.get_system_properties_dict(),
            custom_properties=message.custom_properties,
        )
        # Format payload based on content configuration
        if message.content_type == "application/json":
            str_payload = json.dumps(message.payload)
        else:
            str_payload = str(message.payload)
        byte_payload = str_payload.encode(message.content_encoding)
        # Send
        logger.debug("Sending telemetry message to IoTHub...")
        await self._mqtt_client.publish(topic, byte_payload)
        logger.debug("Sending telemetry message succeeded")

    async def send_method_response(self, method_response: MethodResponse):
        """Send a method response to IoTHub.

        :param method_response: The MethodResponse to be sent
        :type method_response: :class:`models.MethodResponse`

        :raises: MQTTError if there is an error sending the MethodResponse
        :raises: ValueError if the size of the MethodResponse payload is too large
        """
        topic = mqtt_topic.get_method_topic_for_publish(
            method_response.request_id, method_response.status
        )
        payload = json.dumps(method_response.payload)
        logger.debug(
            "Sending method response to IoTHub... (rid: {})".format(method_response.request_id)
        )
        await self._mqtt_client.publish(topic, payload)
        logger.debug(
            "Sending method response succeeded (rid: {})".format(method_response.request_id)
        )

    async def send_twin_patch(self, patch: TwinPatch) -> None:
        """Send a twin patch to IoTHub

        :param patch: The JSON patch to send
        :type patch: dict, list, tuple, str, int, float, bool, None

        :raises: MQTTError if there is an error sending the twin patch
        :raises: ValueError if the size of the the twin patch is too large
        :raises: CancelledError if enabling twin responses is cancelled by network failure
        """
        if not self._twin_responses_enabled:
            await self._enable_twin_responses()

        request = await self._request_ledger.create_request()
        try:
            topic = mqtt_topic.get_twin_patch_topic_for_publish(request.request_id)

            # Send the patch to IoTHub
            try:
                logger.debug("Sending twin patch to IoTHub... (rid: {})".format(request.request_id))
                await self._mqtt_client.publish(topic, json.dumps(patch))
            except asyncio.CancelledError:
                logger.warning(
                    "Attempt to send twin patch to IoTHub was cancelled while in flight. It may or may not have been received (rid: {})".format(
                        request.request_id
                    )
                )
                raise
            except Exception:
                logger.error(
                    "Sending twin patch to IoTHub failed (rid: {})".format(request.request_id)
                )
                raise

            # Wait for a response from IoTHub
            try:
                logger.debug(
                    "Waiting for response to the twin patch from IoTHub... (rid: {})".format(
                        request.request_id
                    )
                )
                response = await request.get_response()
            except asyncio.CancelledError:
                logger.debug(
                    "Attempt to send twin patch to IoTHub was cancelled while waiting for response. If the response arrives, it will be discarded (rid: {})".format(
                        request.request_id
                    )
                )
                raise

            # Interpret response
            logger.debug(
                "Received twin patch response with status {} (rid: {})".format(
                    response.status, request.request_id
                )
            )
            # TODO: should body be logged? Is there useful info there?
            if response.status != 200:
                raise IoTHubError(
                    "IoTHub responded to twin patch with a failed status - {}".format(
                        response.status
                    )
                )
        finally:
            # If an exception caused exit before a pending request could be matched with a response
            # then manually delete to prevent leaks.
            if request.request_id in self._request_ledger:
                await self._request_ledger.delete_request(request.request_id)

    async def get_twin(self) -> Twin:
        """Request a full twin from IoTHub

        :returns: The full twin as a JSON object
        :rtype: dict

        :raises: MQTTError if there is an error sending the twin request
        :raises: CancelledError if enabling twin responses is cancelled by network failure
        """
        if not self._twin_responses_enabled:
            await self._enable_twin_responses()

        request = await self._request_ledger.create_request()
        try:
            topic = mqtt_topic.get_twin_request_topic_for_publish(request_id=request.request_id)

            # Send the twin request to IoTHub
            try:
                logger.debug(
                    "Sending get twin request to IoTHub... (rid: {})".format(request.request_id)
                )
                await self._mqtt_client.publish(topic, " ")
            except asyncio.CancelledError:
                logger.warning(
                    "Attempt to send get twin request to IoTHub was cancelled while in flight. It may or may not have been received (rid: {})".format(
                        request.request_id
                    )
                )
                raise
            except Exception:
                logger.error(
                    "Sending get twin request to IoTHub failed (rid: {})".format(request.request_id)
                )
                raise

            # Wait for a response from IoTHub
            try:
                logger.debug(
                    "Waiting to receive twin from IoTHub... (rid: {})".format(request.request_id)
                )
                response = await request.get_response()
            except asyncio.CancelledError:
                logger.debug(
                    "Attempt to get twin from IoTHub was cancelled while waiting for a response. If the response arrives, it will be discarded (rid: {})".format(
                        request.request_id
                    )
                )
                raise
        finally:
            # If an exception caused exit before a pending request could be matched with a response
            # then manually delete to prevent leaks.
            if request.request_id in self._request_ledger:
                await self._request_ledger.delete_request(request.request_id)

        # Interpret response
        if response.status != 200:
            raise IoTHubError(
                "IoTHub responded to get twin request with a failed status - {}".format(
                    response.status
                )
            )
        else:
            logger.debug("Received twin from IoTHub (rid: {})".format(request.request_id))
            twin: Twin = json.loads(response.body)
            return twin

    async def enable_c2d_message_receive(self) -> None:
        """Enable the ability to receive C2D messages

        :raises: MQTTError if there is an error enabling C2D message receive
        :raises: CancelledError if enabling C2D message receive is cancelled by network failure
        :raises: IoTHubClientError if client not configured for a Device
        """
        if self._module_id:
            raise IoTHubClientError("C2D messages not available on Modules")
        logger.debug("Enabling receive for C2D messages...")
        topic = mqtt_topic.get_c2d_topic_for_subscribe(self._device_id)
        await self._mqtt_client.subscribe(topic)
        logger.debug("C2D message receive enabled")

    async def disable_c2d_message_receive(self) -> None:
        """Disable the ability to receive C2D messages

        :raises: MQTTError if there is an error disabling C2D message receive
        :raises: CancelledError if disabling C2D message receive is cancelled by network failure
        :raises: IoTHubClientError if client not configured for a Device
        """
        if self._module_id:
            raise IoTHubClientError("C2D messages not available on Modules")
        logger.debug("Disabling receive for C2D messages...")
        topic = mqtt_topic.get_c2d_topic_for_subscribe(self._device_id)
        await self._mqtt_client.unsubscribe(topic)
        logger.debug("C2D message receive disabled")

    async def enable_input_message_receive(self) -> None:
        """Enable the ability to receive input messages

        :raises: MQTTError if there is an error enabling input message receive
        :raises: CancelledError if enabling input message receive is cancelled by network failure
        :raises: IoTHubClientError if client not configured for a Module
        """
        if not self._module_id:
            raise IoTHubClientError("Input messages not available on Devices")
        logger.debug("Enabling receive for input messages...")
        topic = mqtt_topic.get_input_topic_for_subscribe(self._device_id, self._module_id)
        await self._mqtt_client.subscribe(topic)
        logger.debug("Input message receive enabled")

    async def disable_input_message_receive(self) -> None:
        """Disable the ability to receive input messages

        :raises: MQTTError if there is an error disabling input message receive
        :raises: CancelledError if disabling input message receive is cancelled by network failure
        :raises: IoTHubClientError if client not configured for a Module
        """
        if not self._module_id:
            raise IoTHubClientError("Input messages not available on Devices")
        logger.debug("Disabling receive for input messages...")
        topic = mqtt_topic.get_input_topic_for_subscribe(self._device_id, self._module_id)
        await self._mqtt_client.unsubscribe(topic)
        logger.debug("Input message receive disabled")

    async def enable_method_request_receive(self) -> None:
        """Enable the ability to receive method requests

        :raises: MQTTError if there is an error enabling method request receive
        :raises: CancelledError if enabling method request receive is cancelled by network failure
        """
        logger.debug("Enabling receive for method requests...")
        topic = mqtt_topic.get_method_topic_for_subscribe()
        await self._mqtt_client.subscribe(topic)
        logger.debug("Method request receive enabled")

    async def disable_method_request_receive(self) -> None:
        """Disable the ability to receive method requests

        :raises: MQTTError if there is an error disabling method request receive
        :raises: CancelledError if disabling method request receive is cancelled by network failure
        """
        logger.debug("Disabling receive for method requests...")
        topic = mqtt_topic.get_method_topic_for_subscribe()
        await self._mqtt_client.unsubscribe(topic)
        logger.debug("Method request receive disabled")

    async def enable_twin_patch_receive(self) -> None:
        """Enable the ability to receive twin patches

        :raises: MQTTError if there is an error enabling twin patch receive
        :raises: CancelledError if enabling twin patch receive is cancelled by network failure
        """
        logger.debug("Enabling receive for twin patches...")
        topic = mqtt_topic.get_twin_patch_topic_for_subscribe()
        await self._mqtt_client.subscribe(topic)
        logger.debug("Twin patch receive enabled")

    async def disable_twin_patch_receive(self) -> None:
        """Disable the ability to receive twin patches

        :raises: MQTTError if there is an error disabling twin patch receive
        :raises: CancelledError if disabling twin patch receive is cancelled by network failure
        """
        logger.debug("Disabling receive for twin patches...")
        topic = mqtt_topic.get_twin_patch_topic_for_subscribe()
        await self._mqtt_client.unsubscribe(topic)
        logger.debug("Twin patch receive disabled")


def _format_client_id(device_id: str, module_id: Optional[str] = None) -> str:
    if module_id:
        client_id = "{}/{}".format(device_id, module_id)
    else:
        client_id = device_id
    return client_id


def _create_mqtt_client(
    client_id: str, client_config: config.IoTHubClientConfig
) -> mqtt.MQTTClient:
    logger.debug("Creating MQTTClient")

    if client_config.module_id:
        logger.debug("Using IoTHub Module. Client ID is {}".format(client_id))
    else:
        logger.debug("Using IoTHub Device. Client ID is {}".format(client_id))

    if client_config.gateway_hostname:
        logger.debug("Gateway Hostname is present. Using Gateway Hostname as Hostname")
        hostname = client_config.gateway_hostname
    else:
        logger.debug("Gateway Hostname not present. Using Hostname as Hostname")
        hostname = client_config.hostname

    if client_config.websockets:
        logger.debug("Using MQTT over websockets")
        transport = "websockets"
        port = 443
        websockets_path = "/$iothub/websocket"
    else:
        logger.debug("Using MQTT over TCP")
        transport = "tcp"
        port = 8883
        websockets_path = None

    client = mqtt.MQTTClient(
        client_id=client_id,
        hostname=hostname,
        port=port,
        transport=transport,
        keep_alive=client_config.keep_alive,
        auto_reconnect=client_config.auto_reconnect,
        reconnect_interval=DEFAULT_RECONNECT_INTERVAL,
        ssl_context=client_config.ssl_context,
        websockets_path=websockets_path,
        proxy_options=client_config.proxy_options,
    )

    # Add topic filters for receive
    # IoTHub Receives
    c2d_msg_topic = mqtt_topic.get_c2d_topic_for_subscribe(client_config.device_id)
    client.add_incoming_message_filter(c2d_msg_topic)
    if client_config.module_id:
        input_msg_topic = mqtt_topic.get_input_topic_for_subscribe(
            client_config.device_id, client_config.module_id
        )
        client.add_incoming_message_filter(input_msg_topic)
    method_request_topic = mqtt_topic.get_method_topic_for_subscribe()
    client.add_incoming_message_filter(method_request_topic)
    twin_patch_topic = mqtt_topic.get_twin_patch_topic_for_subscribe()
    client.add_incoming_message_filter(twin_patch_topic)
    # Operation Responses
    twin_response_topic = mqtt_topic.get_twin_response_topic_for_subscribe()
    client.add_incoming_message_filter(twin_response_topic)

    return client


def _format_username(hostname: str, client_id: str, product_info: str) -> str:
    query_param_seq = []

    # Apply query parameters (i.e. key1=value1&key2=value2...&keyN=valueN format)
    if product_info.startswith(constant.DIGITAL_TWIN_PREFIX):  # Digital Twin Stuff
        query_param_seq.append(("api-version", constant.IOTHUB_API_VERSION))
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


# TODO: error handling on extraction, decoding, json loading
# TODO; don't forget json loading can fail if improper decoding occurs
def _create_c2d_message_generator(
    device_id: str, mqtt_client: mqtt.MQTTClient
) -> AsyncGenerator[Message, None]:
    c2d_msg_topic = mqtt_topic.get_c2d_topic_for_subscribe(device_id)
    mqtt_msg_generator = mqtt_client.get_incoming_message_generator(c2d_msg_topic)

    async def c2d_message_generator(
        incoming_mqtt_messages: AsyncGenerator[mqtt.MQTTMessage, None]
    ) -> AsyncGenerator[Message, None]:
        async for mqtt_message in incoming_mqtt_messages:
            c2d_message = _create_hub_message_from_mqtt_message(mqtt_message)
            yield c2d_message

    return c2d_message_generator(mqtt_msg_generator)


def _create_input_message_generator(
    device_id: str, module_id: Optional[str], mqtt_client: mqtt.MQTTClient
) -> Optional[AsyncGenerator[Message, None]]:
    # TODO: this logic probably ought to be elsewhere?
    if module_id is None:
        # Can't create a input message generator without a module id
        return None

    input_msg_topic = mqtt_topic.get_input_topic_for_subscribe(device_id, module_id)
    mqtt_msg_generator = mqtt_client.get_incoming_message_generator(input_msg_topic)

    async def input_message_generator(
        incoming_mqtt_messages: AsyncGenerator[mqtt.MQTTMessage, None]
    ) -> AsyncGenerator[Message, None]:
        async for mqtt_message in incoming_mqtt_messages:
            input_message = _create_hub_message_from_mqtt_message(mqtt_message)
            yield input_message

    return input_message_generator(mqtt_msg_generator)


def _create_method_request_generator(
    mqtt_client: mqtt.MQTTClient,
) -> AsyncGenerator[MethodRequest, None]:
    method_request_topic = mqtt_topic.get_method_topic_for_subscribe()
    mqtt_msg_generator = mqtt_client.get_incoming_message_generator(method_request_topic)

    async def method_request_generator(
        incoming_mqtt_messages: AsyncGenerator[mqtt.MQTTMessage, None]
    ) -> AsyncGenerator[MethodRequest, None]:
        async for mqtt_message in incoming_mqtt_messages:
            # TODO: should request_id be an int in this context?
            request_id = mqtt_topic.extract_request_id_from_method_request_topic(mqtt_message.topic)
            method_name = mqtt_topic.extract_name_from_method_request_topic(mqtt_message.topic)
            payload = json.loads(mqtt_message.payload.decode("utf-8"))
            method_request = MethodRequest(request_id=request_id, name=method_name, payload=payload)
            yield method_request

    return method_request_generator(mqtt_msg_generator)


def _create_twin_patch_generator(mqtt_client: mqtt.MQTTClient) -> AsyncGenerator[TwinPatch, None]:
    twin_patch_topic = mqtt_topic.get_twin_patch_topic_for_subscribe()
    mqtt_msg_generator = mqtt_client.get_incoming_message_generator(twin_patch_topic)

    async def twin_patch_generator(
        incoming_mqtt_messages: AsyncGenerator[mqtt.MQTTMessage, None]
    ) -> AsyncGenerator[TwinPatch, None]:
        async for mqtt_message in incoming_mqtt_messages:
            patch = json.loads(mqtt_message.payload.decode("utf-8"))
            yield patch

    return twin_patch_generator(mqtt_msg_generator)


def _create_hub_message_from_mqtt_message(mqtt_message: mqtt.MQTTMessage) -> Message:
    """Given an MQTTMessage, create and return a Message"""
    properties = mqtt_topic.extract_properties_from_message_topic(mqtt_message.topic)
    # Decode the payload based on content encoding in the topic. If not present, use utf-8
    content_encoding = properties.get("$.ce", "utf-8")
    content_type = properties.get("$.ct", "text/plain")
    payload = mqtt_message.payload.decode(content_encoding)
    if content_type == "application/json":
        payload = json.loads(payload)
    return Message.create_from_properties_dict(payload=payload, properties=properties)
