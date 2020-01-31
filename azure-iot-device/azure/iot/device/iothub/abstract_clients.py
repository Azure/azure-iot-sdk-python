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
import os
import io
from . import auth
from . import pipeline

from azure.iot.device.iothub.pipeline.config import IoTHubPipelineConfig


logger = logging.getLogger(__name__)

# A note on implementation:
# The intializer methods accept pipeline(s) instead of an auth provider in order to protect
# the client from logic related to authentication providers. This reduces edge cases, and allows
# pipeline configuration to be specifically tailored to the method of instantiation.
# For instance, .create_from_connection_string and .create_from_edge_envrionment both can use
# SymmetricKeyAuthenticationProviders to instantiate pipeline(s), but only .create_from_edge_environment
# should use it to instantiate an HTTPPipeline. If the initializer accepted an auth provider, and then
# used it to create pipelines, this detail would be lost, as there would be no way to tell if a
# SymmetricKeyAuthenticationProvider was intended to be part of an Edge scenario or not.


def _validate_kwargs(**kwargs):
    """Helper function to validate user provided kwargs.
    Raises TypeError if an invalid option has been provided"""
    valid_kwargs = ["product_info", "websockets", "cipher", "server_verification_cert"]

    for kwarg in kwargs:
        if kwarg not in valid_kwargs:
            raise TypeError("Got an unexpected keyword argument '{}'".format(kwarg))


def _get_pipeline_config_kwargs(**kwargs):
    """Helper function to get a subset of user provided kwargs relevant to IoTHubPipelineConfig"""
    new_kwargs = {}
    if "product_info" in kwargs:
        new_kwargs["product_info"] = kwargs["product_info"]
    if "websockets" in kwargs:
        new_kwargs["websockets"] = kwargs["websockets"]
    if "cipher" in kwargs:
        new_kwargs["cipher"] = kwargs["cipher"]
    return new_kwargs


