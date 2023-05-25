# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import asyncio
import contextlib
import functools
import logging
import ssl
from typing import Optional, Union, AsyncGenerator, Type, TypeVar, Awaitable
from types import TracebackType

from . import exceptions as exc
from . import signing_mechanism as sm
from . import connection_string as cs
from . import sastoken as st
from . import config, models, custom_typing
from . import iothub_mqtt_client as mqtt

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


def _requires_connection(f):
    """Decorator to indicate a method requires the Session to already be connected."""

    @functools.wraps(f)
    def check_connection_wrapper(*args, **kwargs):
        this = args[0]  # a.k.a. self
        if not this._mqtt_client.connected:
            # NOTE: We need to raise an error directly if not connected because at MQTT
            # Quality of Service (QoS) level 1, used at the lower levels of this stack,
            # a MQTT Publish does not actually fail if not connected - instead, it waits
            # for a connection to be established, and publishes the data once connected.
            #
            # This is not desirable behavior, so we check the connection state before
            # any network operation over MQTT. While this issue only affects MQTT Publishes,
            # and not MQTT Subscribes or Unsubscribes, we want this logic to be used
            # on all methods that do MQTT operations for consistency.
            raise exc.SessionError("IoTHubSession not connected")
        else:
            return f(*args, **kwargs)

    return check_connection_wrapper


