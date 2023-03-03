# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import abc
import asyncio
import logging
import os
import ssl
from typing import Optional, cast
from .custom_typing import FunctionOrCoroutine
from .iot_exceptions import IoTEdgeEnvironmentError
from . import config, edge_hsm
from . import connection_string as cs
from . import iothub_http_client as http
from . import iothub_mqtt_client as mqtt
from . import sastoken as st
from . import signing_mechanism as sm


logger = logging.getLogger(__name__)

# TODO: finalize documentation


class IoTHubClient(abc.ABC):
    """Abstract parent class for IoTHubDeviceClient and IoTHubModuleClient containing
    partial implementation.
    """

    def __init__(self, client_config: config.IoTHubClientConfig) -> None:
        """Initializer for a generic IoTHubClient.
        Do not directly use as the end user, use a factory method instead.

        :param client_config: The IoTHubClientConfig object
        :type client_config: :class:`IoTHubClientConfig`
        """
        # Internal clients
        self._mqtt_client = mqtt.IoTHubMQTTClient(client_config)
        self._http_client = http.IoTHubHTTPClient(client_config)

        # Keep a reference to the SAS Token Provider so it can be shut down later
        self._sastoken_provider = client_config.sastoken_provider

    async def shutdown(self) -> None:
        """Shut down the client

        Call only when completely done with the client for graceful exit.

        Cannot be cancelled - if you try, the client will still fully shut down as much as
        possible (although the CancelledError will still be raised)
        """
        cached_cancel: Optional[asyncio.CancelledError] = None
        try:
            await self._mqtt_client.shutdown()
        except asyncio.CancelledError as e:
            cached_cancel = e

        try:
            await self._http_client.shutdown()
        except asyncio.CancelledError as e:
            cached_cancel = e

        if self._sastoken_provider:
            try:
                await self._sastoken_provider.shutdown()
            except asyncio.CancelledError as e:
                cached_cancel = e

        if cached_cancel:
            raise cached_cancel

    # ~~~~~ Abstract declarations ~~~~~
    # NOTE: rigid typechecking doesn't like when the signature changes in the child class
    # implementation of an abstract method. This creates problems, given that Device/Module
    # clients have some methods with different signatures. It may be worth considering
    # dropping abstract definitions altogether if their use is too inconsistent, or at least
    # paring them back to only the crucial ones (connect, shutdown)

    # @abc.abstractmethod
    # async def connect(self) -> None:
    #     raise NotImplementedError

    # @abc.abstractmethod
    # async def disconnect(self) -> None:
    #     raise NotImplementedError

    # @abc.abstractmethod
    # async def send_message(self) -> None:
    #     raise NotImplementedError

    # @abc.abstractmethod
    # async def send_direct_method_response(self) -> None:
    #     raise NotImplementedError

    # @abc.abstractmethod
    # async def send_twin_reported_properties_patch(self) -> None:
    #     raise NotImplementedError

    # @abc.abstractmethod
    # async def get_twin(self) -> Twin:
    #     raise NotImplementedError

    # ~~~~~~ Shared implementations ~~~~~

    @classmethod
    async def _shared_client_create(
        cls,
        *,
        device_id: str,
        module_id: Optional[str] = None,
        hostname: str,
        ssl_context: Optional[ssl.SSLContext] = None,
        symmetric_key: Optional[str] = None,
        sastoken_fn: Optional[FunctionOrCoroutine] = None,  # TODO: need more rigid definition
        # sastoken_fn: Optional[FunctionOrCoroutine[[], str]] = None,
        **kwargs,
    ) -> "IoTHubClient":
        """Agnostic implementation of .create() shared between Devices and Modules

        :raises: ValueError if  one of 'ssl_context', 'symmetric_key' or 'sastoken_fn' is not
            provided
        :raises: ValueError if both 'symmetric_key' and 'sastoken_fn' are provided
        :raises: SasTokenError if there is a failure generating a SAS Token
        """
        # Validate Parameters
        _validate_kwargs(**kwargs)
        if symmetric_key and sastoken_fn:
            raise ValueError(
                "Incompatible authentication - cannot provide both 'symmetric_key' and 'sastoken_fn'"
            )
        if not symmetric_key and not sastoken_fn and not ssl_context:
            raise ValueError(
                "Missing authentication - must provide one of 'symmetric_key', 'sastoken_fn' or 'ssl_context'"
            )

        if symmetric_key:
            signing_mechanism = sm.SymmetricKeySigningMechanism(symmetric_key)
        else:
            signing_mechanism = None

        # TODO: is edge valid for this method?
        return await cls._internal_factory(
            device_id=device_id,
            module_id=module_id,
            hostname=hostname,
            ssl_context=ssl_context,
            sas_signing_mechanism=signing_mechanism,
            sastoken_fn=sastoken_fn,
            **kwargs,
        )

    @classmethod
    async def _internal_factory(
        cls,
        *,
        device_id: str,
        module_id: Optional[str] = None,
        hostname: str,
        ssl_context: Optional[ssl.SSLContext] = None,
        sas_signing_mechanism: Optional[sm.SigningMechanism] = None,
        sastoken_fn: Optional[FunctionOrCoroutine] = None,  # TODO: need more rigid definition
        # sastoken_fn: Optional[FunctionOrCoroutine[[], str]] = None,
        **kwargs,
    ) -> "IoTHubClient":
        """Internal factory method that creates a client for a all configurations

        :raises: SasTokenError if there is a failure generating a SAS Token
        """
        # NOTE: Validation is assumed to have been done by the time this method is called.

        # Internal SAS Generation
        sastoken_generator: st.SasTokenGenerator
        if sas_signing_mechanism:
            uri = _format_sas_uri(hostname=hostname, device_id=device_id, module_id=module_id)
            sastoken_generator = st.InternalSasTokenGenerator(
                signing_mechanism=sas_signing_mechanism,
                uri=uri,
            )
            sastoken_provider = await st.SasTokenProvider.create_from_generator(sastoken_generator)

        # External SAS Generation
        elif sastoken_fn:
            sastoken_generator = st.ExternalSasTokenGenerator(sastoken_fn)
            sastoken_provider = await st.SasTokenProvider.create_from_generator(sastoken_generator)

        # No SAS Auth
        else:
            sastoken_provider = None

        # SSL
        if not ssl_context:
            ssl_context = _default_ssl_context()

        # Config setup
        client_config = config.IoTHubClientConfig(
            hostname=hostname,
            device_id=device_id,
            module_id=module_id,
            sastoken_provider=sastoken_provider,
            ssl_context=ssl_context,
            **kwargs,
        )

        return cls(client_config)