@six.add_metaclass(abc.ABCMeta)
class AbstractIoTHubClient(object):
    """ A superclass representing a generic IoTHub client.
    This class needs to be extended for specific clients.
    """

    def __init__(self, iothub_pipeline, http_pipeline):
        """Initializer for a generic client.

        :param iothub_pipeline: The pipeline used to connect to the IoTHub endpoint.
        :type iothub_pipeline: :class:`azure.iot.device.iothub.pipeline.IoTHubPipeline`
        """
        self._iothub_pipeline = iothub_pipeline
        self._http_pipeline = http_pipeline

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

        :raises: ValueError if given an invalid connection_string.
        :raises: TypeError if given an unrecognized parameter.

        :returns: An instance of an IoTHub client that uses a connection string for authentication.
        """
        # TODO: Make this device/module specific and reject non-matching connection strings.
        # This will require refactoring of the auth package to use common objects (e.g. ConnectionString)
        # in order to differentiate types of connection strings.

        _validate_kwargs(**kwargs)

        # Pipeline Config setup
        pipeline_config_kwargs = _get_pipeline_config_kwargs(**kwargs)
        pipeline_configuration = IoTHubPipelineConfig(**pipeline_config_kwargs)
        if cls.__name__ == "IoTHubDeviceClient":
            pipeline_configuration.blob_upload = True

        # Auth Provider setup
        authentication_provider = auth.SymmetricKeyAuthenticationProvider.parse(connection_string)
        authentication_provider.server_verification_cert = kwargs.get("server_verification_cert")

        # Pipeline setup
        http_pipeline = pipeline.HTTPPipeline(authentication_provider, pipeline_configuration)
        iothub_pipeline = pipeline.IoTHubPipeline(authentication_provider, pipeline_configuration)

        return cls(iothub_pipeline, http_pipeline)

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
        return self._iothub_pipeline.connected


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

        :raises: TypeError if given an unrecognized parameter.

        :returns: An instance of an IoTHub client that uses an X509 certificate for authentication.
        """
        _validate_kwargs(**kwargs)

        # Pipeline Config setup
        pipeline_config_kwargs = _get_pipeline_config_kwargs(**kwargs)
        pipeline_configuration = IoTHubPipelineConfig(**pipeline_config_kwargs)
        pipeline_configuration.blob_upload = True  # Blob Upload is a feature on Device Clients

        # Auth Provider setup
        authentication_provider = auth.X509AuthenticationProvider(
            x509=x509, hostname=hostname, device_id=device_id
        )
        authentication_provider.server_verification_cert = kwargs.get("server_verification_cert")

        # Pipeline setup
        http_pipeline = pipeline.HTTPPipeline(authentication_provider, pipeline_configuration)
        iothub_pipeline = pipeline.IoTHubPipeline(authentication_provider, pipeline_configuration)

        return cls(iothub_pipeline, http_pipeline)

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

        :raises: TypeError if given an unrecognized parameter.

        :return: An instance of an IoTHub client that uses a symmetric key for authentication.
        """
        _validate_kwargs(**kwargs)

        # Pipeline Config setup
        pipeline_config_kwargs = _get_pipeline_config_kwargs(**kwargs)
        pipeline_configuration = IoTHubPipelineConfig(**pipeline_config_kwargs)
        pipeline_configuration.blob_upload = True  # Blob Upload is a feature on Device Clients

        # Auth Provider setup
        authentication_provider = auth.SymmetricKeyAuthenticationProvider(
            hostname=hostname, device_id=device_id, module_id=None, shared_access_key=symmetric_key
        )
        authentication_provider.server_verification_cert = kwargs.get("server_verification_cert")

        # Pipeline setup
        http_pipeline = pipeline.HTTPPipeline(authentication_provider, pipeline_configuration)
        iothub_pipeline = pipeline.IoTHubPipeline(authentication_provider, pipeline_configuration)

        return cls(iothub_pipeline, http_pipeline)

    @abc.abstractmethod
    def receive_message(self):
        pass


@six.add_metaclass(abc.ABCMeta)
class AbstractIoTHubModuleClient(AbstractIoTHubClient):
    def __init__(self, iothub_pipeline, http_pipeline):
        """Initializer for a module client.

        :param iothub_pipeline: The pipeline used to connect to the IoTHub endpoint.
        :type iothub_pipeline: :class:`azure.iot.device.iothub.pipeline.IoTHubPipeline`
        """
        super(AbstractIoTHubModuleClient, self).__init__(iothub_pipeline, http_pipeline)

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

        :raises: OSError if the IoT Edge container is not configured correctly.
        :raises: ValueError if debug variables are invalid.

        :returns: An instance of an IoTHub client that uses the IoT Edge environment for
            authentication.
        """
        _validate_kwargs(**kwargs)
        if kwargs.get("server_verification_cert"):
            raise TypeError(
                "'server_verification_cert' is not supported by clients using an IoT Edge environment"
            )

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
            # TODO: variant server_verification_cert file vs data object that would remove the need for this fopen
            # Read the certificate file to pass it on as a string
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
            # Use Symmetric Key authentication for local dev experience.
            try:
                authentication_provider = auth.SymmetricKeyAuthenticationProvider.parse(
                    connection_string
                )
            except ValueError:
                raise
            authentication_provider.server_verification_cert = server_verification_cert
        else:
            # Use an HSM for authentication in the general case
            try:
                authentication_provider = auth.IoTEdgeAuthenticationProvider(
                    hostname=hostname,
                    device_id=device_id,
                    module_id=module_id,
                    gateway_hostname=gateway_hostname,
                    module_generation_id=module_generation_id,
                    workload_uri=workload_uri,
                    api_version=api_version,
                )
            except auth.IoTEdgeError as e:
                new_err = OSError("Unexpected failure in IoTEdge")
                new_err.__cause__ = e
                raise new_err

        # Pipeline Config setup
        pipeline_config_kwargs = _get_pipeline_config_kwargs(**kwargs)
        pipeline_configuration = IoTHubPipelineConfig(**pipeline_config_kwargs)
        pipeline_configuration.method_invoke = (
            True
        )  # Method Invoke is allowed on modules created from edge environment

        # Pipeline setup
        http_pipeline = pipeline.HTTPPipeline(authentication_provider, pipeline_configuration)
        iothub_pipeline = pipeline.IoTHubPipeline(authentication_provider, pipeline_configuration)

        return cls(iothub_pipeline, http_pipeline)

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

        :raises: TypeError if given an unrecognized parameter.

        :returns: An instance of an IoTHub client that uses an X509 certificate for authentication.
        """
        _validate_kwargs(**kwargs)

        # Pipeline Config setup
        pipeline_config_kwargs = _get_pipeline_config_kwargs(**kwargs)
        pipeline_configuration = IoTHubPipelineConfig(**pipeline_config_kwargs)

        # Auth Provider setup
        authentication_provider = auth.X509AuthenticationProvider(
            x509=x509, hostname=hostname, device_id=device_id, module_id=module_id
        )
        authentication_provider.server_verification_cert = kwargs.get("server_verification_cert")

        # Pipeline setup
        http_pipeline = pipeline.HTTPPipeline(authentication_provider, pipeline_configuration)
        iothub_pipeline = pipeline.IoTHubPipeline(authentication_provider, pipeline_configuration)
        return cls(iothub_pipeline, http_pipeline)

    @abc.abstractmethod
    def send_message_to_output(self, message, output_name):
        pass

    @abc.abstractmethod
    def receive_message_on_input(self, input_name):
        pass
