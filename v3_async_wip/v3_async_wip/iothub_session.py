# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import asyncio
import contextlib
import ssl
from typing import Optional, Union, AsyncGenerator

from v3_async_wip import signing_mechanism as sm
from v3_async_wip import connection_string as cs
from v3_async_wip import sastoken as st
from v3_async_wip import config, models, custom_typing
from v3_async_wip import iothub_mqtt_client as mqtt


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
        **kwargs,
    ) -> None:
        """
        :param str device_id: The device identity for the IoT Hub device containing the
            IoT Hub module
        :param str module_id: The module identity for the IoT Hub module
        :param str hostname: Hostname of the IoT Hub or IoT Edge the device should connect to
        :param ssl_context: Custom SSL context to be used by the client
            If not provided, a default one will be used
        :type ssl_context: :class:`ssl.SSLContext`
        :param str shared_access_key: A key that can be used to generate SAS Tokens
        :param sastoken_fn: A function or coroutine function that takes no arguments and returns
            a SAS token string when invoked

        :raises: ValueError if none of 'ssl_context', 'symmetric_key' or 'sastoken_fn' are provided
        :raises: ValueError if both 'symmetric_key' and 'sastoken_fn' are provided
        :raises: ValueError if an invalid 'symmetric_key' is provided
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
            generator = st.InternalSasTokenGenerator(signing_mechanism=signing_mechanism, uri=uri)
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
        cfg = config.IoTHubClientConfig(
            hostname=hostname,
            device_id=device_id,
            module_id=module_id,
            sastoken_provider=self._sastoken_provider,
            ssl_context=ssl_context,
            auto_reconnect=False,  # No reconnect for now
            **kwargs,
        )
        self._mqtt_client = mqtt.IoTHubMQTTClient(cfg)

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
            await self._stop()
            raise

        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._mqtt_client.disconnect()
        await self._stop()

    async def _stop(self) -> None:
        await self._mqtt_client.stop()
        if self._sastoken_provider:
            await self._sastoken_provider.stop()

    @classmethod
    def from_connection_string(
        cls, connection_string: str, ssl_context: Optional[ssl.SSLContext] = None, **kwargs
    ) -> "IoTHubSession":
        """Instantiate an IoTHubSession using an IoT Hub device or module connection string

        :param str connection_string: The IoT Hub device connection string
        :param ssl_context: Custom SSL context to be used by the client
            If not provided, a default one will be used
        :type ssl_context: :class:`ssl.SSLContext`

        :keyword int keep_alive: Maximum period in seconds between MQTT communications. If no
            communications are exchanged for this period, a ping exchange will occur.
            Default is 60 seconds
        :keyword str product_info: Arbitrary product information which will be included in the
            User-Agent string
        :keyword proxy_options: Configuration structure for sending traffic through a proxy server
        :type: proxy_options: :class:`ProxyOptions`
        :keyword bool websockets: Set to 'True' to use WebSockets over MQTT. Default is 'False'

        :raises: ValueError if the provided connection string is invalid
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
            **kwargs,
        )

    # TODO: should "output" be an optional argument here?
    async def send_message(self, message: Union[str, models.Message]) -> None:
        """Send a telemetry or input message to its destination

        :param message: Message to send. If not a Message object, will be used as the payload of
            a new Message object.
        :type message: str or :class:`Message`

        :raises: MQTTError if there is an error sending the Message
        :raises: ValueError if the size of the Message payload is too large
        """
        if not isinstance(message, models.Message):
            message = models.Message(message)
        await self._mqtt_client.send_message(message)

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
        await self._mqtt_client.send_direct_method_response(method_response)

    async def update_reported_properties(self, patch: custom_typing.TwinPatch) -> None:
        """Update the reported properties of the Twin

        :param dict patch: JSON object containing the updates to the Twin reported properties

        :raises: MQTTError if there is an error sending the twin patch
        :raises: ValueError if the size of the the twin patch is too large
        :raises: CancelledError if enabling twin responses is cancelled by network failure      # TODO: what should the behavior be here?
        """
        await self._mqtt_client.send_twin_patch(patch)

    async def get_twin(self) -> custom_typing.Twin:
        """Retrieve the full Twin data

        :returns: Twin as a JSON object
        :rtype: dict

        :raises: IoTHubError if a error response is received from IoTHub
        :raises: MQTTError if there is an error sending the twin request
        :raises: CancelledError if enabling twin responses is cancelled by network failure
        """
        return await self._mqtt_client.get_twin()

    # TODO: does this need to support input messages? Pending discussion re: Edge
    @contextlib.asynccontextmanager
    async def messages(self) -> AsyncGenerator[AsyncGenerator[models.Message, None], None]:
        """Returns an async generator of incoming C2D messages"""
        await self._mqtt_client.enable_c2d_message_receive()
        try:
            yield self._mqtt_client.incoming_c2d_messages
        finally:
            await self._mqtt_client.disable_c2d_message_receive()

    @contextlib.asynccontextmanager
    async def direct_method_requests(
        self,
    ) -> AsyncGenerator[AsyncGenerator[models.DirectMethodRequest, None], None]:
        """Returns an async generator of incoming direct method requests"""
        await self._mqtt_client.enable_direct_method_request_receive()
        try:
            yield self._mqtt_client.incoming_direct_method_requests
        finally:
            await self._mqtt_client.disable_direct_method_request_receive()

    @contextlib.asynccontextmanager
    async def desired_property_updates(
        self,
    ) -> AsyncGenerator[AsyncGenerator[custom_typing.TwinPatch, None], None]:
        """Returns an async generator of incoming twin desired property patches"""
        await self._mqtt_client.enable_twin_patch_receive()
        try:
            yield self._mqtt_client.incoming_twin_patches
        finally:
            await self._mqtt_client.disable_twin_patch_receive()


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
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.check_hostname = True
    ssl_context.load_default_certs()
    return ssl_context