class IoTHubDeviceClient(IoTHubClient):
    """A client for connecting a device to an instance of IoT Hub"""

    @classmethod
    async def create(
        cls,
        device_id: str,
        hostname: str,
        ssl_context: Optional[ssl.SSLContext] = None,
        symmetric_key: Optional[str] = None,
        sastoken_fn: Optional[FunctionOrCoroutine] = None,  # TODO: more rigid definition
        # sastoken_fn: Optional[FunctionOrCoroutine[[], str]] = None,
        **kwargs,
    ) -> "IoTHubDeviceClient":
        """
        Instantiate an IoTHubDeviceClient

        - To use symmetric key authentication, provide the symmetric key as the 'symmetric_key'
            parameter
        - To use your own SAS tokens for authentication, provide a function or coroutine function
            that returns SAS Tokens as the 'sastoken_fn' parameter
        - To use X509 certificate authentication, configure an SSLContext for the certificate, and
            provide it as the 'ssl_context' parameter

        One of the these three types of authentication is required to instantiate the client.

        :param str device_id: The device identity for the IoT Hub device
        :param str hostname: Hostname of the IoT Hub or IoT Edge the device should connect to
        :param ssl_context: Custom SSL context to be used by the client
            If not provided, a default one will be used
        :type ssl_context: :class:`ssl.SSLContext`
        :param str symmetric_key: A symmetric key that can be used to generate SAS Tokens
        :param sastoken_fn: A function or coroutine function that takes no arguments and returns
            a SAS token string when invoked

        :keyword bool connection_retry: Indicates whether to use built-in connection retry policy.
            Default is 'True'
        :keyword int keep_alive: Maximum period in seconds between MQTT communications. If no
            communications are exchanged for this period, a ping exchange will occur.
            Default is 60 seconds
        :keyword str product_info: Arbitrary product information which will be included in the
            User-Agent string
        :keyword proxy_options: Configuration structure for sending traffic through a proxy server
        :type: proxy_options: :class:`ProxyOptions`
        :keyword bool websockets: Set to 'True' to use WebSockets over MQTT. Default is 'False'

        :raises: ValueError if  one of 'ssl_context', 'symmetric_key' or 'sastoken_fn' is not
            provided
        :raises: ValueError if both 'symmetric_key' and 'sastoken_fn' are provided
        :raises: SasTokenError if there is a failure generating a SAS Token

        :return: An IoTHubDeviceClient instance
        """

        client = await cls._shared_client_create(
            device_id=device_id,
            hostname=hostname,
            ssl_context=ssl_context,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            **kwargs,
        )
        return cast(IoTHubDeviceClient, client)

    @classmethod
    async def create_from_connection_string(
        cls, connection_string: str, ssl_context: Optional[ssl.SSLContext] = None, **kwargs
    ) -> "IoTHubDeviceClient":
        """Instantiate an IoTHubDeviceClient using a IoT Hub device connection string

        :param str connection_string: The IoT Hub device connection string
        :param ssl_context: Custom SSL context to be used by the client
            If not provided, a default one will be used
        :type ssl_context: :class:`ssl.SSLContext`

        :keyword bool connection_retry: Indicates whether to use built-in connection retry policy.
            Default is 'True'
        :keyword int keep_alive: Maximum period in seconds between MQTT communications. If no
            communications are exchanged for this period, a ping exchange will occur.
            Default is 60 seconds
        :keyword str product_info: Arbitrary product information which will be included in the
            User-Agent string
        :keyword proxy_options: Configuration structure for sending traffic through a proxy server
        :type: proxy_options: :class:`ProxyOptions`
        :keyword bool websockets: Set to 'True' to use WebSockets over MQTT. Default is 'False'

        :raises: ValueError if the provided connection string is invalid
        :raises: SasTokenError if there is a failure generating a SAS Token

        :return: An IoTHubDeviceClient instance
        """
        # Validate connection string for Device
        cs_obj = cs.ConnectionString(connection_string)
        if cs.MODULE_ID in cs_obj:
            raise ValueError("IoT Hub module connection string provided for IoTHubDeviceClient")

        signing_mechanism = sm.SymmetricKeySigningMechanism(cs_obj[cs.SHARED_ACCESS_KEY])

        # If the Gateway Hostname exists, use it instead of the Hostname
        hostname = cs_obj.get(cs.GATEWAY_HOST_NAME, cs_obj[cs.HOST_NAME])

        client = await cls._internal_factory(
            device_id=cs_obj[cs.DEVICE_ID],
            hostname=hostname,
            sas_signing_mechanism=signing_mechanism,
            ssl_context=ssl_context,
            **kwargs,
        )
        return cast(IoTHubDeviceClient, client)


