# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains abstract classes for the various clients of the Azure IoT Hub Device SDK
"""

import six
import abc
import logging
import threading
import os
import io
from . import pipeline
from azure.iot.device.common.auth import connection_string as cs
from azure.iot.device.common.auth import sastoken as st
from azure.iot.device import exceptions
from azure.iot.device.common import auth
from . import edge_hsm

logger = logging.getLogger(__name__)


def _validate_kwargs(exclude=[], **kwargs):
    """Helper function to validate user provided kwargs.
    Raises TypeError if an invalid option has been provided"""
    valid_kwargs = [
        "product_info",
        "websockets",
        "cipher",
        "server_verification_cert",
        "proxy_options",
        "sastoken_ttl",
        "keep_alive",
    ]

    for kwarg in kwargs:
        if (kwarg not in valid_kwargs) or (kwarg in exclude):
            raise TypeError("Unsupported keyword argument: '{}'".format(kwarg))


def _get_config_kwargs(**kwargs):
    """Get the subset of kwargs which pertain the config object"""
    valid_config_kwargs = [
        "product_info",
        "websockets",
        "cipher",
        "server_verification_cert",
        "proxy_options",
        "keep_alive",
    ]

    config_kwargs = {}
    for kwarg in kwargs:
        if kwarg in valid_config_kwargs:
            config_kwargs[kwarg] = kwargs[kwarg]
    return config_kwargs


def _form_sas_uri(hostname, device_id, module_id=None):
    if module_id:
        return "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=hostname, device_id=device_id, module_id=module_id
        )
    else:
        return "{hostname}/devices/{device_id}".format(hostname=hostname, device_id=device_id)


# Receive Type constant defs
RECEIVE_TYPE_NONE_SET = "none_set"  # Type of receiving has not been set
RECEIVE_TYPE_HANDLER = "handler"  # Only use handlers for receive
RECEIVE_TYPE_API = "api"  # Only use APIs for receive


@six.add_metaclass(abc.ABCMeta)
class AbstractIoTHubClient(object):
    """ A superclass representing a generic IoTHub client.
    This class needs to be extended for specific clients.
    """

    def __init__(self, mqtt_pipeline, http_pipeline):
        """Initializer for a generic client.

        :param mqtt_pipeline: The pipeline used to connect to the IoTHub endpoint.
        :type mqtt_pipeline: :class:`azure.iot.device.iothub.pipeline.MQTTPipeline`
        """
        self._mqtt_pipeline = mqtt_pipeline
        self._http_pipeline = http_pipeline

        self._inbox_manager = None  # this will be overriden in child class
        self._receive_type = RECEIVE_TYPE_NONE_SET
        self._client_lock = threading.Lock()

    def _check_receive_mode_is_api(self):
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

    def _check_receive_mode_is_handler(self):
        """Call this function first in EVERY handler setter"""
        with self._client_lock:
            if self._receive_type is RECEIVE_TYPE_NONE_SET:
                # Lock the client to ONLY use receive handlers (no APIs)
                self._receive_type = RECEIVE_TYPE_HANDLER
                # Set the inbox manager to use unified msg receives
                self._inbox_manager.use_unified_msg_mode = True
            elif self._receive_type is RECEIVE_TYPE_API:
                raise exceptions.ClientError(
                    "Cannot set receive handlers - receive APIs have already been used"
                )
            else:
                pass

    @classmethod
    def create_from_connection_string(cls, connection_string, **kwargs):
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
            authentication. Default is 3600 seconds (1 hour)
        :param int keepalive: Maximum period in seconds between communications with the
        broker. If no other messages are being exchanged, this controls the
        rate at which the client will send ping messages to the broker.
        If not provided default value of 60 secs will be used.

        :raises: ValueError if given an invalid connection_string.
        :raises: TypeError if given an unsupported parameter.

        :returns: An instance of an IoTHub client that uses a connection string for authentication.
        """
        # TODO: Make this device/module specific and reject non-matching connection strings.

        # Ensure no invalid kwargs were passed by the user
        _validate_kwargs(**kwargs)

        # Create SasToken
        connection_string = cs.ConnectionString(connection_string)
        uri = _form_sas_uri(
            hostname=connection_string[cs.HOST_NAME],
            device_id=connection_string[cs.DEVICE_ID],
            module_id=connection_string.get(cs.MODULE_ID),
        )
        signing_mechanism = auth.SymmetricKeySigningMechanism(
            key=connection_string[cs.SHARED_ACCESS_KEY]
        )
        token_ttl = kwargs.get("sastoken_ttl", 3600)
        try:
            sastoken = st.SasToken(uri, signing_mechanism, ttl=token_ttl)
        except st.SasTokenError as e:
            new_err = ValueError("Could not create a SasToken using provided values")
            new_err.__cause__ = e
            raise new_err
        # Pipeline Config setup
        config_kwargs = _get_config_kwargs(**kwargs)
        pipeline_configuration = pipeline.IoTHubPipelineConfig(
            device_id=connection_string[cs.DEVICE_ID],
            module_id=connection_string.get(cs.MODULE_ID),
            hostname=connection_string[cs.HOST_NAME],
            gateway_hostname=connection_string.get(cs.GATEWAY_HOST_NAME),
            sastoken=sastoken,
            **config_kwargs
        )
        if cls.__name__ == "IoTHubDeviceClient":
            pipeline_configuration.blob_upload = True

        # Pipeline setup
        http_pipeline = pipeline.HTTPPipeline(pipeline_configuration)
        mqtt_pipeline = pipeline.MQTTPipeline(pipeline_configuration)

        return cls(mqtt_pipeline, http_pipeline)

    @abc.abstractmethod
    def connect(self):
        pass

    @abc.abstractmethod
    def disconnect(self):
        pass

    @abc.abstractmethod
    def send_message(self, message):
        pass

    @abc.abstractmethod
    def receive_method_request(self, method_name=None):
        pass

    @abc.abstractmethod
    def send_method_response(self, method_request, payload, status):
        pass

    @abc.abstractmethod
    def get_twin(self):
        pass

    @abc.abstractmethod
    def patch_twin_reported_properties(self, reported_properties_patch):
        pass

    @abc.abstractmethod
    def receive_twin_desired_properties_patch(self):
        pass

    @property
    def connected(self):
        """
        Read-only property to indicate if the transport is connected or not.
        """
        return self._mqtt_pipeline.connected

    @abc.abstractproperty
    def on_message_received(self):
        pass

    @abc.abstractproperty
    def on_method_request_received(self):
        pass

    @abc.abstractproperty
    def on_twin_desired_properties_patch_received(self):
        pass