class IoTHubSession:
    def __init__(
        self,
        *,
        hostname: str,  # iothub_hostname?
        device_id: str,
        module_id: Optional[str] = None,
        ssl_context: Optional[ssl.SSLContext] = None,
        shared_access_key: Optional[str] = None,
        sastoken: Optional[str] = None,
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
        :param str sastoken: A SAS Token string to use directly as a credential
        :param sastoken_ttl: Time-to-live (in seconds) for SAS tokens generated when using
            'shared_access_key' authentication.
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
        :raises: ValueError if an invalid parameter value is provided
        :raises: TypeError if an unsupported keyword argument is provided
        """
        # Validate parameters
        _validate_kwargs(**kwargs)
        if shared_access_key and sastoken:
            raise ValueError(
                "Incompatible authentication - cannot provide both 'shared_access_key' and 'sastoken'"
            )
        if not shared_access_key and not sastoken and not ssl_context:
            raise ValueError(
                "Missing authentication - must provide one of 'shared_access_key', 'sastoken' or 'ssl_context'"
            )

        if not ssl_context:
            ssl_context = _default_ssl_context()

        # Set up SAS auth for future use (if using)
        self._user_sastoken: Optional[st.SasToken] = None
        self._sastoken_generator: Optional[st.SasTokenGenerator] = None
        self._sastoken_ttl = sastoken_ttl
        if shared_access_key:
            # If using SasToken generation, we cannot generate during this __init__
            # because .generate_sastoken() is a coroutine. The token will be generated and then
            # set on the underlying client upon context manager entry
            uri = _format_sas_uri(hostname=hostname, device_id=device_id, module_id=module_id)
            signing_mechanism = sm.SymmetricKeySigningMechanism(shared_access_key)
            self._sastoken_generator = st.SasTokenGenerator(
                signing_mechanism=signing_mechanism, uri=uri
            )
        elif sastoken:
            # If directly using a SasToken, it is set here, and will later be set on the
            # underlying client upon context manager entry
            new_sas = st.SasToken(sastoken)
            if new_sas.is_expired():
                raise ValueError("SAS Token has already expired")
            self._user_sastoken = new_sas

        # Instantiate the MQTTClient
        client_config = config.IoTHubClientConfig(
            hostname=hostname,
            device_id=device_id,
            module_id=module_id,
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
        self._wait_for_disconnect_task: Optional[
            asyncio.Task[Optional[exc.MQTTConnectionDroppedError]]
        ] = None

    async def __aenter__(self) -> "IoTHubSession":
        """
        Connect and begin a session with the IoTHub

        :raises: MQTTConnectionFailedError if connecting fails
        :raises: CredentialError if user-provided SAS Token has expired
        """
        # First, if using SAS auth, set it on the underlying client
        if self._user_sastoken:
            # NOTE: We don't need to validate here, because .connect() below will fail
            # with a CredentialError if this token is already expired.
            self._mqtt_client.set_sastoken(self._user_sastoken)
        elif self._sastoken_generator:
            self._mqtt_client.set_sastoken(
                await self._sastoken_generator.generate_sastoken(ttl=self._sastoken_ttl)
                # NOTE: Because the SasToken is generated here, rather than at object instantiation
                # (which it has to be, due to using a coroutine), this creates an issue with E2E
                # tests, where the SasToken errantly shows up as a memory leak. This has been
                # suppressed for now, but un-setting the SasToken upon context manager exit
                # (or failed entry) may be a preferable long term solution, although it has
                # drawbacks in terms of complexity surrounding error cases.
            )

        # Start/connect
        try:
            await self._mqtt_client.start()
            await self._mqtt_client.connect()
        except (Exception, asyncio.CancelledError):
            # Stop/cleanup if something goes wrong
            await self._mqtt_client.stop()
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
        """Disconnect and end a session with the IoTHub"""
        try:
            await self._mqtt_client.disconnect()
        finally:
            # TODO: is it dangerous to cancel / remove this task?
            if self._wait_for_disconnect_task:
                self._wait_for_disconnect_task.cancel()
                self._wait_for_disconnect_task = None
            await self._mqtt_client.stop()

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
        :raises: TypeError if an unsupported keyword argument is provided
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
            sastoken=cs_obj.get(cs.SHARED_ACCESS_SIGNATURE),
            ssl_context=ssl_context,
            sastoken_ttl=sastoken_ttl,
            **kwargs,
        )

    def update_sastoken(self, sastoken: str) -> None:
        """Update the current user-provided SAS token.

        This SAS token will be used the next time a connection with IoT Hub is established.

        :raises: SessionError if not using user-provided SAS auth
        :raises: ValueError if the provided SAS token is expired
        :raises: ValueError if the provided SAS token is invalid
        """
        if self._mqtt_client.connected:
            logger.warning(
                "Currently connected - Updated SAS token will not take effect until a new connection is established"
            )
        if not self._user_sastoken:
            raise exc.SessionError(
                "Cannot update SAS Token when not using user-provided SAS Token auth"
            )
        new_sas = st.SasToken(sastoken)
        if new_sas.is_expired():
            # NOTE: Use a ValueError here instead of a CredentialError.
            # The provided value has not yet been used as a credential, so it's still just a value.
            # Additionally, this keeps the CredentialError for just situations where there is an
            # issue with a credential that is currently in use.
            raise ValueError("SAS Token has already expired")
        self._user_sastoken = new_sas

    @_requires_connection
    async def send_message(self, message: Union[str, models.Message]) -> None:
        """Send a telemetry message to IoT Hub

        :param message: Message to send. If not a Message object, will be used as the payload of
            a new Message object.
        :type message: str or :class:`Message`

        :raises: MQTTError if there is an error sending the Message
        :raises: MQTTConnectionDroppedError if the connection is lost during the send attempt
        :raises: SessionError if there is no connection
        :raises: ValueError if the size of the Message payload is too large
        """
        if not isinstance(message, models.Message):
            message = models.Message(message)
        await self._add_disconnect_interrupt_to_coroutine(self._mqtt_client.send_message(message))

    @_requires_connection
    async def send_direct_method_response(
        self, method_response: models.DirectMethodResponse
    ) -> None:
        """Send a response to a direct method request

        :param method_response: The response object containing information regarding the result of
            the direct method invocation
        :type method_response: :class:`DirectMethodResponse`

        :raises: MQTTError if there is an error sending the DirectMethodResponse
        :raises: MQTTConnectionDroppedError if the connection is lost during the send attempt
        :raises: SessionError if there is no connection
        :raises: ValueError if the size of the DirectMethodResponse payload is too large
        """
        await self._add_disconnect_interrupt_to_coroutine(
            self._mqtt_client.send_direct_method_response(method_response)
        )

    @_requires_connection
    async def update_reported_properties(self, patch: custom_typing.TwinPatch) -> None:
        """Update the reported properties of the Twin

        :param dict patch: JSON object containing the updates to the Twin reported properties

        :raises: IoTHubError if an error response is received from IoT Hub
        :raises: MQTTError if there is an error sending the updated reported properties
        :raises: MQTTConnectionDroppedError if the connection is lost during the send attempt
        :raises: SessionError if there is no connection
        :raises: ValueError if the size of the the reported properties patch too large
        :raises: CancelledError if enabling responses from IoT Hub is cancelled by network failure
        """
        await self._add_disconnect_interrupt_to_coroutine(self._mqtt_client.send_twin_patch(patch))

    @_requires_connection
    async def get_twin(self) -> custom_typing.Twin:
        """Retrieve the full Twin data

        :returns: Twin as a JSON object
        :rtype: dict

        :raises: IoTHubError if a error response is received from IoTHub
        :raises: MQTTError if there is an error sending the request
        :raises: MQTTConnectionDroppedError if the connection is lost during the send attempt
        :raises: SessionError if there is no connection
        :raises: CancelledError if enabling responses from IoT Hub is cancelled by network failure
        """
        return await self._add_disconnect_interrupt_to_coroutine(self._mqtt_client.get_twin())

    @contextlib.asynccontextmanager
    @_requires_connection
    async def messages(self) -> AsyncGenerator[AsyncGenerator[models.Message, None], None]:
        """Returns an async generator of incoming C2D messages"""
        await self._mqtt_client.enable_c2d_message_receive()
        try:
            yield self._add_disconnect_interrupt_to_generator(
                self._mqtt_client.incoming_c2d_messages
            )
        finally:
            try:
                if self._mqtt_client.connected:
                    await self._mqtt_client.disable_c2d_message_receive()
            except exc.MQTTError:
                # i.e. not connected
                # This error would be expected if a disconnection has ocurred
                pass

    @contextlib.asynccontextmanager
    @_requires_connection
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
                if self._mqtt_client.connected:
                    await self._mqtt_client.disable_direct_method_request_receive()
            except exc.MQTTError:
                # i.e. not connected
                # This error would be expected if a disconnection has ocurred
                pass

    @contextlib.asynccontextmanager
    @_requires_connection
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
                if self._mqtt_client.connected:
                    await self._mqtt_client.disable_twin_patch_receive()
            except exc.MQTTError:
                # i.e. not connected
                # This error would be expected if a disconnection has ocurred
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
                    raise asyncio.CancelledError("Cancelled by disconnect")
            else:
                return await original_task

        return wrapping_coroutine()

    @property
    def connected(self) -> bool:
        return self._mqtt_client.connected

    @property
    def device_id(self) -> str:
        return self._mqtt_client._device_id

    @property
    def module_id(self) -> Optional[str]:
        return self._mqtt_client._module_id


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
