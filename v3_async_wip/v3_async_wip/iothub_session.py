# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import asyncio
import contextlib
import ssl
from typing import Optional, Union

# from v3_async_wip import signing_mechanism as sm
# from v3_async_wip import connection_string as cs
from v3_async_wip import sastoken as st
from v3_async_wip import config, models, custom_typing
from v3_async_wip.iothub_mqtt_client import IoTHubMQTTClient


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

        :raises: ValueError if  one of 'ssl_context', 'symmetric_key' or 'sastoken_fn' is not
            provided
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

        # Need to keep a reference to the SasTokenProvider so we can stop it during cleanup
        self._sastoken_provider: Optional[st.SasTokenProvider]
        if shared_access_key or sastoken_fn:
            self._sastoken_provider = _create_sastoken_provider(
                shared_access_key=shared_access_key, sastoken_fn=sastoken_fn
            )
        else:
            self._sastoken_provider = None

        # Instantiate the MQTTClient
        cfg = config.IoTHubClientConfig(
            hostname=hostname,
            device_id=device_id,
            module_id=module_id,
            sastoken_provider=self._sastoken_provider,
            ssl_context=ssl_context,
        )
        self._mqtt_client = IoTHubMQTTClient(cfg)

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

    # @classmethod
    # def from_connection_string(
    #     cls, connection_string: str, ssl_context: Optional[ssl.SSLContext] = None, **kwargs
    # ) -> "IoTHubSession":
    #     """Instantiate an IoTHubSession using an IoT Hub device or module connection string

    #     :param str connection_string: The IoT Hub device connection string
    #     :param ssl_context: Custom SSL context to be used by the client
    #         If not provided, a default one will be used
    #     :type ssl_context: :class:`ssl.SSLContext`

    #     :keyword int keep_alive: Maximum period in seconds between MQTT communications. If no
    #         communications are exchanged for this period, a ping exchange will occur.
    #         Default is 60 seconds
    #     :keyword str product_info: Arbitrary product information which will be included in the
    #         User-Agent string
    #     :keyword proxy_options: Configuration structure for sending traffic through a proxy server
    #     :type: proxy_options: :class:`ProxyOptions`
    #     :keyword bool websockets: Set to 'True' to use WebSockets over MQTT. Default is 'False'

    #     :raises: ValueError if the provided connection string is invalid
    #     """
    #     cs_obj = cs.ConnectionString(connection_string)
    #     signing_mechanism = sm.SymmetricKeySigningMechanism(cs_obj[cs.SHARED_ACCESS_KEY])
    #     uri = "{hostname}/devices/{device_id}".format(
    #         hostname=cs_obj[cs.HOST_NAME], device_id=cs_obj[cs.DEVICE_ID]
    #     )
    #     generator = st.InternalSasTokenGenerator(signing_mechanism=signing_mechanism, uri=uri)
    #     provider = st.SasTokenProvider(generator)
    #     return cls(
    #         hostname=cs_obj[cs.HOST_NAME],
    #         device_id=cs_obj[cs.DEVICE_ID],
    #         sas_auth=provider,
    #     )

    async def send_message(self, message: Union[str, models.Message]):
        if not isinstance(message, models.Message):
            message = models.Message(message)
        await self._mqtt_client.send_message(message)

    async def send_direct_method_response(self, method_response: models.DirectMethodResponse):
        await self._mqtt_client.send_direct_method_response(method_response)

    async def send_twin_patch(self, twin_patch: custom_typing.TwinPatch):
        await self._mqtt_client.send_twin_patch(twin_patch)

    async def get_twin(self):
        await self._mqtt_client.get_twin()

    @contextlib.asynccontextmanager
    async def messages(self):
        await self._mqtt_client.enable_c2d_message_receive()
        try:
            yield self._mqtt_client.incoming_c2d_messages
        finally:
            await self._mqtt_client.disable_c2d_message_receive()

    @contextlib.asynccontextmanager
    async def direct_method_requests(self):
        await self._mqtt_client.enable_direct_method_request_receive()
        try:
            yield self._mqtt_client.incoming_direct_method_requests
        finally:
            await self._mqtt_client.disable_direct_method_request_receive()

    # TODO: Clarify naming
    @contextlib.asynccontextmanager
    async def twin_patches(self):
        await self._mqtt_client.enable_twin_patch_receive()
        try:
            yield self._mqtt_client.incoming_twin_patches
        finally:
            await self._mqtt_client.disable_twin_patch_receive()


def _validate_kwargs(exclude=[], **kwargs):
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


def _create_sastoken_provider(
    *, shared_access_key: Optional[str], sastoken_fn: Optional[custom_typing.FunctionOrCoroutine]
):  # -> st.SasTokenProvider:
    # NOTE: these two arguments are mutually exclusive. While that is not validated here,
    # it is validated by the caller (the IoTHubSession __init__)
    pass
    # if shared_access_key:
