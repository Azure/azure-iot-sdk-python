# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains abstract classes for the various clients of the Azure IoT Hub Device SDK
"""
from __future__ import annotations  # Needed for annotation bug < 3.10
import abc
import logging
import threading
import os
import io
import time
from . import pipeline
from .pipeline import constant as pipeline_constant
from azure.iot.device.common.auth import connection_string as cs
from azure.iot.device.common.auth import sastoken as st
from azure.iot.device.iothub import client_event
from azure.iot.device.iothub.models import Message, MethodRequest, MethodResponse
from azure.iot.device.common.models import X509
from azure.iot.device import exceptions
from azure.iot.device.common import auth, handle_exceptions
from . import edge_hsm
from .pipeline import MQTTPipeline, HTTPPipeline
from typing_extensions import Self
from azure.iot.device.custom_typing import FunctionOrCoroutine, Twin, TwinPatch
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def _validate_kwargs(exclude: Optional[List[str]] = [], **kwargs) -> None:
    """Helper function to validate user provided kwargs.
    Raises TypeError if an invalid option has been provided"""
    valid_kwargs = [
        "server_verification_cert",
        "gateway_hostname",
        "websockets",
        "cipher",
        "product_info",
        "proxy_options",
        "sastoken_ttl",
        "keep_alive",
        "auto_connect",
        "connection_retry",
        "connection_retry_interval",
        "ensure_desired_properties",
    ]

    for kwarg in kwargs:
        if (kwarg not in valid_kwargs) or (exclude is not None and kwarg in exclude):
            raise TypeError("Unsupported keyword argument: '{}'".format(kwarg))


def _get_config_kwargs(**kwargs) -> Dict[str, Any]:
    """Get the subset of kwargs which pertain the config object"""
    valid_config_kwargs = [
        "server_verification_cert",
        "gateway_hostname",
        "websockets",
        "cipher",
        "product_info",
        "proxy_options",
        "keep_alive",
        "auto_connect",
        "connection_retry",
        "connection_retry_interval",
        "ensure_desired_properties",
    ]

    config_kwargs = {}
    for kwarg in kwargs:
        if kwarg in valid_config_kwargs:
            config_kwargs[kwarg] = kwargs[kwarg]
    return config_kwargs


def _form_sas_uri(hostname: str, device_id: str, module_id: Optional[str] = None) -> str:
    if module_id:
        return "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=hostname, device_id=device_id, module_id=module_id
        )
    else:
        return "{hostname}/devices/{device_id}".format(hostname=hostname, device_id=device_id)


def _extract_sas_uri_values(uri: str) -> Dict[str, Any]:
    d = {}
    items = uri.split("/")
    if len(items) != 3 and len(items) != 5:
        raise ValueError("Invalid SAS URI")
    if items[1] != "devices":
        raise ValueError("Cannot extract device id from SAS URI")
    if len(items) > 3 and items[3] != "modules":
        raise ValueError("Cannot extract module id from SAS URI")
    d["hostname"] = items[0]
    d["device_id"] = items[2]
    try:
        d["module_id"] = items[4]
    except IndexError:
        d["module_id"] = ""
    return d


# Receive Type constant defs
RECEIVE_TYPE_NONE_SET = "none_set"  # Type of receiving has not been set
RECEIVE_TYPE_HANDLER = "handler"  # Only use handlers for receive
RECEIVE_TYPE_API = "api"  # Only use APIs for receive


class AbstractIoTHubClient(abc.ABC):
    """A superclass representing a generic IoTHub client.
    This class needs to be extended for specific clients.
    """

    def __init__(self, mqtt_pipeline: MQTTPipeline, http_pipeline: HTTPPipeline) -> None:
        """Initializer for a generic client.

        :param mqtt_pipeline: The pipeline used to connect to the IoTHub endpoint.
        :type mqtt_pipeline: :class:`azure.iot.device.iothub.pipeline.MQTTPipeline`
        """
        self._mqtt_pipeline = mqtt_pipeline
        self._http_pipeline = http_pipeline

        self._inbox_manager = None  # this will be overridden in child class
        self._handler_manager = None  # this will be overridden in child class
        self._receive_type = RECEIVE_TYPE_NONE_SET
        self._client_lock = threading.Lock()

    def _on_connected(self) -> None:
        """Helper handler that is called upon an iothub pipeline connect"""
        logger.info("Connection State - Connected")
        if self._inbox_manager is not None:
            client_event_inbox = self._inbox_manager.get_client_event_inbox()
            # Only add a ClientEvent to the inbox if the Handler Manager is capable of dealing with it
            if self._handler_manager.handling_client_events:
                event = client_event.ClientEvent(client_event.CONNECTION_STATE_CHANGE)
                client_event_inbox.put(event)
            # Ensure that all handlers are running now that connection is re-established.
            self._handler_manager.ensure_running()

    def _on_disconnected(self) -> None:
        """Helper handler that is called upon an iothub pipeline disconnect"""
        logger.info("Connection State - Disconnected")
        if self._inbox_manager is not None:
            client_event_inbox = self._inbox_manager.get_client_event_inbox()
            # Only add a ClientEvent to the inbox if the Handler Manager is capable of dealing with it
            if self._handler_manager.handling_client_events:
                event = client_event.ClientEvent(client_event.CONNECTION_STATE_CHANGE)
                client_event_inbox.put(event)
            # Locally stored method requests on client are cleared.
            # They will be resent by IoTHub on reconnect.
            self._inbox_manager.clear_all_method_requests()
            logger.info("Cleared all pending method requests due to disconnect")

    def _on_new_sastoken_required(self) -> None:
        """Helper handler that is called upon the iothub pipeline needing new SAS token"""
        logger.info("New SasToken required from user")
        if self._inbox_manager is not None:
            client_event_inbox = self._inbox_manager.get_client_event_inbox()
            # Only add a ClientEvent to the inbox if the Handler Manager is capable of dealing with it
            if self._handler_manager.handling_client_events:
                event = client_event.ClientEvent(client_event.NEW_SASTOKEN_REQUIRED)
                client_event_inbox.put(event)

    def _on_background_exception(self, e: Exception) -> None:
        """Helper handler that is called upon an iothub pipeline background exception"""
        handle_exceptions.handle_background_exception(e)
        if self._inbox_manager is not None:
            client_event_inbox = self._inbox_manager.get_client_event_inbox()
            # Only add a ClientEvent to the inbox if the Handler Manager is capable of dealing with it
            if self._handler_manager.handling_client_events:
                event = client_event.ClientEvent(client_event.BACKGROUND_EXCEPTION, e)
                client_event_inbox.put(event)

    def _check_receive_mode_is_api(self) -> None:
        """Call this function first in EVERY receive API"""
        with self._client_lock:
            if self._receive_type is RECEIVE_TYPE_NONE_SET:
                # Lock the client to ONLY use receive APIs (no handlers)
                self._receive_type = RECEIVE_TYPE_API
            elif self._receive_type is RECEIVE_TYPE_HANDLER:
                raise exceptions.ClientError(
                    "Cannot use receive APIs - receive handler(s) have already been set"
                )
            else:
                pass

    def _check_receive_mode_is_handler(self) -> None:
        """Call this function first in EVERY handler setter"""
        with self._client_lock:
            if self._receive_type is RECEIVE_TYPE_NONE_SET:
                # Lock the client to ONLY use receive handlers (no APIs)
                self._receive_type = RECEIVE_TYPE_HANDLER
                # Set the inbox manager to use unified msg receives
                if self._inbox_manager is not None:
                    self._inbox_manager.use_unified_msg_mode = True
            elif self._receive_type is RECEIVE_TYPE_API:
                raise exceptions.ClientError(
                    "Cannot set receive handlers - receive APIs have already been used"
                )
            else:
                pass

    def _replace_user_supplied_sastoken(self, sastoken_str: str) -> None:
        """
        Replaces the pipeline's NonRenewableSasToken with a new one based on a provided
        sastoken string. Also does validation.
        This helper only updates the PipelineConfig - it does not reauthorize the connection.
        """
        if not isinstance(
            self._mqtt_pipeline.pipeline_configuration.sastoken, st.NonRenewableSasToken
        ):
            raise exceptions.ClientError(
                "Cannot update sastoken when client was not created with one"
            )
        # Create new SasToken
        try:
            new_token_o = st.NonRenewableSasToken(sastoken_str)
        except st.SasTokenError as e:
            new_err = ValueError("Invalid SasToken provided")
            new_err.__cause__ = e
            raise new_err
        # Extract values from SasToken
        vals = _extract_sas_uri_values(new_token_o.resource_uri)
        # Validate new token
        if type(self).__name__ == "IoTHubDeviceClient" and vals["module_id"]:
            raise ValueError("Provided SasToken is for a module")
        if type(self).__name__ == "IoTHubModuleClient" and not vals["module_id"]:
            raise ValueError("Provided SasToken is for a device")
        if self._mqtt_pipeline.pipeline_configuration.device_id != vals["device_id"]:
            raise ValueError("Provided SasToken does not match existing device id")
        if (
            vals["module_id"] != ""
            and self._mqtt_pipeline.pipeline_configuration.module_id != vals["module_id"]
        ):
            raise ValueError("Provided SasToken does not match existing module id")
        if self._mqtt_pipeline.pipeline_configuration.hostname != vals["hostname"]:
            raise ValueError("Provided SasToken does not match existing hostname")
        if new_token_o.expiry_time < int(time.time()):
            raise ValueError("Provided SasToken has already expired")
        # Set token
        # NOTE: We only need to set this on MQTT because this is a reference to the same object
        # that is stored in HTTP. The HTTP pipeline is updated implicitly.
        self._mqtt_pipeline.pipeline_configuration.sastoken = new_token_o

    @abc.abstractmethod
    def _generic_receive_handler_setter(
        self,
        handler_name: str,
        feature_name: str,
        new_handler: Optional[FunctionOrCoroutine[[Any], Any]],
    ) -> None:
        # Will be implemented differently in child classes, but define here for static analysis
        pass

    @classmethod
    def create_from_connection_string(cls, connection_string: str, **kwargs) -> Self:
        """
        Instantiate the client from a IoTHub device or module connection string.

        :param str connection_string: The connection string for the IoTHub you wish to connect to.

        :param str server_verification_cert: Configuration Option. The trusted certificate chain.
            Necessary when using connecting to an endpoint which has a non-standard root of trust,
            such as a protocol gateway.
        :param bool websockets: Configuration Option. Default is False. Set to true if using MQTT
            over websockets.
        :param cipher: Configuration Option. Cipher suite(s) for TLS/SSL, as a string in
            "OpenSSL cipher list format" or as a list of cipher suite strings.
        :type cipher: str or list(str)
        :param str product_info: Configuration Option. Default is empty string. The string contains
            arbitrary product info which is appended to the user agent string.
        :param proxy_options: Options for sending traffic through proxy servers.
        :type proxy_options: :class:`azure.iot.device.ProxyOptions`
        :param int sastoken_ttl: The time to live (in seconds) for the created SasToken used for
            authentication. Default is 3600 seconds (1 hour).
        :param int keep_alive: Maximum period in seconds between communications with the
            broker. If no other messages are being exchanged, this controls the
            rate at which the client will send ping messages to the broker.
            If not provided default value of 60 secs will be used.
        :param bool auto_connect: Automatically connect the client to IoTHub when a method is
            invoked which requires a connection to be established. (Default: True)
        :param bool connection_retry: Attempt to re-establish a dropped connection (Default: True)
        :param int connection_retry_interval: Interval, in seconds, between attempts to
            re-establish a dropped connection (Default: 10)
        :param bool ensure_desired_properties: Ensure the most recent desired properties patch has
            been received upon re-connections (Default:True)

        :raises: ValueError if given an invalid connection_string.
        :raises: TypeError if given an unsupported parameter.

        :returns: An instance of an IoTHub client that uses a connection string for authentication.
        """
        # TODO: Make this device/module specific and reject non-matching connection strings.

        # Ensure no invalid kwargs were passed by the user
        excluded_kwargs = ["gateway_hostname"]
        _validate_kwargs(exclude=excluded_kwargs, **kwargs)

        # Create SasToken
        connection_string_dict = cs.ConnectionString(connection_string)
        if connection_string_dict.get(cs.X509) is not None:
            raise ValueError(
                "Use the .create_from_x509_certificate() method instead when using X509 certificates"
            )
        uri = _form_sas_uri(
            hostname=connection_string_dict[cs.HOST_NAME],
            device_id=connection_string_dict[cs.DEVICE_ID],
            module_id=connection_string_dict.get(cs.MODULE_ID),
        )
        signing_mechanism = auth.SymmetricKeySigningMechanism(
            key=connection_string_dict[cs.SHARED_ACCESS_KEY]
        )
        token_ttl = kwargs.get("sastoken_ttl", 3600)
        try:
            sastoken = st.RenewableSasToken(uri, signing_mechanism, ttl=token_ttl)
        except st.SasTokenError as e:
            new_err = ValueError("Could not create a SasToken using provided values")
            new_err.__cause__ = e
            raise new_err
        # Pipeline Config setup
        config_kwargs = _get_config_kwargs(**kwargs)
        pipeline_configuration = pipeline.IoTHubPipelineConfig(
            device_id=connection_string_dict[cs.DEVICE_ID],
            module_id=connection_string_dict.get(cs.MODULE_ID),
            hostname=connection_string_dict[cs.HOST_NAME],
            gateway_hostname=connection_string_dict.get(cs.GATEWAY_HOST_NAME),
            sastoken=sastoken,
            **config_kwargs,
        )
        if cls.__name__ == "IoTHubDeviceClient":
            pipeline_configuration.blob_upload = True

        # Pipeline setup
        http_pipeline = pipeline.HTTPPipeline(pipeline_configuration)
        mqtt_pipeline = pipeline.MQTTPipeline(pipeline_configuration)

        return cls(mqtt_pipeline, http_pipeline)

    @classmethod
    def create_from_sastoken(cls, sastoken: str, **kwargs: Dict[str, Any]) -> Self:
        """Instantiate the client from a pre-created SAS Token string

        :param str sastoken: The SAS Token string

        :param str server_verification_cert: Configuration Option. The trusted certificate chain.
            Necessary when using connecting to an endpoint which has a non-standard root of trust,
            such as a protocol gateway.
        :param str gateway_hostname: Configuration Option. The gateway hostname for the gateway
            device.
        :param bool websockets: Configuration Option. Default is False. Set to true if using MQTT
            over websockets.
        :param cipher: Configuration Option. Cipher suite(s) for TLS/SSL, as a string in
            "OpenSSL cipher list format" or as a list of cipher suite strings.
        :type cipher: str or list(str)
        :param str product_info: Configuration Option. Default is empty string. The string contains
            arbitrary product info which is appended to the user agent string.
        :param proxy_options: Options for sending traffic through proxy servers.
        :type proxy_options: :class:`azure.iot.device.ProxyOptions`
        :param int keep_alive: Maximum period in seconds between communications with the
            broker. If no other messages are being exchanged, this controls the
            rate at which the client will send ping messages to the broker.
            If not provided default value of 60 secs will be used.
        :param bool auto_connect: Automatically connect the client to IoTHub when a method is
            invoked which requires a connection to be established. (Default: True)
        :param bool connection_retry: Attempt to re-establish a dropped connection (Default: True)
        :param int connection_retry_interval: Interval, in seconds, between attempts to
            re-establish a dropped connection (Default: 10)
        :param bool ensure_desired_properties: Ensure the most recent desired properties patch has
            been received upon re-connections (Default:True)

        :raises: TypeError if given an unsupported parameter.
        :raises: ValueError if the sastoken parameter is invalid.
        """
        # Ensure no invalid kwargs were passed by the user
        excluded_kwargs = ["sastoken_ttl"]
        _validate_kwargs(exclude=excluded_kwargs, **kwargs)

        # Create SasToken object from string
        try:
            sastoken_o = st.NonRenewableSasToken(sastoken)
        except st.SasTokenError as e:
            new_err = ValueError("Invalid SasToken provided")
            new_err.__cause__ = e
            raise new_err
        # Extract values from SasToken
        vals = _extract_sas_uri_values(sastoken_o.resource_uri)
        if cls.__name__ == "IoTHubDeviceClient" and vals["module_id"]:
            raise ValueError("Provided SasToken is for a module")
        if cls.__name__ == "IoTHubModuleClient" and not vals["module_id"]:
            raise ValueError("Provided SasToken is for a device")
        if sastoken_o.expiry_time < int(time.time()):
            raise ValueError("Provided SasToken has already expired")
        # Pipeline Config setup
        config_kwargs = _get_config_kwargs(**kwargs)
        pipeline_configuration = pipeline.IoTHubPipelineConfig(
            device_id=vals["device_id"],
            module_id=vals["module_id"],
            hostname=vals["hostname"],
            sastoken=sastoken_o,
            **config_kwargs,
        )
        if cls.__name__ == "IoTHubDeviceClient":
            pipeline_configuration.blob_upload = True  # Blob Upload is a feature on Device Clients

        # Pipeline setup
        http_pipeline = pipeline.HTTPPipeline(pipeline_configuration)
        mqtt_pipeline = pipeline.MQTTPipeline(pipeline_configuration)

        return cls(mqtt_pipeline, http_pipeline)

    @abc.abstractmethod
    def shutdown(self) -> None:
        pass

    @abc.abstractmethod
    def connect(self) -> None:
        pass

    @abc.abstractmethod
    def disconnect(self) -> None:
        pass

    @abc.abstractmethod
    def update_sastoken(self, sastoken: str) -> None:
        pass

    @abc.abstractmethod
    def send_message(self, message: Union[Message, str]) -> None:
        pass

    @abc.abstractmethod
    def receive_method_request(self, method_name: Optional[str] = None) -> None:
        pass

    @abc.abstractmethod
    def send_method_response(self, method_response: MethodResponse) -> None:
        pass

    @abc.abstractmethod
    def get_twin(self) -> Twin:
        pass

    @abc.abstractmethod
    def patch_twin_reported_properties(self, reported_properties_patch: TwinPatch) -> None:
        pass

    @abc.abstractmethod
    def receive_twin_desired_properties_patch(self) -> TwinPatch:
        pass

    @property
    def connected(self) -> bool:
        """
        Read-only property to indicate if the transport is connected or not.
        """
        return self._mqtt_pipeline.connected

    @property
    def on_connection_state_change(self) -> FunctionOrCoroutine[[None], None]:
        """The handler function or coroutine that will be called when the connection state changes.

        The function or coroutine definition should take no positional arguments.
        """
        if self._handler_manager is not None:
            return self._handler_manager.on_connection_state_change

    @on_connection_state_change.setter
    def on_connection_state_change(self, value: FunctionOrCoroutine[[None], None]) -> None:
        if self._handler_manager is not None:
            self._handler_manager.on_connection_state_change = value

    @property
    def on_new_sastoken_required(self) -> FunctionOrCoroutine[[None], None]:
        """The handler function or coroutine that will be called when the client requires a new
        SAS token. This will happen approximately 2 minutes before the SAS Token expires.
        On Windows platforms, if the lifespan exceeds approximately 49 days, a new token will
        be required after those 49 days regardless of how long the SAS lifespan is.

        Note that this handler is ONLY necessary when using a client created via the
        .create_from_sastoken() method.

        The new token can be provided in your function or coroutine via use of the client's
        .update_sastoken() method.

        The function or coroutine definition should take no positional arguments.
        """
        if self._handler_manager is not None:
            return self._handler_manager.on_new_sastoken_required

    @on_new_sastoken_required.setter
    def on_new_sastoken_required(self, value: FunctionOrCoroutine[[None], None]) -> None:
        if self._handler_manager is not None:
            self._handler_manager.on_new_sastoken_required = value

    @property
    def on_background_exception(self) -> FunctionOrCoroutine[[Exception], None]:
        """The handler function or coroutine will be called when a background exception occurs.

        The function or coroutine definition should take one positional argument (the exception
        object)"""
        if self._handler_manager is not None:
            return self._handler_manager.on_background_exception

    @on_background_exception.setter
    def on_background_exception(self, value: FunctionOrCoroutine[[Exception], None]) -> None:
        if self._handler_manager is not None:
            self._handler_manager.on_background_exception = value

    @abc.abstractproperty
    def on_message_received(self) -> FunctionOrCoroutine[[Message], None]:
        # Defined below on AbstractIoTHubDeviceClient / AbstractIoTHubModuleClient
        pass

    @property
    def on_method_request_received(self) -> FunctionOrCoroutine[[MethodRequest], None]:
        """The handler function or coroutine that will be called when a method request is received.

        Remember to acknowledge the method request in your function or coroutine via use of the
        client's .send_method_response() method.

        The function or coroutine definition should take one positional argument (the
        :class:`azure.iot.device.MethodRequest` object)"""
        if self._handler_manager is not None:
            return self._handler_manager.on_method_request_received

    @on_method_request_received.setter
    def on_method_request_received(self, value: FunctionOrCoroutine[[MethodRequest], None]) -> None:
        self._generic_receive_handler_setter(
            "on_method_request_received", pipeline_constant.METHODS, value
        )

    @property
    def on_twin_desired_properties_patch_received(self) -> FunctionOrCoroutine[[TwinPatch], None]:
        """The handler function or coroutine that will be called when a twin desired properties
        patch is received.

        The function or coroutine definition should take one positional argument (the twin patch
        in the form of a JSON dictionary object)"""
        if self._handler_manager is not None:
            return self._handler_manager.on_twin_desired_properties_patch_received

    @on_twin_desired_properties_patch_received.setter
    def on_twin_desired_properties_patch_received(
        self, value: FunctionOrCoroutine[[TwinPatch], None]
    ):
        self._generic_receive_handler_setter(
            "on_twin_desired_properties_patch_received", pipeline_constant.TWIN_PATCHES, value
        )


class AbstractIoTHubDeviceClient(AbstractIoTHubClient):
    @classmethod
    def create_from_x509_certificate(
        cls, x509: X509, hostname: str, device_id: str, **kwargs
    ) -> Self:
        """
        Instantiate a client using X509 certificate authentication.

        :param str hostname: Host running the IotHub.
            Can be found in the Azure portal in the Overview tab as the string hostname.
        :param x509: The complete x509 certificate object.
            To use the certificate the enrollment object needs to contain cert
            (either the root certificate or one of the intermediate CA certificates).
            If the cert comes from a CER file, it needs to be base64 encoded.
        :type x509: :class:`azure.iot.device.X509`
        :param str device_id: The ID used to uniquely identify a device in the IoTHub

        :param str server_verification_cert: Configuration Option. The trusted certificate chain.
            Necessary when using connecting to an endpoint which has a non-standard root of trust,
            such as a protocol gateway.
        :param str gateway_hostname: Configuration Option. The gateway hostname for the gateway
            device.
        :param bool websockets: Configuration Option. Default is False. Set to true if using MQTT
            over websockets.
        :param cipher: Configuration Option. Cipher suite(s) for TLS/SSL, as a string in
            "OpenSSL cipher list format" or as a list of cipher suite strings.
        :type cipher: str or list(str)
        :param str product_info: Configuration Option. Default is empty string. The string contains
            arbitrary product info which is appended to the user agent string.
        :param proxy_options: Options for sending traffic through proxy servers.
        :type proxy_options: :class:`azure.iot.device.ProxyOptions`
        :param int keep_alive: Maximum period in seconds between communications with the
            broker. If no other messages are being exchanged, this controls the
            rate at which the client will send ping messages to the broker.
            If not provided default value of 60 secs will be used.
        :param bool auto_connect: Automatically connect the client to IoTHub when a method is
            invoked which requires a connection to be established. (Default: True)
        :param bool connection_retry: Attempt to re-establish a dropped connection (Default: True)
        :param int connection_retry_interval: Interval, in seconds, between attempts to
            re-establish a dropped connection (Default: 10)
        :param bool ensure_desired_properties: Ensure the most recent desired properties patch has
            been received upon re-connections (Default:True)

        :raises: TypeError if given an unsupported parameter.

        :returns: An instance of an IoTHub client that uses an X509 certificate for authentication.
        """
        # Ensure no invalid kwargs were passed by the user
        excluded_kwargs = ["sastoken_ttl"]
        _validate_kwargs(exclude=excluded_kwargs, **kwargs)

        # Pipeline Config setup
        config_kwargs = _get_config_kwargs(**kwargs)
        pipeline_configuration = pipeline.IoTHubPipelineConfig(
            device_id=device_id, hostname=hostname, x509=x509, **config_kwargs
        )
        pipeline_configuration.blob_upload = True  # Blob Upload is a feature on Device Clients

        # Pipeline setup
        http_pipeline = pipeline.HTTPPipeline(pipeline_configuration)
        mqtt_pipeline = pipeline.MQTTPipeline(pipeline_configuration)

        return cls(mqtt_pipeline, http_pipeline)

    @classmethod
    def create_from_symmetric_key(
        cls, symmetric_key: str, hostname: str, device_id: str, **kwargs
    ) -> Self:
        """
        Instantiate a client using symmetric key authentication.

        :param symmetric_key: The symmetric key.
        :param str hostname: Host running the IotHub.
            Can be found in the Azure portal in the Overview tab as the string hostname.
        :param device_id: The device ID

        :param str server_verification_cert: Configuration Option. The trusted certificate chain.
            Necessary when using connecting to an endpoint which has a non-standard root of trust,
            such as a protocol gateway.
        :param str gateway_hostname: Configuration Option. The gateway hostname for the gateway
            device.
        :param bool websockets: Configuration Option. Default is False. Set to true if using MQTT
            over websockets.
        :param cipher: Configuration Option. Cipher suite(s) for TLS/SSL, as a string in
            "OpenSSL cipher list format" or as a list of cipher suite strings.
        :type cipher: str or list(str)
        :param str product_info: Configuration Option. Default is empty string. The string contains
            arbitrary product info which is appended to the user agent string.
        :param proxy_options: Options for sending traffic through proxy servers.
        :type proxy_options: :class:`azure.iot.device.ProxyOptions`
        :param int sastoken_ttl: The time to live (in seconds) for the created SasToken used for
            authentication. Default is 3600 seconds (1 hour)
        :param int keep_alive: Maximum period in seconds between communications with the
            broker. If no other messages are being exchanged, this controls the
            rate at which the client will send ping messages to the broker.
            If not provided default value of 60 secs will be used.
        :param bool auto_connect: Automatically connect the client to IoTHub when a method is
            invoked which requires a connection to be established. (Default: True)
        :param bool connection_retry: Attempt to re-establish a dropped connection (Default: True)
        :param int connection_retry_interval: Interval, in seconds, between attempts to
            re-establish a dropped connection (Default: 10)
        :param bool ensure_desired_properties: Ensure the most recent desired properties patch has
            been received upon re-connections (Default:True)

        :raises: TypeError if given an unsupported parameter.
        :raises: ValueError if the provided parameters are invalid.

        :return: An instance of an IoTHub client that uses a symmetric key for authentication.
        """
        # Ensure no invalid kwargs were passed by the user
        _validate_kwargs(**kwargs)

        # Create SasToken
        uri = _form_sas_uri(hostname=hostname, device_id=device_id)
        signing_mechanism = auth.SymmetricKeySigningMechanism(key=symmetric_key)
        token_ttl = kwargs.get("sastoken_ttl", 3600)
        try:
            sastoken = st.RenewableSasToken(uri, signing_mechanism, ttl=token_ttl)
        except st.SasTokenError as e:
            new_err = ValueError("Could not create a SasToken using provided values")
            new_err.__cause__ = e
            raise new_err

        # Pipeline Config setup
        config_kwargs = _get_config_kwargs(**kwargs)
        pipeline_configuration = pipeline.IoTHubPipelineConfig(
            device_id=device_id, hostname=hostname, sastoken=sastoken, **config_kwargs
        )
        pipeline_configuration.blob_upload = True  # Blob Upload is a feature on Device Clients

        # Pipeline setup
        http_pipeline = pipeline.HTTPPipeline(pipeline_configuration)
        mqtt_pipeline = pipeline.MQTTPipeline(pipeline_configuration)

        return cls(mqtt_pipeline, http_pipeline)

    @abc.abstractmethod
    def receive_message(self) -> Message:
        pass

    @abc.abstractmethod
    def get_storage_info_for_blob(self, blob_name: str) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def notify_blob_upload_status(
        self, correlation_id: str, is_success: bool, status_code: int, status_description: str
    ) -> None:
        pass

    @property
    def on_message_received(self) -> FunctionOrCoroutine[[Message], None]:
        """The handler function or coroutine that will be called when a message is received.

        The function or coroutine definition should take one positional argument (the
        :class:`azure.iot.device.Message` object)"""
        if self._handler_manager is not None:
            return self._handler_manager.on_message_received

    @on_message_received.setter
    def on_message_received(self, value: FunctionOrCoroutine[[Message], None]):
        self._generic_receive_handler_setter(
            "on_message_received", pipeline_constant.C2D_MSG, value
        )


class AbstractIoTHubModuleClient(AbstractIoTHubClient):
    @classmethod
    def create_from_edge_environment(cls, **kwargs) -> Self:
        """
        Instantiate the client from the IoT Edge environment.

        This method can only be run from inside an IoT Edge container, or in a debugging
        environment configured for Edge development (e.g. Visual Studio, Visual Studio Code)

        :param bool websockets: Configuration Option. Default is False. Set to true if using MQTT
            over websockets.
        :param cipher: Configuration Option. Cipher suite(s) for TLS/SSL, as a string in
            "OpenSSL cipher list format" or as a list of cipher suite strings.
        :type cipher: str or list(str)
        :param str product_info: Configuration Option. Default is empty string. The string contains
            arbitrary product info which is appended to the user agent string.
        :param proxy_options: Options for sending traffic through proxy servers.
        :type proxy_options: :class:`azure.iot.device.ProxyOptions`
        :param int sastoken_ttl: The time to live (in seconds) for the created SasToken used for
            authentication. Default is 3600 seconds (1 hour)
        :param int keep_alive: Maximum period in seconds between communications with the
            broker. If no other messages are being exchanged, this controls the
            rate at which the client will send ping messages to the broker.
            If not provided default value of 60 secs will be used.
        :param bool auto_connect: Automatically connect the client to IoTHub when a method is
            invoked which requires a connection to be established. (Default: True)
        :param bool connection_retry: Attempt to re-establish a dropped connection (Default: True)
        :param int connection_retry_interval: Interval, in seconds, between attempts to
            re-establish a dropped connection (Default: 10)

        :raises: OSError if the IoT Edge container is not configured correctly.
        :raises: ValueError if debug variables are invalid.
        :raises: TypeError if given an unsupported parameter.

        :returns: An instance of an IoTHub client that uses the IoT Edge environment for
            authentication.
        """
        # Ensure no invalid kwargs were passed by the user
        excluded_kwargs = ["server_verification_cert", "gateway_hostname"]
        _validate_kwargs(exclude=excluded_kwargs, **kwargs)

        # First try the regular Edge container variables
        try:
            hostname = os.environ["IOTEDGE_IOTHUBHOSTNAME"]
            device_id = os.environ["IOTEDGE_DEVICEID"]
            module_id = os.environ["IOTEDGE_MODULEID"]
            gateway_hostname = os.environ["IOTEDGE_GATEWAYHOSTNAME"]
            module_generation_id = os.environ["IOTEDGE_MODULEGENERATIONID"]
            workload_uri = os.environ["IOTEDGE_WORKLOADURI"]
            api_version = os.environ["IOTEDGE_APIVERSION"]
        except KeyError:
            # As a fallback, try the Edge local dev variables for debugging.
            # These variables are set by VS/VS Code in order to allow debugging
            # of Edge application code in a non-Edge dev environment.
            try:
                connection_string = os.environ["EdgeHubConnectionString"]
                ca_cert_filepath = os.environ["EdgeModuleCACertificateFile"]
            except KeyError as e:
                new_err = OSError("IoT Edge environment not configured correctly")
                new_err.__cause__ = e
                raise new_err

            # Read the certificate file to pass it on as a string
            # TODO: variant server_verification_cert file vs data object that would remove the need for this file open
            try:
                with io.open(ca_cert_filepath, mode="r") as ca_cert_file:
                    server_verification_cert = ca_cert_file.read()
            except FileNotFoundError:
                raise
            except OSError as e:
                raise ValueError("Invalid CA certificate file") from e

            # Extract config values from connection string
            connection_string = cs.ConnectionString(connection_string)
            try:
                device_id = connection_string[cs.DEVICE_ID]
                module_id = connection_string[cs.MODULE_ID]
                hostname = connection_string[cs.HOST_NAME]
                gateway_hostname = connection_string[cs.GATEWAY_HOST_NAME]
            except KeyError:
                raise ValueError("Invalid Connection String")

            # Use Symmetric Key authentication for local dev experience.
            signing_mechanism = auth.SymmetricKeySigningMechanism(
                key=connection_string[cs.SHARED_ACCESS_KEY]
            )

        else:
            # Use an HSM for authentication in the general case
            hsm = edge_hsm.IoTEdgeHsm(
                module_id=module_id,
                generation_id=module_generation_id,
                workload_uri=workload_uri,
                api_version=api_version,
            )
            try:
                server_verification_cert = hsm.get_certificate()
            except edge_hsm.IoTEdgeError as e:
                new_err = OSError("Unexpected failure in IoTEdge")
                new_err.__cause__ = e
                raise new_err
            signing_mechanism = hsm

        # Create SasToken
        uri = _form_sas_uri(hostname=hostname, device_id=device_id, module_id=module_id)
        token_ttl = kwargs.get("sastoken_ttl", 3600)
        try:
            sastoken = st.RenewableSasToken(uri, signing_mechanism, ttl=token_ttl)
        except st.SasTokenError as e:
            new_val_err = ValueError(
                "Could not create a SasToken using the values provided, or in the Edge environment"
            )
            new_val_err.__cause__ = e
            raise new_val_err

        # Pipeline Config setup
        config_kwargs = _get_config_kwargs(**kwargs)
        pipeline_configuration = pipeline.IoTHubPipelineConfig(
            device_id=device_id,
            module_id=module_id,
            hostname=hostname,
            gateway_hostname=gateway_hostname,
            sastoken=sastoken,
            server_verification_cert=server_verification_cert,
            **config_kwargs,
        )
        pipeline_configuration.method_invoke = (
            True  # Method Invoke is allowed on modules created from edge environment
        )

        # Pipeline setup
        http_pipeline = pipeline.HTTPPipeline(pipeline_configuration)
        mqtt_pipeline = pipeline.MQTTPipeline(pipeline_configuration)

        return cls(mqtt_pipeline, http_pipeline)

    @classmethod
    def create_from_x509_certificate(
        cls, x509: X509, hostname: str, device_id: str, module_id: str, **kwargs
    ) -> Self:
        """
        Instantiate a client using X509 certificate authentication.

        :param str hostname: Host running the IotHub.
            Can be found in the Azure portal in the Overview tab as the string hostname.
        :param x509: The complete x509 certificate object.
            To use the certificate the enrollment object needs to contain cert
            (either the root certificate or one of the intermediate CA certificates).
            If the cert comes from a CER file, it needs to be base64 encoded.
        :type x509: :class:`azure.iot.device.X509`
        :param str device_id: The ID used to uniquely identify a device in the IoTHub
        :param str module_id: The ID used to uniquely identify a module on a device on the IoTHub.

        :param str server_verification_cert: Configuration Option. The trusted certificate chain.
            Necessary when using connecting to an endpoint which has a non-standard root of trust,
            such as a protocol gateway.
        :param str gateway_hostname: Configuration Option. The gateway hostname for the gateway
            device.
        :param bool websockets: Configuration Option. Default is False. Set to true if using MQTT
            over websockets.
        :param cipher: Configuration Option. Cipher suite(s) for TLS/SSL, as a string in
            "OpenSSL cipher list format" or as a list of cipher suite strings.
        :type cipher: str or list(str)
        :param str product_info: Configuration Option. Default is empty string. The string contains
            arbitrary product info which is appended to the user agent string.
        :param proxy_options: Options for sending traffic through proxy servers.
        :type proxy_options: :class:`azure.iot.device.ProxyOptions`
        :param int keep_alive: Maximum period in seconds between communications with the
            broker. If no other messages are being exchanged, this controls the
            rate at which the client will send ping messages to the broker.
            If not provided default value of 60 secs will be used.
        :param bool auto_connect: Automatically connect the client to IoTHub when a method is
            invoked which requires a connection to be established. (Default: True)
        :param bool connection_retry: Attempt to re-establish a dropped connection (Default: True)
        :param int connection_retry_interval: Interval, in seconds, between attempts to
            re-establish a dropped connection (Default: 10)
        :param bool ensure_desired_properties: Ensure the most recent desired properties patch has
            been received upon re-connections (Default:True)

        :raises: TypeError if given an unsupported parameter.

        :returns: An instance of an IoTHub client that uses an X509 certificate for authentication.
        """
        # Ensure no invalid kwargs were passed by the user
        excluded_kwargs = ["sastoken_ttl"]
        _validate_kwargs(exclude=excluded_kwargs, **kwargs)

        # Pipeline Config setup
        config_kwargs = _get_config_kwargs(**kwargs)
        pipeline_configuration = pipeline.IoTHubPipelineConfig(
            device_id=device_id, module_id=module_id, hostname=hostname, x509=x509, **config_kwargs
        )

        # Pipeline setup
        http_pipeline = pipeline.HTTPPipeline(pipeline_configuration)
        mqtt_pipeline = pipeline.MQTTPipeline(pipeline_configuration)
        return cls(mqtt_pipeline, http_pipeline)

    @abc.abstractmethod
    def send_message_to_output(self, message: Union[Message, str], output_name: str) -> None:
        pass

    @abc.abstractmethod
    def receive_message_on_input(self, input_name: str) -> Message:
        pass

    @abc.abstractmethod
    def invoke_method(
        self, method_params: dict, device_id: str, module_id: Optional[str] = None
    ) -> None:
        pass

    @property
    def on_message_received(self) -> FunctionOrCoroutine[[Message], Any]:
        """The handler function or coroutine that will be called when an input message is received.

        The function definition or coroutine should take one positional argument (the
        :class:`azure.iot.device.Message` object)"""
        if self._handler_manager is not None:
            return self._handler_manager.on_message_received

    @on_message_received.setter
    def on_message_received(self, value: FunctionOrCoroutine[[Message], Any]) -> None:
        self._generic_receive_handler_setter(
            "on_message_received", pipeline_constant.INPUT_MSG, value
        )
