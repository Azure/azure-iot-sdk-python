# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import asyncio
import ssl
from typing import Optional, Type, Awaitable, TypeVar
from types import TracebackType

from . import signing_mechanism as sm
from . import sastoken as st
from . import config, custom_typing
from . import provisioning_mqtt_client as mqtt
from .custom_typing import RegistrationPayload

_T = TypeVar("_T")


class ProvisioningSession:
    def __init__(
        self,
        *,
        provisioning_host: str,
        id_scope: str,
        registration_id: str,
        ssl_context: Optional[ssl.SSLContext] = None,
        shared_access_key: Optional[str] = None,
        sastoken_fn: Optional[custom_typing.FunctionOrCoroutine] = None,
        **kwargs,
    ) -> None:
        """
        :param str registration_id: The device registration identity being provisioned.
        :param str hostname: The hostname of the Provisioning hub instance to connect to.
        :param ssl_context: Custom SSL context to be used by the client
            If not provided, a default one will be used
        :type ssl_context: :class:`ssl.SSLContext`
        :param str shared_access_key: A key that can be used to generate SAS Tokens
        :param sastoken_fn: A function or coroutine function that takes no arguments and returns
            a SAS token string when invoked

        :raises: ValueError if none of 'ssl_context', 'symmetric_key' or 'sastoken_fn' are provided
        :raises: ValueError if both 'symmetric_key' and 'sastoken_fn' are provided
        :raises: ValueError if an invalid 'symmetric_key' is provided
        :raises: TypeError if an invalid keyword argument is provided
        """
        # The following validation is present in the previous SDK.
        _validate_registration_id(registration_id)
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
            uri = _format_sas_uri(id_scope=id_scope, registration_id=registration_id)
            signing_mechanism = sm.SymmetricKeySigningMechanism(shared_access_key)
            # TODO This existed before
            token_ttl = kwargs.get("sastoken_ttl", 3600)
            generator = st.InternalSasTokenGenerator(
                signing_mechanism=signing_mechanism, uri=uri, ttl=token_ttl
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
        client_config = config.ProvisioningClientConfig(
            hostname=provisioning_host,
            registration_id=registration_id,
            id_scope=id_scope,
            sastoken_provider=self._sastoken_provider,
            ssl_context=ssl_context,
            auto_reconnect=False,  # No reconnect for now
            **kwargs,
        )
        self._mqtt_client = mqtt.ProvisioningMQTTClient(client_config)
        self._wait_for_disconnect_task: Optional[asyncio.Task[Optional[mqtt.MQTTError]]] = None

    async def __aenter__(self) -> "ProvisioningSession":
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

    async def register(
        self, payload: Optional[RegistrationPayload] = None
    ) -> custom_typing.RegistrationResult:
        """Register the device

        :returns: RegistrationResult
        :rtype: RegistrationResult

        :raises: ProvisioningError if a error response is received from IoTHub
        :raises: MQTTError if there is an error sending the request
        :raises: CancelledError if enabling responses from IoT Hub is cancelled by network failure
        """
        if not self._mqtt_client.connected:
            # See NOTE 1 at the bottom of iothub_session file for why this occurs
            raise mqtt.MQTTError(rc=4)
        return await self._add_disconnect_interrupt_to_coroutine(
            self._mqtt_client.send_register(payload)
        )

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
        # "server_verification_cert",
        # "gateway_hostname",
        "websockets",
        # "cipher",
        "proxy_options",
        "sastoken_ttl",
        "keep_alive",
    ]

    for kwarg in kwargs:
        if (kwarg not in valid_kwargs) or (kwarg in exclude):
            # NOTE: TypeError is the conventional error that is returned when an invalid kwarg is
            # supplied. It feels like it should be a ValueError, but it's not.
            raise TypeError("Unsupported keyword argument: '{}'".format(kwarg))


def _validate_registration_id(reg_id: str):
    if not (reg_id and reg_id.strip()):
        raise ValueError("Registration Id can not be none, empty or blank.")


def _format_sas_uri(id_scope: str, registration_id: str) -> str:
    """Format the SAS URI DPS"""
    return "{id_scope}/registrations/{registration_id}".format(
        id_scope=id_scope, registration_id=registration_id
    )


def _default_ssl_context() -> ssl.SSLContext:
    """Return a default SSLContext"""
    ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.check_hostname = True
    ssl_context.load_default_certs()
    return ssl_context
