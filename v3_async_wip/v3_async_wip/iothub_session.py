# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import asyncio
import contextlib
import ssl
from typing import Optional, Union, AsyncGenerator, Type, TypeVar, Awaitable
from types import TracebackType

from v3_async_wip import signing_mechanism as sm
from v3_async_wip import connection_string as cs
from v3_async_wip import sastoken as st
from v3_async_wip import config, models, custom_typing
from v3_async_wip import iothub_mqtt_client as mqtt

_T = TypeVar("_T")

# TODO: add tests for sastoken_ttl argument once we settle on a SAS strategy


class IoTHubSession:
    def __init__(
        self,
        *,
        hostname: str,  # iothub_hostname?
        device_id: str,
        module_id: Optional[str] = None,
        ssl_context: Optional[ssl.SSLContext] = None,
        shared_access_key: Optional[str] = None,
        sastoken_fn: Optional[custom_typing.FunctionOrCoroutine] = None,
        sastoken_ttl: int = 3600,
        **kwargs,
    ) -> None:
        """
        :param str device_id: The device identity for the IoT Hub device containing the
            IoT Hub module
        :param str module_id: The module identity for the IoT Hub module
        :param str hostname: Hostname of the IoT Hub or IoT Edge the device should connect to
        :param ssl_context: Custom SSL context to be used when establishing a connection.
            If not provided, a default one will be used
        :type ssl_context: :class:`ssl.SSLContext`
        :param str shared_access_key: A key that can be used to generate SAS Tokens
        :param sastoken_fn: A function or coroutine function that takes no arguments and returns
            a SAS token string when invoked
        :param sastoken_ttl: Time-to-live (in seconds) for SAS tokens generated when using
            'shared_access_key' authentication.
            If using this auth type, a new Session will need to be created once this time expires.
            Default is 3600 seconds (1 hour).

        :keyword int keep_alive: Maximum period in seconds between MQTT communications. If no
            communications are exchanged for this period, a ping exchange will occur.
            Default is 60 seconds
        :keyword str product_info: Arbitrary product information which will be included in the
            User-Agent string
        :keyword proxy_options: Configuration structure for sending traffic through a proxy server
        :type: proxy_options: :class:`ProxyOptions`
        :keyword bool websockets: Set to 'True' to use WebSockets over MQTT. Default is 'False'

        :raises: ValueError if an invalid combination of parameters are provided
        :raises: ValueError if an invalid 'symmetric_key' is provided
        :raises: TypeError if an invalid keyword argument is provided
        """
        # Validate parameters
        _validate_kwargs(**kwargs)
        if shared_access_key and sastoken_fn:
            raise ValueError(
                "Incompatible authentication - cannot provide both 'shared_access_key' and 'sastoken_fn'"
            )
        if not shared_access_key and not sastoken_fn and not ssl_context:
            raise ValueError(
                "Missing authentication - must provide one of 'shared_access_key', 'sastoken_fn' or 'ssl_context'"
            )

        # Set up SAS auth (if using)
        generator: Optional[st.SasTokenGenerator]
        # NOTE: Need to keep a reference to the SasTokenProvider so we can stop it during cleanup
        self._sastoken_provider: Optional[st.SasTokenProvider]
        if shared_access_key:
            uri = _format_sas_uri(hostname=hostname, device_id=device_id, module_id=module_id)
            signing_mechanism = sm.SymmetricKeySigningMechanism(shared_access_key)
            generator = st.InternalSasTokenGenerator(
                signing_mechanism=signing_mechanism, uri=uri, ttl=sastoken_ttl
            )
            self._sastoken_provider = st.SasTokenProvider(generator)
        elif sastoken_fn:
            generator = st.ExternalSasTokenGenerator(sastoken_fn)
            self._sastoken_provider = st.SasTokenProvider(generator)
        else:
            self._sastoken_provider = None

        # Create a default SSLContext if not provided
        if not ssl_context:
            ssl_context = _default_ssl_context()

        # Instantiate the MQTTClient
        client_config = config.IoTHubClientConfig(
            hostname=hostname,
            device_id=device_id,
            module_id=module_id,
            sastoken_provider=self._sastoken_provider,
            ssl_context=ssl_context,
            auto_reconnect=False,  # We do not reconnect in a Session
            **kwargs,
        )
        self._mqtt_client = mqtt.IoTHubMQTTClient(client_config)

        # This task is used to propagate dropped connections through receiver generators
        # It will be set upon context manager entry and cleared upon exit
        # NOTE: If we wanted to design lower levels of the stack to be specific to our
        # Session design pattern, this could happen lower (and it would be simpler), but it's
        # up here so we can be more implementation-generic down the stack.
        self._wait_for_disconnect_task: Optional[asyncio.Task[Optional[mqtt.MQTTError]]] = None

    async def __aenter__(self) -> "IoTHubSession":
        # First, if using SAS auth, start up the provider
        if self._sastoken_provider:
            # NOTE: No try/except block is needed here because in the case of failure there is not
            # yet anything that we would need to clean up.
            await self._sastoken_provider.start()

        # Start/connect
        try:
            await self._mqtt_client.start()
            await self._mqtt_client.connect()
        except (Exception, asyncio.CancelledError):
            # Stop/cleanup if something goes wrong
            await self._stop_all()
            raise

        self._wait_for_disconnect_task = asyncio.create_task(
            self._mqtt_client.wait_for_disconnect()
        )

        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        traceback: TracebackType,
    ) -> None:
        try:
            await self._mqtt_client.disconnect()
        finally:
            # TODO: is it dangerous to cancel / remove this task?
            if self._wait_for_disconnect_task:
                self._wait_for_disconnect_task.cancel()
                self._wait_for_disconnect_task = None
            await self._stop_all()

    async def _stop_all(self) -> None:
        try:
            await self._mqtt_client.stop()
        finally:
            if self._sastoken_provider:
                await self._sastoken_provider.stop()

    @classmethod
    def from_connection_string(
        cls,
        connection_string: str,
        ssl_context: Optional[ssl.SSLContext] = None,
        sastoken_ttl: int = 3600,
        **kwargs,
    ) -> "IoTHubSession":
        """Instantiate an IoTHubSession using an IoT Hub device or module connection string

        :returns: A new instance of IoTHubSession
        :rtype: IoTHubSession

        :param str connection_string: The IoT Hub device connection string
        :param ssl_context: Custom SSL context to be used when establishing a connection.
            If not provided, a default one will be used
        :type ssl_context: :class:`ssl.SSLContext`
        :param sastoken_ttl: Time-to-live (in seconds) for SAS tokens used for authentication.
            A new Session will need to be created once this time expires.
            Default is 3600 seconds (1 hour).

        :keyword int keep_alive: Maximum period in seconds between MQTT communications. If no
            communications are exchanged for this period, a ping exchange will occur.
            Default is 60 seconds
        :keyword str product_info: Arbitrary product information which will be included in the
            User-Agent string
        :keyword proxy_options: Configuration structure for sending traffic through a proxy server
        :type: proxy_options: :class:`ProxyOptions`
        :keyword bool websockets: Set to 'True' to use WebSockets over MQTT. Default is 'False'

        :raises: ValueError if the provided connection string is invalid
        :raises: TypeError if an invalid keyword argument is provided
        """
        cs_obj = cs.ConnectionString(connection_string)
        if cs_obj.get(cs.X509, "").lower() == "true" and ssl_context is None:
            raise ValueError(
                "Connection string indicates X509 certificate authentication, but no ssl_context provided"
            )
        if cs.GATEWAY_HOST_NAME in cs_obj:
            hostname = cs_obj[cs.GATEWAY_HOST_NAME]
        else:
            hostname = cs_obj[cs.HOST_NAME]
        return cls(
            hostname=hostname,
            device_id=cs_obj[cs.DEVICE_ID],
            module_id=cs_obj.get(cs.MODULE_ID),
            shared_access_key=cs_obj.get(cs.SHARED_ACCESS_KEY),
            ssl_context=ssl_context,
            sastoken_ttl=sastoken_ttl,
            **kwargs,
        )

    async def send_message(self, message: Union[str, models.Message]) -> None:
        """Send a telemetry message to IoT Hub

        :param message: Message to send. If not a Message object, will be used as the payload of
            a new Message object.
        :type message: str or :class:`Message`

        :raises: MQTTError if there is an error sending the Message
        :raises: ValueError if the size of the Message payload is too large
        :raises: RuntimeError if not connected when invoked
        """
        if not self._mqtt_client.connected:
            # See NOTE 1 at the bottom of this file for why this occurs
            raise mqtt.MQTTError(rc=4)
        if not isinstance(message, models.Message):
            message = models.Message(message)
        await self._add_disconnect_interrupt_to_coroutine(self._mqtt_client.send_message(message))

    async def send_direct_method_response(
        self, method_response: models.DirectMethodResponse
    ) -> None:
        """Send a response to a direct method request

        :param method_response: The response object containing information regarding the result of
            the direct method invocation
        :type method_response: :class:`DirectMethodResponse`

        :raises: MQTTError if there is an error sending the DirectMethodResponse
        :raises: ValueError if the size of the DirectMethodResponse payload is too large
        """
        if not self._mqtt_client.connected:
            # See NOTE 1 at the bottom of this file for why this occurs
            raise mqtt.MQTTError(rc=4)
        await self._add_disconnect_interrupt_to_coroutine(
            self._mqtt_client.send_direct_method_response(method_response)
        )

    async def update_reported_properties(self, patch: custom_typing.TwinPatch) -> None:
        """Update the reported properties of the Twin

        :param dict patch: JSON object containing the updates to the Twin reported properties

        :raises: IoTHubError if an error response is received from IoT Hub
        :raises: MQTTError if there is an error sending the updated reported properties
        :raises: ValueError if the size of the the reported properties patch too large
        :raises: CancelledError if enabling responses from IoT Hub is cancelled by network failure
        """
        if not self._mqtt_client.connected:
            # See NOTE 1 at the bottom of this file for why this occurs
            raise mqtt.MQTTError(rc=4)
        await self._add_disconnect_interrupt_to_coroutine(self._mqtt_client.send_twin_patch(patch))

    async def get_twin(self) -> custom_typing.Twin:
        """Retrieve the full Twin data

        :returns: Twin as a JSON object
        :rtype: dict

        :raises: IoTHubError if a error response is received from IoTHub
        :raises: MQTTError if there is an error sending the request
        :raises: CancelledError if enabling responses from IoT Hub is cancelled by network failure
        """
        if not self._mqtt_client.connected:
            # See NOTE 1 at the bottom of this file for why this occurs
            raise mqtt.MQTTError(rc=4)
        return await self._add_disconnect_interrupt_to_coroutine(self._mqtt_client.get_twin())

    @contextlib.asynccontextmanager
    async def messages(self) -> AsyncGenerator[AsyncGenerator[models.Message, None], None]:
        """Returns an async generator of incoming C2D messages"""
        await self._mqtt_client.enable_c2d_message_receive()
        try:
            yield self._add_disconnect_interrupt_to_generator(
                self._mqtt_client.incoming_c2d_messages
            )
        finally:
            try:
                await self._mqtt_client.disable_c2d_message_receive()
            except mqtt.MQTTError:
                # i.e. not connected
                pass

    @contextlib.asynccontextmanager
    async def direct_method_requests(
        self,
    ) -> AsyncGenerator[AsyncGenerator[models.DirectMethodRequest, None], None]:
        """Returns an async generator of incoming direct method requests"""
        await self._mqtt_client.enable_direct_method_request_receive()
        try:
            yield self._add_disconnect_interrupt_to_generator(
                self._mqtt_client.incoming_direct_method_requests
            )
        finally:
            try:
                await self._mqtt_client.disable_direct_method_request_receive()
            except mqtt.MQTTError:
                # i.e. not connected
                pass

    @contextlib.asynccontextmanager
    async def desired_property_updates(
        self,
    ) -> AsyncGenerator[AsyncGenerator[custom_typing.TwinPatch, None], None]:
        """Returns an async generator of incoming twin desired property patches"""
        await self._mqtt_client.enable_twin_patch_receive()
        try:
            yield self._add_disconnect_interrupt_to_generator(
                self._mqtt_client.incoming_twin_patches
            )
        finally:
            try:
                await self._mqtt_client.disable_twin_patch_receive()
            except mqtt.MQTTError:
                # i.e. not connected
                pass

    def _add_disconnect_interrupt_to_generator(
        self, generator: AsyncGenerator[_T, None]
    ) -> AsyncGenerator[_T, None]:
        """Wrap a generator in another generator that will either return the next item yielded by
        the original generator, or raise error in the event of disconnect
        """

        async def wrapping_generator():
            while True:
                new_item_t = asyncio.create_task(generator.__anext__())
                done, _ = await asyncio.wait(
                    [new_item_t, self._wait_for_disconnect_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if self._wait_for_disconnect_task in done:
                    new_item_t.cancel()
                    cause = self._wait_for_disconnect_task.result()
                    if cause is not None:
                        raise cause
                    else:
                        # TODO: should this raise MQTTError(rc=4) instead?
                        raise asyncio.CancelledError("Cancelled by disconnect")
                else:
                    yield new_item_t.result()

        return wrapping_generator()

    def _add_disconnect_interrupt_to_coroutine(self, coro: Awaitable[_T]) -> Awaitable[_T]:
        """Wrap a coroutine in another coroutine that will either return the result of the original
        coroutine, or raise error in the event of disconnect
        """

        async def wrapping_coroutine():
            original_task = asyncio.create_task(coro)
            done, _ = await asyncio.wait(
                [original_task, self._wait_for_disconnect_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            if self._wait_for_disconnect_task in done:
                original_task.cancel()
                cause = self._wait_for_disconnect_task.result()
                if cause is not None:
                    raise cause
                else:
                    # TODO: should this raise MQTTError(rc=4) instead?
                    raise asyncio.CancelledError("Cancelled by disconnect")
            else:
                return await original_task

        return wrapping_coroutine()


def _validate_kwargs(exclude=[], **kwargs) -> None:
    """Helper function to validate user provided kwargs.
    Raises TypeError if an invalid option has been provided"""
    valid_kwargs = [
        # "auto_reconnect",
        "keep_alive",
        "product_info",
        "proxy_options",
        "websockets",
    ]

    for kwarg in kwargs:
        if (kwarg not in valid_kwargs) or (kwarg in exclude):
            # NOTE: TypeError is the conventional error that is returned when an invalid kwarg is
            # supplied. It feels like it should be a ValueError, but it's not.
            raise TypeError("Unsupported keyword argument: '{}'".format(kwarg))


def _format_sas_uri(hostname: str, device_id: str, module_id: Optional[str]) -> str:
    """Format the SAS URI for using IoT Hub"""
    if module_id:
        return "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=hostname, device_id=device_id, module_id=module_id
        )
    else:
        return "{hostname}/devices/{device_id}".format(hostname=hostname, device_id=device_id)


def _default_ssl_context() -> ssl.SSLContext:
    """Return a default SSLContext"""
    ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.check_hostname = True
    ssl_context.load_default_certs()
    return ssl_context


# NOTE 1: We raise this MQTT-level error directly because it won't naturally raise.
# Our MQTT stack below uses MQTT QoS (Quality of Service) level 1, which means it technically
# doesn't fail upon an attempt to publish an MQTT message with no connection. An rc 4 would be
# returned by the publish attempt, but no error would be raised, since the message has been queued,
# and could later be sent once a connection is established.
#
# However, for the implementation of IoTHubSession, this is not desirable  behavior - we want an
# immediate failure when sending with no connection, and the queuing of the message is strange if
# an error is raised. Thus, we manually raise an MQTT-level error (with rc 4) without actually
# making a publish attempt to emulate the MQTT QoS level 0 behavior we would prefer to have.
#
# The MQTT-level error is used instead of a higher-level one so that the error handling experience
# is simpler for the end user - MQTTError is the class of error that is raised on connection drop
# and any other MQTT-related failure, so it make sense to raise that again here.
#
# This is a highly irregular design, and if an alternate solution could be created, that would be
# ideal.
