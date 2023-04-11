# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import json
import logging
import urllib.parse
import uuid
from typing import Optional, TypeVar
from .custom_typing import (
    RegistrationResult,
    RegistrationState,
    RegistrationPayload,
    DeviceRegistrationRequest,
)
from .provisioning_exceptions import ProvisioningServiceError
from .mqtt_client import (  # noqa: F401 (Importing directly to re-export)
    MQTTError,
    MQTTConnectionFailedError,
)
from . import config, constant, user_agent
from . import request_response as rr
from . import mqtt_client as mqtt
from . import mqtt_topic_provisioning as mqtt_topic

# TODO: update docstrings with correct class paths once repo structured better

logger = logging.getLogger(__name__)

DEFAULT_POLLING_INTERVAL: int = 2
DEFAULT_RECONNECT_INTERVAL: int = 10
DEFAULT_TIMEOUT_INTERVAL: int = 30

_T = TypeVar("_T")


class ProvisioningMQTTClient:
    def __init__(
        self,
        client_config: config.ProvisioningClientConfig,
    ) -> None:
        """Instantiate the client

        :param client_config: The config object for the client
        :type client_config: :class:`ProvisioningClientConfig`
        """
        # Identity
        self._registration_id = client_config.registration_id
        self._username = _format_username(
            id_scope=client_config.id_scope,
            registration_id=self._registration_id,
            # product_info=client_config.product_info,
        )

        # SAS (Optional)
        self._sastoken_provider = client_config.sastoken_provider

        # MQTT Configuration
        self._mqtt_client = _create_mqtt_client(self._registration_id, client_config)

        # Add filters for receive topics delivering data used internally
        register_response_topic = mqtt_topic.get_response_topic_for_subscribe()
        self._mqtt_client.add_incoming_message_filter(register_response_topic)
        # NOTE: credentials are set upon `.start()`

        # Internal request/response infrastructure
        self._request_ledger = rr.RequestLedger()
        self._register_responses_enabled = False

        # Background Tasks (Will be set upon `.start()`)
        self._process_dps_responses_task: Optional[asyncio.Task[None]] = None

    async def _enable_dps_responses(self) -> None:
        """Enable receiving of registration or polling responses from device provisioning service"""
        logger.debug("Enabling receive of responses from device provisioning service...")
        topic = mqtt_topic.get_response_topic_for_subscribe()
        await self._mqtt_client.subscribe(topic)
        self._register_responses_enabled = True
        logger.debug("Device provisioning service responses receive enabled")

    async def _process_dps_responses(self) -> None:
        """Run indefinitely, matching responses from DPS with request ID"""
        logger.debug("Starting the '_process_dps_responses' background task")
        dps_response_topic = mqtt_topic.get_response_topic_for_subscribe()
        dps_responses = self._mqtt_client.get_incoming_message_generator(dps_response_topic)

        async for mqtt_message in dps_responses:
            try:
                extracted_properties = mqtt_topic.extract_properties_from_response_topic(
                    mqtt_message.topic
                )
                request_id = extracted_properties["$rid"]
                status_code = int(
                    mqtt_topic.extract_status_code_from_response_topic(mqtt_message.topic)
                )
                # NOTE: We don't know what the content of the body is until we match the rid, so don't
                # do more than just decode it here - leave interpreting the string to the coroutine
                # waiting for the response.
                response_body = mqtt_message.payload.decode("utf-8")
                logger.debug("Device provisioning response received (rid: {})".format(request_id))
                logger.debug("Response body is {}".format(response_body))
                response = rr.Response(
                    request_id=request_id,
                    status=status_code,
                    body=response_body,
                    properties=extracted_properties,
                )
            except Exception as e:
                logger.error(
                    "Unexpected error ({}) while translating device provisioning response. Dropping.".format(
                        e
                    )
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
                    "Device provisioning response (rid: {}) does not match any request".format(
                        request_id
                    )
                )
            except Exception as e:
                logger.error(
                    "Unexpected error ({}) while matching Device provisioning response (rid: {}). Dropping response".format(
                        e, request_id
                    )
                )

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
        if not self._process_dps_responses_task:
            self._process_dps_responses_task = asyncio.create_task(self._process_dps_responses())

    async def stop(self) -> None:
        """Stop the client.

        - Must be invoked when done with the client for graceful exit.
        - If already stopped, will not do anything.
        - Cannot be cancelled - if you try, the client will still fully shut down as much as
            possible, although CancelledError will still be raised.
        """
        cancelled_tasks = []
        logger.debug("Stopping ProvisioningMQTTClient...")

        if self._process_dps_responses_task:
            logger.debug("Cancelling '_process_dps_responses' background task")
            self._process_dps_responses_task.cancel()
            cancelled_tasks.append(self._process_dps_responses_task)
            self._process_dps_responses_task = None

        results = await asyncio.gather(
            *cancelled_tasks, asyncio.shield(self.disconnect()), return_exceptions=True
        )
        for result in results:
            # NOTE: Need to specifically exclude asyncio.CancelledError because it is not a
            # BaseException in Python 3.7
            if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                raise result

    async def connect(self) -> None:
        """Connect to Device Provisioning Service

        :raises: MQTTConnectionFailedError if there is a failure connecting
        """
        # Connect
        logger.debug("Connecting to Device Provisioning Service...")
        await self._mqtt_client.connect()
        logger.debug("Connect succeeded")

    async def disconnect(self) -> None:
        """Disconnect from Device Provisioning Service"""
        logger.debug("Disconnecting from Device Provisioning Service...")
        await self._mqtt_client.disconnect()
        logger.debug("Disconnect succeeded")

    async def wait_for_disconnect(self) -> Optional[MQTTError]:
        """Block until disconnection and return the cause, if any

        :returns: An MQTTError if the connection was dropped, or None if the
            connection was intentionally ended
        :rtype: MQTTError or None
        """
        async with self._mqtt_client.disconnected_cond:
            await self._mqtt_client.disconnected_cond.wait_for(lambda: not self.connected)
            return self._mqtt_client.previous_disconnection_cause()

    async def send_register(
        self, payload: Optional[RegistrationPayload] = None
    ) -> RegistrationResult:
        if not self._register_responses_enabled:
            await self._enable_dps_responses()
        register_request_id = str(uuid.uuid4())
        register_topic = mqtt_topic.get_register_topic_for_publish(request_id=register_request_id)
        device_registration_request: DeviceRegistrationRequest = {
            "registrationId": self._registration_id,
            "payload": payload,
        }
        publish_payload = json.dumps(
            device_registration_request, default=lambda o: o.__dict__, sort_keys=True
        )
        interval = 0  # Initially set to no sleep
        register_response = None

        while True:
            await asyncio.sleep(interval)
            # Create request with existing request id
            # It is either a new request or a re-triable request
            request = await self._request_ledger.create_request(register_request_id)
            try:
                try:
                    # Send request to DPS
                    logger.debug(
                        "Sending register request to Device Provisioning Service... (rid: {})".format(
                            request.request_id
                        )
                    )
                    logger.debug(
                        "The payload to be published to Device Provisioning Service is {}".format(
                            publish_payload
                        )
                    )
                    await self._mqtt_client.publish(register_topic, publish_payload)
                except asyncio.CancelledError:
                    logger.warning(
                        "Attempt to send register request to Device Provisioning Service was cancelled while in flight."
                        "It may or may not have been received (rid: {})".format(request.request_id)
                    )
                    raise
                except Exception:
                    logger.error(
                        "Sending register request to Device Provisioning Service failed (rid: {})".format(
                            request.request_id
                        )
                    )
                    raise

                # Wait for a response from DPS
                try:
                    logger.debug(
                        "Waiting to receive response for register request from Device Provisioning Service...(rid: {})".format(
                            request.request_id
                        )
                    )
                    # Include a timeout for receipt of response
                    register_response = await asyncio.wait_for(
                        request.get_response(), DEFAULT_TIMEOUT_INTERVAL
                    )
                except asyncio.TimeoutError as te:
                    logger.debug(
                        "Attempt to send register request to Device Provisioning Service "
                        "took more time than allowable limit while waiting for a response. If the response arrives, "
                        "it will be discarded (rid: {})".format(request.request_id)
                    )
                    raise ProvisioningServiceError(
                        "Device Provisioning Service timed out while waiting for response to the "
                        "register request...(rid: {}).".format(request.request_id)
                    ) from te
                except asyncio.CancelledError:
                    logger.debug(
                        "Attempt to send register request to Device Provisioning Service "
                        "was cancelled while waiting for a response. If the response arrives, "
                        "it will be discarded (rid: {})".format(request.request_id)
                    )
                    raise
            finally:
                # If an exception caused exit before a pending request could be matched with a response
                # then manually delete to prevent leaks.
                if request.request_id in self._request_ledger:
                    await self._request_ledger.delete_request(request.request_id)
            if register_response:
                if 300 <= register_response.status < 429:
                    raise ProvisioningServiceError(
                        "Device Provisioning Service responded to the register request with a failed status - {}. The detailed error is {}.".format(
                            register_response.status, register_response.body
                        )
                    )
                elif register_response.status >= 429:
                    # Process same request for retry again
                    if register_response.properties is not None:
                        retry_after = int(register_response.properties.get("retry-after", "0"))
                    logger.debug(
                        "Retrying register request after {} secs to Device Provisioning Service...(rid: {})".format(
                            retry_after, request.request_id
                        )
                    )
                    interval = retry_after
                else:  # happens when response.status 200-300
                    logger.debug(
                        "Received response for register request from Device Provisioning Service "
                        "(rid: {})".format(request.request_id)
                    )
                    decoded_dps_response = json.loads(register_response.body)
                    operation_id = decoded_dps_response.get("operationId", None)
                    registration_status = decoded_dps_response.get("status", None)
                    if registration_status == "assigning":
                        # Transition into polling
                        logger.debug(
                            "Transitioning to polling request to Device Provisioning Service..."
                        )
                        return await self.send_polling(operation_id)
                    elif (
                        registration_status == "assigned" or registration_status == "failed"
                    ):  # breaking from while
                        decoded_dps_state = decoded_dps_response.get("registrationState", None)
                        registration_state: RegistrationState = {
                            "deviceId": decoded_dps_state.get("deviceId", None),
                            "assignedHub": decoded_dps_state.get("assignedHub", None),
                            "subStatus": decoded_dps_state.get("subStatus", None),
                            "createdDateTimeUtc": decoded_dps_state.get("createdDateTimeUtc", None),
                            "lastUpdatedDateTimeUtc": decoded_dps_state.get(
                                "lastUpdatedDateTimeUtc", None
                            ),
                            "etag": decoded_dps_state.get("etag", None),
                            "payload": decoded_dps_state.get("payload", None),
                        }
                        registration_result: RegistrationResult = {
                            "operationId": operation_id,
                            "status": registration_status,
                            "registrationState": registration_state,
                        }
                        return registration_result
                    else:
                        raise ProvisioningServiceError(
                            "Device Provisioning Service responded to the register request with an invalid "
                            "registration status {} failed status - {}. The entire error response is {}".format(
                                registration_status,
                                register_response.status,
                                json.loads(register_response.body),
                            )
                        )

    async def send_polling(self, operation_id: str) -> RegistrationResult:
        polling_request_id = str(uuid.uuid4())
        query_topic = mqtt_topic.get_status_query_topic_for_publish(
            request_id=polling_request_id, operation_id=operation_id
        )
        interval = DEFAULT_POLLING_INTERVAL
        query_response = None
        while True:
            await asyncio.sleep(interval)
            # Create request with existing request id
            # It is either a new request or a re-triable request
            request = await self._request_ledger.create_request(polling_request_id)
            try:
                # Send the request to DPS, this can be a register or a query request
                try:
                    logger.debug(
                        "Sending polling request to Device Provisioning Service... (rid: {})".format(
                            request.request_id
                        )
                    )
                    await self._mqtt_client.publish(query_topic, " ")
                except asyncio.CancelledError:
                    logger.warning(
                        "Attempt to send polling request to Device Provisioning Service was cancelled while in flight. "
                        "It may or may not have been received (rid: {})".format(request.request_id)
                    )
                    raise
                except Exception:
                    logger.error(
                        "Sending polling request to Device Provisioning Service failed (rid: {})".format(
                            request.request_id
                        )
                    )
                    raise

                # Wait for a response from IoTHub
                try:
                    logger.debug(
                        "Waiting to receive a response for polling request from Device Provisioning Service... (rid: {})".format(
                            request.request_id
                        )
                    )
                    # response = await request.get_response()
                    query_response = await asyncio.wait_for(
                        request.get_response(), DEFAULT_TIMEOUT_INTERVAL
                    )
                except asyncio.TimeoutError as te:
                    logger.debug(
                        "Attempt to send polling request to Device Provisioning Service "
                        "took more time than allowable limit while waiting for a response. If the response arrives, "
                        "it will be discarded (rid: {})".format(request.request_id)
                    )
                    raise ProvisioningServiceError(
                        "Device Provisioning Service timed out while waiting for response to the "
                        "polling request with (rid: {})".format(request.request_id)
                    ) from te
                except asyncio.CancelledError:
                    logger.debug(
                        "Attempt to send polling request to Device Provisioning Service "
                        "was cancelled while waiting for a response. If the response arrives, "
                        "it will be discarded (rid: {})".format(request.request_id)
                    )
                    raise
            finally:
                # If an exception caused exit before a pending request could be matched with a response
                # then manually delete to prevent leaks.
                if request.request_id in self._request_ledger:
                    await self._request_ledger.delete_request(request.request_id)
            if query_response:
                if 300 <= query_response.status < 429:
                    # breaking from while
                    raise ProvisioningServiceError(
                        "Device Provisioning Service responded to the polling request with a failed status - {}. The detailed error is {}. ".format(
                            query_response.status, query_response.body
                        )
                    )
                elif query_response.status >= 429:
                    # Process same request for retry again
                    if query_response.properties is not None:
                        retry_after = int(query_response.properties.get("retry-after", "0"))
                    logger.debug(
                        "Retrying polling request after {} secs to Device Provisioning Service...(rid: {})".format(
                            retry_after, request.request_id
                        )
                    )
                    interval = retry_after
                else:  # happens when response.status < 300
                    logger.debug(
                        "Received response for polling request from Device Provisioning Service "
                        "(rid: {})".format(request.request_id)
                    )
                    decoded_dps_response = json.loads(query_response.body)
                    operation_id = decoded_dps_response.get("operationId", None)
                    registration_status = decoded_dps_response.get("status", None)
                    if registration_status == "assigning":
                        if query_response.properties is not None:
                            interval = int(
                                query_response.properties.get(
                                    "retry-after", DEFAULT_POLLING_INTERVAL
                                )
                            )
                        logger.debug(
                            "Retrying polling request after {} secs to Device Provisioning Service...(rid: {})".format(
                                interval, request.request_id
                            )
                        )
                    elif (
                        registration_status == "assigned" or registration_status == "failed"
                    ):  # breaking from while
                        decoded_dps_state = decoded_dps_response.get("registrationState", None)
                        registration_state: RegistrationState = {
                            "deviceId": decoded_dps_state.get("deviceId", None),
                            "assignedHub": decoded_dps_state.get("assignedHub", None),
                            "subStatus": decoded_dps_state.get("subStatus", None),
                            "createdDateTimeUtc": decoded_dps_state.get("createdDateTimeUtc", None),
                            "lastUpdatedDateTimeUtc": decoded_dps_state.get(
                                "lastUpdatedDateTimeUtc", None
                            ),
                            "etag": decoded_dps_state.get("etag", None),
                            "payload": decoded_dps_state.get("payload", None),
                        }
                        registration_result: RegistrationResult = {
                            "operationId": operation_id,
                            "status": registration_status,
                            "registrationState": registration_state,
                        }
                        return registration_result
                    else:
                        raise ProvisioningServiceError(
                            "Device Provisioning Service responded to the polling request with an invalid "
                            "registration status {} failed status - {}. The entire error response is {}".format(
                                registration_status,
                                query_response.status,
                                json.loads(query_response.body),
                            )
                        )

    @property
    def connected(self) -> bool:
        """Boolean indicating connection status"""
        return self._mqtt_client.is_connected()


def _create_mqtt_client(
    client_id: str, client_config: config.ProvisioningClientConfig
) -> mqtt.MQTTClient:
    logger.debug("Creating MQTTClient")

    logger.debug("Using {} as hostname".format(client_config.hostname))
    logger.debug("Using IoTHub Device Registration Id. Client ID is {}".format(client_id))

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


def _format_username(id_scope: str, registration_id: str) -> str:
    query_param_seq = []

    # Apply query parameters (i.e. key1=value1&key2=value2...&keyN=valueN format)

    query_param_seq.append(("api-version", constant.PROVISIONING_API_VERSION))
    query_param_seq.append(("ClientVersion", user_agent.get_provisioning_user_agent()))

    username = "{id_scope}/registrations/{registration_id}/{query_params}".format(
        id_scope=id_scope,
        registration_id=registration_id,
        query_params=urllib.parse.urlencode(query_param_seq, quote_via=urllib.parse.quote),
    )
    return username