class IoTHubModuleClient(IoTHubClient):
    """A client for connecting a module to an instance of IoT Hub"""

    @classmethod
    async def create(
        cls,
        device_id: str,
        module_id: str,
        hostname: str,
        ssl_context: Optional[ssl.SSLContext] = None,
        symmetric_key: Optional[str] = None,
        # sastoken_fn: Optional[FunctionOrCoroutine[[], str]] = None,
        sastoken_fn: Optional[FunctionOrCoroutine] = None,  # TODO: more rigid definition
        **kwargs,
    ) -> "IoTHubModuleClient":
        """
        Instantiate an IoTHubModuleClient

        - To use symmetric key authentication, provide the symmetric key as the 'symmetric_key'
            parameter
        - To use your own SAS tokens for authentication, provide a function or coroutine function
            that returns SAS Tokens as the 'sastoken_fn' parameter
        - To use X509 certificate authentication, configure an SSLContext for the certificate, and
            provide it as the 'ssl_context' parameter

        One of the these three types of authentication is required to instantiate the client.

        :param str device_id: The device identity for the IoT Hub device containing the
            IoT Hub module
        :param str module_id: The module identity for the IoT Hub module
        :param str hostname: Hostname of the IoT Hub or IoT Edge the device should connect to
        :param ssl_context: Custom SSL context to be used by the client
            If not provided, a default one will be used
        :type ssl_context: :class:`ssl.SSLContext`
        :param str symmetric_key: A symmetric key that can be used to generate SAS Tokens
        :param sastoken_fn: A function or coroutine function that takes no arguments and returns
            a SAS token string when invoked

        :keyword bool connection_retry: Indicates whether to use built-in connection retry policy.
            Default is 'True'
        :keyword int keep_alive: Maximum period in seconds between MQTT communications. If no
            communications are exchanged for this period, a ping exchange will occur.
            Default is 60 seconds
        :keyword str product_info: Arbitrary product information which will be included in the
            User-Agent string
        :keyword proxy_options: Configuration structure for sending traffic through a proxy server
        :type: proxy_options: :class:`ProxyOptions`
        :keyword bool websockets: Set to 'True' to use WebSockets over MQTT. Default is 'False'

        :raises: ValueError if  one of 'ssl_context', 'symmetric_key' or 'sastoken_fn' is not
            provided
        :raises: ValueError if both 'symmetric_key' and 'sastoken_fn' are provided
        :raises: SasTokenError if there is a failure generating a SAS Token

        :return: An IoTHubModuleClient instance
        """
        client = await cls._shared_client_create(
            device_id=device_id,
            module_id=module_id,
            hostname=hostname,
            ssl_context=ssl_context,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            **kwargs,
        )
        return cast(IoTHubModuleClient, client)

    @classmethod
    async def create_from_connection_string(
        cls, connection_string: str, ssl_context: Optional[ssl.SSLContext] = None, **kwargs
    ) -> "IoTHubModuleClient":
        """Instantiate an IoTHubModuleClient using a IoT Hub module connection string

        :param str connection_string: The IoT Hub module connection string
        :param ssl_context: Custom SSL context to be used by the client
            If not provided, a default one will be used
        :type ssl_context: :class:`ssl.SSLContext`

        :keyword bool connection_retry: Indicates whether to use built-in connection retry policy.
            Default is 'True'
        :keyword int keep_alive: Maximum period in seconds between MQTT communications. If no
            communications are exchanged for this period, a ping exchange will occur.
            Default is 60 seconds
        :keyword str product_info: Arbitrary product information which will be included in the
            User-Agent string
        :keyword proxy_options: Configuration structure for sending traffic through a proxy server
        :type: proxy_options: :class:`ProxyOptions`
        :keyword bool websockets: Set to 'True' to use WebSockets over MQTT. Default is 'False'
        :raises: ValueError if the provided connection string is invalid
        :raises: SasTokenError if there is a failure generating a SAS Token

        :return: An IoTHubModuleClient instance
        """
        # Validate connection string for Module
        cs_obj = cs.ConnectionString(connection_string)
        if cs.MODULE_ID not in cs_obj:
            raise ValueError("IoT Hub device connection string provided for IoTHubModuleClient")

        # If the Gateway Hostname exists, use it instead of the Hostname
        hostname = cs_obj.get(cs.GATEWAY_HOST_NAME, cs_obj[cs.HOST_NAME])

        client = await cls._internal_factory(
            device_id=cs_obj[cs.DEVICE_ID],
            hostname=hostname,
            symmetric_key=cs_obj[cs.SHARED_ACCESS_KEY],
            ssl_context=ssl_context,
            **kwargs,
        )
        return cast(IoTHubModuleClient, client)

    async def create_from_edge_environment(cls, **kwargs) -> "IoTHubModuleClient":
        """Instantiate an IoTHubModuleClient using information from an IoT Edge environment

        This method can only be run from inside an IoT Edge environment, or in a debugging
        environment configured for Edge development (e.g. Visual Studio Code)

        :keyword bool connection_retry: Indicates whether to use built-in connection retry policy.
            Default is 'True'
        :keyword int keep_alive: Maximum period in seconds between MQTT communications. If no
            communications are exchanged for this period, a ping exchange will occur.
            Default is 60 seconds
        :keyword str product_info: Arbitrary product information which will be included in the
            User-Agent string
        :keyword proxy_options: Configuration structure for sending traffic through a proxy server
        :type: proxy_options: :class:`ProxyOptions`
        :keyword bool websockets: Set to 'True' to use WebSockets over MQTT. Default is 'False'

        :raises: IoTEdgeEnvironmentError if the required environment variables are not present or
            cannot be accessed
        :raises: IoTEdgeError if there is a failure with the IoT Edge
        :raises: SasTokenError if there is a failure generating a SAS Token

        :return: An IoTHubModuleClient instance
        """
        _validate_kwargs(**kwargs)

        try:
            # First, try to find the regular IoT Edge environment variables
            return await cls._create_from_real_edge_environment(**kwargs)
        except IoTEdgeEnvironmentError as original_exception:
            try:
                # If they can't be found, try looking for the IoT Edge simulator variables
                return await cls._create_from_simulated_edge_environment(**kwargs)
            except IoTEdgeEnvironmentError:
                # Raise the original error if the IoT Edge simulator variables also cannot be found
                raise original_exception

    async def _create_from_real_edge_environment(cls, **kwargs) -> "IoTHubModuleClient":
        """Instantiate an IoTHubModuleClient from values stored in environment variables
        in a IoT Edge deployment environment.

        :raises: IoTEdgeEnvironmentError if IoT Edge environment variables are not present or
            cannot be accessed
        :raises: IoTEdgeError if there is a failure communicating with IoT Edge
        :raises: SasTokenError if there is a failure generating a SAS Token
        """
        # Read values from the IoT Edge environment variables
        try:
            device_id = os.environ["IOTEDGE_DEVICEID"]
            module_id = os.environ["IOTEDGE_MODULEID"]
            hostname = os.environ["IOTEDGE_GATEWAYHOSTNAME"]
            module_generation_id = os.environ["IOTEDGE_MODULEGENERATIONID"]
            workload_uri = os.environ["IOTEDGE_WORKLOADURI"]
            api_version = os.environ["IOTEDGE_APIVERSION"]
        except KeyError as e:
            raise IoTEdgeEnvironmentError("Could not retrieve Edge environment variables") from e

        # The IoT Edge HSM will be used to get the verification certs, as well as to sign data
        # for making SAS Tokens
        hsm = edge_hsm.IoTEdgeHsm(
            module_id=module_id,
            generation_id=module_generation_id,
            workload_uri=workload_uri,
            api_version=api_version,
        )

        # Set up Edge SSL context by loading the cert
        server_verification_cert = await hsm.get_certificate()
        ssl_context = _default_ssl_context()
        # TODO: verify that it's okay to load this cert after already loading default certs
        ssl_context.load_verify_locations(cadata=server_verification_cert)

        # Send to the internal factory
        client = await cls._internal_factory(
            device_id=device_id,
            module_id=module_id,
            hostname=hostname,
            ssl_context=ssl_context,
            sas_signing_mechanism=hsm,
            **kwargs,
        )
        return cast(IoTHubModuleClient, client)

    async def _create_from_simulated_edge_environment(cls, **kwargs) -> "IoTHubModuleClient":
        """Instantiate an IoTHubModuleClient from values stored in environment variables
        in a simulated IoT Edge environment

        :raises: IoTEdgeEnvironmentError if IoT Edge environment variables are not present or
            cannot be accessed
        :raises: SasTokenError if there is a failure generating a SAS Token
        """
        # Read values from the IoT Edge Simulator environment variables
        try:
            connection_string = os.environ["EdgeHubConnectionString"]
            ca_cert_filepath = os.environ["EdgeModuleCACertificateFile"]
        except KeyError as e:
            raise IoTEdgeEnvironmentError("Could not retrieve Edge environment variables") from e

        # Set up Edge SSL context by loading the cert file
        ssl_context = _default_ssl_context()
        # TODO: verify that it's okay to load this cert after already loading default certs
        ssl_context.load_verify_locations(cafile=ca_cert_filepath)

        # Since we have a connection string, just use the connection string factory
        return await cls.create_from_connection_string(
            connection_string, ssl_context=ssl_context, **kwargs
        )


def _validate_kwargs(exclude=[], **kwargs):
    """Helper function to validate user provided kwargs.
    Raises TypeError if an invalid option has been provided"""
    valid_kwargs = [
        "connection_retry",
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


def _default_ssl_context() -> ssl.SSLContext:
    """Return a default SSLContext"""
    ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.check_hostname = True
    ssl_context.load_default_certs()
    return ssl_context


def _format_sas_uri(hostname: str, device_id: str, module_id: Optional[str] = None) -> str:
    if module_id:
        return "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=hostname, device_id=device_id, module_id=module_id
        )
    else:
        return "{hostname}/devices/{device_id}".format(hostname=hostname, device_id=device_id)
