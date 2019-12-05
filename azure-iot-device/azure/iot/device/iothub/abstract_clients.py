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
# should use it to instantiate an EdgePipeline. If the initializer accepted an auth provider, and then
# used it to create pipelines, this detail would be lost, as there would be no way to tell if a
# SymmetricKeyAuthenticationProvider was intended to be part of an Edge scenario or not.


@six.add_metaclass(abc.ABCMeta)
class AbstractIoTHubClient(object):
    """ A superclass representing a generic IoTHub client.
    This class needs to be extended for specific clients.
    """

    def __init__(self, iothub_pipeline):
        """Initializer for a generic client.

        :param iothub_pipeline: The pipeline used to connect to the IoTHub endpoint.
        :type iothub_pipeline: :class:`azure.iot.device.iothub.pipeline.IoTHubPipeline`
        """
        self._iothub_pipeline = iothub_pipeline
        self._edge_pipeline = None

    @classmethod
    def create_from_connection_string(cls, connection_string, ca_cert=None, **kwargs):
        """
        Instantiate the client from a IoTHub device or module connection string.

        :param str connection_string: The connection string for the IoTHub you wish to connect to.
        :param str ca_cert: The trusted certificate chain. Only necessary when using a
            connection string with a GatewayHostName parameter.

        :param bool websockets: Configuration Option. Default is False. Set to true if using MQTT over websockets.
        :param str product_info: Configuration Option. Default is empty string. The string contains arbitrary product info which is appended to the user agent string.

        :raises: ValueError if given an invalid connection_string.

        :returns: An instance of an IoTHub client that uses a connection string for authentication.
        """
        # TODO: Make this device/module specific and reject non-matching connection strings.
        # This will require refactoring of the auth package to use common objects (e.g. ConnectionString)
        # in order to differentiate types of connection strings.
        authentication_provider = auth.SymmetricKeyAuthenticationProvider.parse(connection_string)
        authentication_provider.ca_cert = ca_cert  # TODO: make this part of the instantiation
        pipeline_configuration = IoTHubPipelineConfig(**kwargs)
        iothub_pipeline = pipeline.IoTHubPipeline(authentication_provider, pipeline_configuration)
        return cls(iothub_pipeline)

    @classmethod
    def create_from_shared_access_signature(cls, sas_token, **kwargs):
        """
        Instantiate the client from a Shared Access Signature (SAS) token.
        This method of instantiation is not recommended for general usage.

        :param str sas_token: The string representation of a SAS token.

        :param bool websockets: Configuration Option. Default is False. Set to true if using MQTT over websockets.
        :param str product_info: Configuration Option. Default is empty string. The string contains arbitrary product info which is appended to the user agent string.

        :raises: ValueError if given an invalid sas_token

        :returns: An instance of an IoTHub client that uses a SAS token for authentication.
        """
        authentication_provider = auth.SharedAccessSignatureAuthenticationProvider.parse(sas_token)
        pipeline_configuration = IoTHubPipelineConfig(**kwargs)
        iothub_pipeline = pipeline.IoTHubPipeline(authentication_provider, pipeline_configuration)
        return cls(iothub_pipeline)

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

        :param bool websockets: Configuration Option. Default is False. Set to true if using MQTT over websockets.
        :param str product_info: Configuration Option. Default is empty string. The string contains arbitrary product info which is appended to the user agent string.

        :returns: An instance of an IoTHub client that uses an X509 certificate for authentication.
        """
        authentication_provider = auth.X509AuthenticationProvider(
            x509=x509, hostname=hostname, device_id=device_id
        )
        pipeline_configuration = IoTHubPipelineConfig(**kwargs)
        iothub_pipeline = pipeline.IoTHubPipeline(authentication_provider, pipeline_configuration)
        return cls(iothub_pipeline)

    @classmethod
    def create_from_registration_result_and_symmetric_key(
        cls, registration_result, symmetric_key, ca_cert=None, **kwargs
    ):
        registration_state = registration_result.registration_state
        # Decided not to call create_from_connection_string
        # method and parse the connection_string again
        # when we have all the individual elements
        authentication_provider = auth.SymmetricKeyAuthenticationProvider(
            hostname=registration_state.assigned_hub,
            device_id=registration_state.device_id,
            module_id=None,
            shared_access_key=symmetric_key,
        )
        authentication_provider.ca_cert = ca_cert  # TODO: make this part of the instantiation
        pipeline_configuration = IoTHubPipelineConfig(**kwargs)
        iothub_pipeline = pipeline.IoTHubPipeline(authentication_provider, pipeline_configuration)
        return cls(iothub_pipeline)

    @classmethod
    def create_from_registration_result_and_x509(cls, registration_result, x509, **kwargs):
        registration_state = registration_result.registration_state
        authentication_provider = auth.X509AuthenticationProvider(
            hostname=registration_state.assigned_hub,
            device_id=registration_state.device_id,
            x509=x509,
        )
        pipeline_configuration = IoTHubPipelineConfig(**kwargs)
        iothub_pipeline = pipeline.IoTHubPipeline(authentication_provider, pipeline_configuration)
        return cls(iothub_pipeline)

    @abc.abstractmethod
    def receive_message(self):
        pass


@six.add_metaclass(abc.ABCMeta)
class AbstractIoTHubModuleClient(AbstractIoTHubClient):
    def __init__(self, iothub_pipeline, edge_pipeline=None):
        """Initializer for a module client.

        :param iothub_pipeline: The pipeline used to connect to the IoTHub endpoint.
        :type iothub_pipeline: :class:`azure.iot.device.iothub.pipeline.IoTHubPipeline`
        :param edge_pipeline: The pipeline used to connect to the Edge endpoint.
        :type edge_pipeline: :class:`azure.iot.device.iothub.pipeline.EdgePipeline`
        """
        super(AbstractIoTHubModuleClient, self).__init__(iothub_pipeline)
        self._edge_pipeline = edge_pipeline

    @classmethod
    def create_from_edge_environment(cls, **kwargs):
        """
        Instantiate the client from the IoT Edge environment.

        This method can only be run from inside an IoT Edge container, or in a debugging
        environment configured for Edge development (e.g. Visual Studio, Visual Studio Code)

        :param bool websockets: Configuration Option. Default is False. Set to true if using MQTT over websockets.
        :param str product_info: Configuration Option. Default is empty string. The string contains arbitrary product info which is appended to the user agent string.

        :raises: OSError if the IoT Edge container is not configured correctly.
        :raises: ValueError if debug variables are invalid

        :returns: An instance of an IoTHub client that uses the IoT Edge environment for
            authentication.
        """
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
            # TODO: variant ca_cert file vs data object that would remove the need for this fopen
            # Read the certificate file to pass it on as a string
            try:
                with io.open(ca_cert_filepath, mode="r") as ca_cert_file:
                    ca_cert = ca_cert_file.read()
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
            authentication_provider.ca_cert = ca_cert
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

        pipeline_configuration = IoTHubPipelineConfig(**kwargs)
        iothub_pipeline = pipeline.IoTHubPipeline(authentication_provider, pipeline_configuration)
        edge_pipeline = pipeline.EdgePipeline(authentication_provider)
        return cls(iothub_pipeline, edge_pipeline=edge_pipeline)

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

        :param bool websockets: Configuration Option. Default is False. Set to true if using MQTT over websockets.
        :param str product_info: Configuration Option. Default is empty string. The string contains arbitrary product info which is appended to the user agent string.

        :returns: An instance of an IoTHub client that uses an X509 certificate for authentication.
        """
        authentication_provider = auth.X509AuthenticationProvider(
            x509=x509, hostname=hostname, device_id=device_id, module_id=module_id
        )
        pipeline_configuration = IoTHubPipelineConfig(**kwargs)
        iothub_pipeline = pipeline.IoTHubPipeline(authentication_provider, pipeline_configuration)
        return cls(iothub_pipeline)

    @abc.abstractmethod
    def send_message_to_output(self, message, output_name):
        pass

    @abc.abstractmethod
    def receive_message_on_input(self, input_name):
        pass
