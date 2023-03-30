# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import json
import logging
import urllib.parse
from typing import Callable, Optional, AsyncGenerator, TypeVar, Any
from .custom_typing import TwinPatch, Twin
from .iot_exceptions import IoTHubError, IoTHubClientError
from .mqtt_client import (  # noqa: F401 (Importing directly to re-export)
    MQTTError,
    MQTTConnectionFailedError,
)
from . import config, constant, user_agent, models
from . import request_response as rr
from . import mqtt_client as mqtt
from . import mqtt_topic_iothub as mqtt_topic

# TODO: update docstrings with correct class paths once repo structured better

logger = logging.getLogger(__name__)

DEFAULT_RECONNECT_INTERVAL: int = 10

_T = TypeVar("_T")


class IoTHubMQTTClient:
    def __init__(
        self,
        client_config: config.IoTHubClientConfig,
    ) -> None:
        """Instantiate the client

        :param client_config: The config object for the client
        :type client_config: :class:`IoTHubClientConfig`
        """
        # Identity
        self._device_id = client_config.device_id
        self._module_id = client_config.module_id
        self._client_id = _format_client_id(self._device_id, self._module_id)
        self._username = _format_username(
            hostname=client_config.hostname,
            client_id=self._client_id,
            product_info=client_config.product_info,
        )

        # SAS (Optional)
        self._sastoken_provider = client_config.sastoken_provider

        # MQTT Configuration
        self._mqtt_client = _create_mqtt_client(self._client_id, client_config)
        # NOTE: credentials are set upon `.start()`

        # Add filters for receive topics delivering data used internally
        twin_response_topic = mqtt_topic.get_twin_response_topic_for_subscribe()
        self._mqtt_client.add_incoming_message_filter(twin_response_topic)

        # Create generators for receive topics delivering data used externally
        # (Implicitly adding filters for these topics as well)
        self._incoming_input_messages: Optional[AsyncGenerator[models.Message, None]] = None
        self._incoming_c2d_messages: Optional[AsyncGenerator[models.Message, None]] = None
        self._incoming_direct_method_requests: AsyncGenerator[models.DirectMethodRequest, None]
        self._incoming_twin_patches: AsyncGenerator[TwinPatch, None]
        # TODO: what is the proper type for this?
        self._incoming_twin_responses: Optional[AsyncGenerator[Any, None]] = None
        if self._module_id:
            self._incoming_input_messages = self._create_incoming_data_generator(
                topic=mqtt_topic.get_input_topic_for_subscribe(self._device_id, self._module_id),
                transform_fn=_create_iothub_message_from_mqtt_message,
            )
        else:
            self._incoming_c2d_messages = self._create_incoming_data_generator(
                topic=mqtt_topic.get_c2d_topic_for_subscribe(self._device_id),
                transform_fn=_create_iothub_message_from_mqtt_message,
            )
        self._incoming_direct_method_requests = self._create_incoming_data_generator(
            topic=mqtt_topic.get_direct_method_request_topic_for_subscribe(),
            transform_fn=_create_direct_method_request_from_mqtt_message,
        )
        self._incoming_twin_patches = self._create_incoming_data_generator(
            topic=mqtt_topic.get_twin_patch_topic_for_subscribe(),
            transform_fn=_create_twin_patch_from_mqtt_message,
        )

        # Internal request/response infrastructure
        self._request_ledger = rr.RequestLedger()
        self._twin_responses_enabled = False

        # Background Tasks (Will be set upon `.start()`)
        self._process_twin_responses_bg_task: Optional[asyncio.Task[None]] = None
        self._keep_credentials_fresh_bg_task: Optional[asyncio.Task[None]] = None

    def _create_incoming_data_generator(
        self, topic: str, transform_fn: Callable[[mqtt.MQTTMessage], _T]
    ) -> AsyncGenerator[_T, None]:
        """Return a generator for incoming MQTT data on a given topic, yielding a transformation
        of that data via the given transform function"""
        self._mqtt_client.add_incoming_message_filter(topic)
        incoming_mqtt_messages = self._mqtt_client.get_incoming_message_generator(topic)

        async def generator() -> AsyncGenerator[_T, None]:
            async for mqtt_message in incoming_mqtt_messages:
                try:
                    yield transform_fn(mqtt_message)
                    mqtt_message = None
                except asyncio.CancelledError:
                    # NOTE: In Python 3.7 this isn't a BaseException, so we must catch and re-raise
                    # NOTE: This shouldn't ever happen since none of the transform_fns should be
                    # doing async invocations, but can't hurt to have this for future-proofing.
                    raise
                except Exception as e:
                    # TODO: background exception logging improvements (e.g. stacktrace)
                    logger.error("Failure transforming MQTTMessage: {}".format(e))
                    logger.warning("Dropping MQTTMessage that could not be transformed")

        return generator()

    async def _enable_twin_responses(self) -> None:
        """Enable receiving of twin responses (for twin requests, or twin patches) from IoTHub"""
        logger.debug("Enabling receive of twin responses...")
        topic = mqtt_topic.get_twin_response_topic_for_subscribe()
        await self._mqtt_client.subscribe(topic)
        self._twin_responses_enabled = True
        logger.debug("Twin responses receive enabled")

    async def _process_twin_responses(self) -> None:
        """Run indefinitely, matching twin responses with request ID"""
        logger.debug("Starting the 'process_twin_responses' background task")
        twin_response_topic = mqtt_topic.get_twin_response_topic_for_subscribe()
        twin_responses = self._mqtt_client.get_incoming_message_generator(twin_response_topic)
        self.incoming_twin_response_generator = twin_responses

        async for mqtt_message in twin_responses:
            try:
                request_id = mqtt_topic.extract_request_id_from_twin_response_topic(
                    mqtt_message.topic
                )
                status_code = int(
                    mqtt_topic.extract_status_code_from_twin_response_topic(mqtt_message.topic)
                )
                # NOTE: We don't know what the content of the body is until we match the rid, so don't
                # do more than just decode it here - leave interpreting the string to the coroutine
                # waiting for the response.
                response_body = mqtt_message.payload.decode("utf-8")
                logger.debug("Twin response received (rid: {})".format(request_id))
                response = rr.Response(
                    request_id=request_id, status=status_code, body=response_body
                )
            except Exception as e:
                logger.error(
                    "Unexpected error ({}) while translating Twin response. Dropping.".format(e)
                )
                # NOTE: In this situation the operation waiting for the response that we failed to
                # receive will hang. This isn't the end of the world, since it can be cancelled,
                # but if we really wanted to smooth this out, we could cancel the pending operation
                # based on the request id (assuming getting the request id is not what failed).
                # But for now, that's probably overkill, especially since this path ideally should
                # never happen, because we would like to assume IoTHub isn't sending malformed data
                continue
            try:
                await self._request_ledger.match_response(response)
            except asyncio.CancelledError:
                # NOTE: In Python 3.7 this isn't a BaseException, so we must catch and re-raise
                raise
            except KeyError:
                # NOTE: This should only happen in edge cases involving cancellation of
                # in-flight operations
                logger.warning(
                    "Twin response (rid: {}) does not match any request".format(request_id)
                )
            except Exception as e:
                logger.error(
                    "Unexpected error ({}) while matching Twin response (rid: {}). Dropping response".format(
                        e, request_id
                    )
                )

    async def _keep_credentials_fresh(self) -> None:
        """Run indefinitely, updating MQTT credentials when new SAS Token is available"""
        logger.debug("Starting the 'keep_credentials_fresh' background task")
        while True:
            if self._sastoken_provider:
                try:
                    logger.debug("Waiting for new SAS Token to become available")
                    new_sastoken = await self._sastoken_provider.wait_for_new_sastoken()
                    logger.debug("New SAS Token available, updating MQTTClient credentials")
                    self._mqtt_client.set_credentials(self._username, str(new_sastoken))
                    # TODO: should we reconnect here? Or just wait for drop?
                except asyncio.CancelledError:
                    # NOTE: In Python 3.7 this isn't a BaseException, so we must catch and re-raise
                    raise
                except Exception as e:
                    logger.error(
                        "Unexpected exception ({}) while keeping credentials fresh. Ignoring".format(
                            e
                        )
                    )
                    continue
            else:
                # NOTE: This should never execute, it's mostly just here to keep the
                # type checker happy
                logger.error("No SasTokenProvider. Cannot update credentials")
                break

    async def start(self) -> None:
        """Start up the client.

        - Must be invoked before any other methods.
        - If already started, will not (meaningfully) do anything.
        """
        # Set credentials
        if self._sastoken_provider:
            logger.debug("Using SASToken as password")
            password = str(self._sastoken_provider.get_current_sastoken())
        else:
            logger.debug("No password used")
            password = None
        self._mqtt_client.set_credentials(self._username, password)
        # Start background tasks
        if self._sastoken_provider and not self._keep_credentials_fresh_bg_task:
            self._keep_credentials_fresh_bg_task = asyncio.create_task(
                self._keep_credentials_fresh()
            )
        if not self._process_twin_responses_bg_task:
            self._process_twin_responses_bg_task = asyncio.create_task(
                self._process_twin_responses()
            )

    async def stop(self) -> None:
        """Stop the client.

        - Must be invoked when done with the client for graceful exit.
        - If already stopped, will not do anything.
        - Cannot be cancelled - if you try, the client will still fully shut down as much as
            possible, although CancelledError will still be raised.
        """
        cancelled_tasks = []
        logger.debug("Stopping IoTHubMQTTClient...")

        if self._process_twin_responses_bg_task:
            logger.debug("Cancelling 'process_twin_responses' background task")
            self._process_twin_responses_bg_task.cancel()
            cancelled_tasks.append(self._process_twin_responses_bg_task)
            self._process_twin_responses_bg_task = None

        if self._keep_credentials_fresh_bg_task:
            logger.debug("Cancelling 'keep_credentials_fresh' background task")
            self._keep_credentials_fresh_bg_task.cancel()
            cancelled_tasks.append(self._keep_credentials_fresh_bg_task)
            self._keep_credentials_fresh_bg_task = None

        # shut down our async generators. If we dont do this, generators won't correctly
        # stop when we leave the session.
        # https://stackoverflow.com/a/60233813
        # https://stackoverflow.com/questions/60226557/how-to-forcefully-close-an-async-generator
        for generator in [
            self._incoming_input_messages,
            self._incoming_c2d_messages,
            self._incoming_direct_method_requests,
            self._incoming_twin_patches,
            self._incoming_twin_responses,
        ]:
            if generator:
                coro: Any = generator.__anext__()
                task: asyncio.Task = asyncio.create_task(coro)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                await generator.aclose()

        results = await asyncio.gather(
            *cancelled_tasks, asyncio.shield(self.disconnect()), return_exceptions=True
        )
        for result in results:
            # NOTE: Need to specifically exclude asyncio.CancelledError because it is not a
            # BaseException in Python 3.7
            if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                raise result

    async def connect(self) -> None:
        """Connect to IoTHub

        :raises: MQTTConnectionFailedError if there is a failure connecting
        """
        # Connect
        logger.debug("Connecting to IoTHub...")
        await self._mqtt_client.connect()
        logger.debug("Connect succeeded")

    async def disconnect(self) -> None:
        """Disconnect from IoTHub"""
        logger.debug("Disconnecting from IoTHub...")
        await self._mqtt_client.disconnect()
        logger.debug("Disconnect succeeded")

    async def send_message(self, message: models.Message) -> None:
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

    async def send_direct_method_response(
        self, method_response: models.DirectMethodResponse
    ) -> None:
        """Send a direct method response to IoTHub.

        :param method_response: The DirectMethodResponse to be sent
        :type method_response: :class:`models.DirectMethodResponse`

        :raises: MQTTError if there is an error sending the DirectMethodResponse
        :raises: ValueError if the size of the DirectMethodResponse payload is too large
        """
        topic = mqtt_topic.get_direct_method_response_topic_for_publish(
            method_response.request_id, method_response.status
        )
        payload = json.dumps(method_response.payload)
        logger.debug(
            "Sending direct method response to IoTHub... (rid: {})".format(
                method_response.request_id
            )
        )
        await self._mqtt_client.publish(topic, payload)
        logger.debug(
            "Sending direct method response succeeded (rid: {})".format(method_response.request_id)
        )

    async def send_twin_patch(self, patch: TwinPatch) -> None:
        """Send a twin patch to IoTHub

        :param patch: The JSON patch to send
        :type patch: dict, list, tuple, str, int, float, bool, None

        :raises: IoTHubError if an error response is received from IoT Hub
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
            if response.status >= 400:
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

        :raises: IoTHubError if an error response is received from IoT Hub
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
        if response.status >= 400:
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

    async def enable_direct_method_request_receive(self) -> None:
        """Enable the ability to receive direct method requests

        :raises: MQTTError if there is an error enabling direct method request receive
        :raises: CancelledError if enabling direct method request receive is cancelled by
            network failure
        """
        logger.debug("Enabling receive for direct method requests...")
        topic = mqtt_topic.get_direct_method_request_topic_for_subscribe()
        await self._mqtt_client.subscribe(topic)
        logger.debug("Direct method request receive enabled")

    async def disable_direct_method_request_receive(self) -> None:
        """Disable the ability to receive direct method requests

        :raises: MQTTError if there is an error disabling direct method request receive
        :raises: CancelledError if disabling direct method request receive is cancelled by
            network failure
        """
        logger.debug("Disabling receive for direct method requests...")
        topic = mqtt_topic.get_direct_method_request_topic_for_subscribe()
        await self._mqtt_client.unsubscribe(topic)
        logger.debug("Direct method request receive disabled")

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

    @property
    def incoming_c2d_messages(self) -> AsyncGenerator[models.Message, None]:
        """Generator that yields incoming C2D Messages"""
        if not self._incoming_c2d_messages:
            raise IoTHubClientError("C2D Messages not available for Module")
        else:
            return self._incoming_c2d_messages

    @property
    def incoming_input_messages(self) -> AsyncGenerator[models.Message, None]:
        """Generator that yields incoming input Messages"""
        if not self._incoming_input_messages:
            raise IoTHubClientError("Input Messages not available for Device")
        else:
            return self._incoming_input_messages

    @property
    def incoming_direct_method_requests(
        self,
    ) -> AsyncGenerator[models.DirectMethodRequest, None]:
        """Generator that yields incoming DirectMethodRequests"""
        return self._incoming_direct_method_requests

    @property
    def incoming_twin_patches(self) -> AsyncGenerator[TwinPatch, None]:
        """Generator that yields incoming TwinPatches"""
        return self._incoming_twin_patches


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

    logger.debug("Using {} as hostname".format(client_config.hostname))

    if client_config.module_id:
        logger.debug("Using IoTHub Module. Client ID is {}".format(client_id))
    else:
        logger.debug("Using IoTHub Device. Client ID is {}".format(client_id))

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
        hostname=client_config.hostname,
        port=port,
        transport=transport,
        keep_alive=client_config.keep_alive,
        auto_reconnect=client_config.auto_reconnect,
        reconnect_interval=DEFAULT_RECONNECT_INTERVAL,
        ssl_context=client_config.ssl_context,
        websockets_path=websockets_path,
        proxy_options=client_config.proxy_options,
    )

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


def _create_iothub_message_from_mqtt_message(mqtt_message: mqtt.MQTTMessage) -> models.Message:
    """Given an MQTTMessage, create and return a Message"""
    properties = mqtt_topic.extract_properties_from_message_topic(mqtt_message.topic)
    # Decode the payload based on content encoding in the topic. If not present, use utf-8
    content_encoding = properties.get("$.ce", "utf-8")
    content_type = properties.get("$.ct", "text/plain")
    payload = mqtt_message.payload.decode(content_encoding)
    if content_type == "application/json":
        payload = json.loads(payload)
    return models.Message.create_from_properties_dict(payload=payload, properties=properties)


def _create_direct_method_request_from_mqtt_message(
    mqtt_message: mqtt.MQTTMessage,
) -> models.DirectMethodRequest:
    """Given an MQTTMessage, create and return a DirectMethodRequest"""
    request_id = mqtt_topic.extract_request_id_from_direct_method_request_topic(mqtt_message.topic)
    method_name = mqtt_topic.extract_name_from_direct_method_request_topic(mqtt_message.topic)
    payload = json.loads(mqtt_message.payload.decode("utf-8"))
    return models.DirectMethodRequest(request_id=request_id, name=method_name, payload=payload)


def _create_twin_patch_from_mqtt_message(mqtt_message: mqtt.MQTTMessage) -> TwinPatch:
    """Given an MQTTMessage, create and return a TwinPatch"""
    return json.loads(mqtt_message.payload.decode("utf-8"))
