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
from .pipeline import IoTHubPipeline


logger = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class AbstractIoTHubClient(object):
    """A superclass representing a generic client. This class needs to be extended for specific clients."""

    def __init__(self, pipeline):
        """Initializer for a generic client.

        :param pipeline: The pipeline that the client will use.
        """
        # TODO: Refactor this to be an iothub_pipeline, and instantiate here instead of
        # in the factory methods
        self._pipeline = pipeline

    @classmethod
    def create_from_connection_string(cls, connection_string, trusted_certificate_chain=None):
        """
        Instantiate the client from a IoTHub device or module connection string.

        :param str connection_string: The connection string for the IoTHub you wish to connect to.
        :param str trusted_certificate_chain: The trusted certificate chain. Necessary when using a
        connection string with a GatewayHostName parameter. DEFAULT: None

        :raises: ValueError if given an invalid connection_string.
        """
        # TODO: Make this device/module specific and reject non-matching connection strings.
        # This will require refactoring of the auth package to use common objects (e.g. ConnectionString)
        # in order to differentiate types of connection strings.
        authentication_provider = auth.SymmetricKeyAuthenticationProvider.parse(connection_string)
        authentication_provider.ca_cert = (
            trusted_certificate_chain
        )  # TODO: make this part of the instantiation
        pipeline = IoTHubPipeline(authentication_provider)
        return cls(pipeline)

    @classmethod
    def create_from_shared_access_signature(cls, sas_token):
        """
        Instantiate the client from a Shared Access Signature (SAS) token.

        This method of instantiation is not recommended for general usage.

        :param str sas_token: The string representation of a SAS token.

        :raises: ValueError if given an invalid sas_token
        """
        authentication_provider = auth.SharedAccessSignatureAuthenticationProvider.parse(sas_token)
        pipeline = IoTHubPipeline(authentication_provider)
        return cls(pipeline)

    @abc.abstractmethod
    def connect(self):
        pass

    @abc.abstractmethod
    def disconnect(self):
        pass

    @abc.abstractmethod
    def send_d2c_message(self, message):
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
    def create_from_x509_certificate(cls, hostname, device_id, x509):
        """
        Instantiate a client which using X509 certificate authentication.
        :param hostname: Host running the IotHub. Can be found in the Azure portal in the Overview tab as the string hostname.
        :param device_id: The ID is used to uniquely identify a device in the IoTHub
        :param x509: The complete x509 certificate object, To use the certificate the enrollment object needs to contain cert (either the root certificate or one of the intermediate CA certificates).
        If the cert comes from a CER file, it needs to be base64 encoded.
        :type x509: X509
        :return: A IoTHubClient which can use X509 authentication.
        """
        authentication_provider = auth.X509AuthenticationProvider(
            hostname=hostname, device_id=device_id, x509=x509
        )
        pipeline = IoTHubPipeline(authentication_provider)
        return cls(pipeline)

    @abc.abstractmethod
    def receive_c2d_message(self):
        pass


@six.add_metaclass(abc.ABCMeta)
class AbstractIoTHubModuleClient(AbstractIoTHubClient):
    @classmethod
    def create_from_edge_environment(cls):
        """
        Instantiate the client from the IoT Edge environment.

        This method can only be run from inside an IoT Edge container, or in a debugging
        environment configured for Edge development (e.g. Visual Studio, Visual Studio Code)

        :raises: IoTEdgeError if the IoT Edge container is not configured correctly.
        :raises: ValueError if debug variables are invalid
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
            except KeyError:
                # TODO: consider using a different error here. (OSError?)
                raise auth.IoTEdgeError("IoT Edge environment not configured correctly")

            # Read the certificate file to pass it on as a string
            try:
                with io.open(ca_cert_filepath, mode="r") as ca_cert_file:
                    ca_cert = ca_cert_file.read()
            except (OSError, IOError):
                # In Python 2, a non-existent file raises IOError, and an invalid file raises an IOError.
                # In Python 3, a non-existent file raises FileNotFoundError, and an invalid file raises an OSError.
                # However, FileNotFoundError inherits from OSError, and IOError has been turned into an alias for OSError,
                # thus we can catch the errors for both versions in this block.
                # Unfortunately, we can't distinguish cause of error from error type, so the raised ValueError has a generic
                # message. If, in the future, we want to add detail, this could be accomplished by inspecting the e.errno
                # attribute
                raise ValueError("Invalid CA certificate file")
            # Use Symmetric Key authentication for local dev experience.
            authentication_provider = auth.SymmetricKeyAuthenticationProvider.parse(
                connection_string
            )
            authentication_provider.ca_cert = ca_cert
        else:
            # Use an HSM for authentication in the general case
            authentication_provider = auth.IoTEdgeAuthenticationProvider(
                hostname=hostname,
                device_id=device_id,
                module_id=module_id,
                gateway_hostname=gateway_hostname,
                module_generation_id=module_generation_id,
                workload_uri=workload_uri,
                api_version=api_version,
            )

        pipeline = IoTHubPipeline(authentication_provider)
        return cls(pipeline)

    @abc.abstractmethod
    def send_to_output(self, message, output_name):
        pass

    @abc.abstractmethod
    def receive_input_message(self, input_name):
        pass