@six.add_metaclass(abc.ABCMeta)
class AbstractIoTHubDeviceClient(AbstractIoTHubClient):
    @classmethod
    def create_from_x509_certificate(cls, x509, hostname, device_id, **kwargs):
        """
        Instantiate a client which using X509 certificate authentication.

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
        :param bool websockets: Configuration Option. Default is False. Set to true if using MQTT
            over websockets.
        :param cipher: Configuration Option. Cipher suite(s) for TLS/SSL, as a string in
            "OpenSSL cipher list format" or as a list of cipher suite strings.
        :type cipher: str or list(str)
        :param str product_info: Configuration Option. Default is empty string. The string contains
            arbitrary product info which is appended to the user agent string.
        :param proxy_options: Options for sending traffic through proxy servers.
        :type proxy_options: :class:`azure.iot.device.ProxyOptions`
        :param int keepalive: Maximum period in seconds between communications with the
        broker. If no other messages are being exchanged, this controls the
        rate at which the client will send ping messages to the broker.
        If not provided default value of 60 secs will be used.

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
    def create_from_symmetric_key(cls, symmetric_key, hostname, device_id, **kwargs):
        """
        Instantiate a client using symmetric key authentication.

        :param symmetric_key: The symmetric key.
        :param str hostname: Host running the IotHub.
            Can be found in the Azure portal in the Overview tab as the string hostname.
        :param device_id: The device ID

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
            authentication. Default is 3600 seconds (1 hour)
        :param int keepalive: Maximum period in seconds between communications with the
        broker. If no other messages are being exchanged, this controls the
        rate at which the client will send ping messages to the broker.
        If not provided default value of 60 secs will be used.

        :raises: TypeError if given an unsupported parameter.

        :return: An instance of an IoTHub client that uses a symmetric key for authentication.
        """
        # Ensure no invalid kwargs were passed by the user
        _validate_kwargs(**kwargs)

        # Create SasToken
        uri = _form_sas_uri(hostname=hostname, device_id=device_id)
        signing_mechanism = auth.SymmetricKeySigningMechanism(key=symmetric_key)
        token_ttl = kwargs.get("sastoken_ttl", 3600)
        try:
            sastoken = st.SasToken(uri, signing_mechanism, ttl=token_ttl)
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
    def receive_message(self):
        pass


@six.add_metaclass(abc.ABCMeta)
class AbstractIoTHubModuleClient(AbstractIoTHubClient):
    @classmethod
    def create_from_edge_environment(cls, **kwargs):
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
        :param int keepalive: Maximum period in seconds between communications with the
        broker. If no other messages are being exchanged, this controls the
        rate at which the client will send ping messages to the broker.
        If not provided default value of 60 secs will be used.

        :raises: OSError if the IoT Edge container is not configured correctly.
        :raises: ValueError if debug variables are invalid.
        :raises: TypeError if given an unsupported parameter.

        :returns: An instance of an IoTHub client that uses the IoT Edge environment for
            authentication.
        """
        # Ensure no invalid kwargs were passed by the user
        excluded_kwargs = ["server_verification_cert"]
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
            # TODO: variant server_verification_cert file vs data object that would remove the need for this fopen
            try:
                with io.open(ca_cert_filepath, mode="r") as ca_cert_file:
                    server_verification_cert = ca_cert_file.read()
            except (OSError, IOError) as e:
                # In Python 2, a non-existent file raises IOError, and an invalid file raises an IOError.
                # In Python 3, a non-existent file raises FileNotFoundError, and an invalid file raises an OSError.
                # However, FileNotFoundError inherits from OSError, and IOError has been turned into an alias for OSError,
                # thus we can catch the errors for both versions in this block.
                # Unfortunately, we can't distinguish cause of error from error type, so the raised ValueError has a generic
                # message. If, in the future, we want to add detail, this could be accomplished by inspecting the e.errno
                # attribute
                new_err = ValueError("Invalid CA certificate file")
                new_err.__cause__ = e
                raise new_err

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
            sastoken = st.SasToken(uri, signing_mechanism, ttl=token_ttl)
        except st.SasTokenError as e:
            new_err = ValueError(
                "Could not create a SasToken using the values provided, or in the Edge environment"
            )
            new_err.__cause__ = e
            raise new_err

        # Pipeline Config setup
        config_kwargs = _get_config_kwargs(**kwargs)
        pipeline_configuration = pipeline.IoTHubPipelineConfig(
            device_id=device_id,
            module_id=module_id,
            hostname=hostname,
            gateway_hostname=gateway_hostname,
            sastoken=sastoken,
            server_verification_cert=server_verification_cert,
            **config_kwargs
        )
        pipeline_configuration.method_invoke = (
            True  # Method Invoke is allowed on modules created from edge environment
        )

        # Pipeline setup
        http_pipeline = pipeline.HTTPPipeline(pipeline_configuration)
        mqtt_pipeline = pipeline.MQTTPipeline(pipeline_configuration)

        return cls(mqtt_pipeline, http_pipeline)

    @classmethod
    def create_from_x509_certificate(cls, x509, hostname, device_id, module_id, **kwargs):
        """
        Instantiate a client which using X509 certificate authentication.

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
        :param bool websockets: Configuration Option. Default is False. Set to true if using MQTT
            over websockets.
        :param cipher: Configuration Option. Cipher suite(s) for TLS/SSL, as a string in
            "OpenSSL cipher list format" or as a list of cipher suite strings.
        :type cipher: str or list(str)
        :param str product_info: Configuration Option. Default is empty string. The string contains
            arbitrary product info which is appended to the user agent string.
        :param proxy_options: Options for sending traffic through proxy servers.
        :type proxy_options: :class:`azure.iot.device.ProxyOptions`
        :param int keepalive: Maximum period in seconds between communications with the
        broker. If no other messages are being exchanged, this controls the
        rate at which the client will send ping messages to the broker.
        If not provided default value of 60 secs will be used.

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
    def send_message_to_output(self, message, output_name):
        pass

    @abc.abstractmethod
    def receive_message_on_input(self, input_name):
        pass
