# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""
This module provides an abstract interface representing clients which can communicate with the
Device Provisioning Service.
"""

import abc
import six
import logging
from .security.sk_security_client import SymmetricKeySecurityClient
from .security.x509_security_client import X509SecurityClient
from azure.iot.device.provisioning.pipeline.provisioning_pipeline import ProvisioningPipeline
from azure.iot.device.common.pipeline.config import BasePipelineConfig

logger = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class AbstractProvisioningDeviceClient(object):
    """
    Super class for any client that can be used to register devices to Device Provisioning Service.
    """

    def __init__(self, provisioning_pipeline):
        """
        Initializes the provisioning client.

        :param provisioning_pipeline: Instance of the provisioning pipeline object.
        :type provisioning_pipeline: :class:`azure.iot.device.provisioning.pipeline.ProvisioningPipeline`
        """
        self._provisioning_pipeline = provisioning_pipeline
        self._provisioning_payload = None

    @classmethod
    def create_from_symmetric_key(
        cls, provisioning_host, registration_id, id_scope, symmetric_key, **kwargs
    ):
        """
        Create a client which can be used to run the registration of a device with provisioning service
        using Symmetric Key authentication.

        :param str provisioning_host: Host running the Device Provisioning Service.
            Can be found in the Azure portal in the Overview tab as the string Global device endpoint.
        :param str registration_id: The registration ID used to uniquely identify a device in the
            Device Provisioning Service. The registration ID is alphanumeric, lowercase string
            and may contain hyphens.
        :param str id_scope: The ID scope used to uniquely identify the specific provisioning
            service the device will register through. The ID scope is assigned to a
            Device Provisioning Service when it is created by the user and is generated by the
            service and is immutable, guaranteeing uniqueness.
        :param str symmetric_key: The key which will be used to create the shared access signature
            token to authenticate the device with the Device Provisioning Service. By default,
            the Device Provisioning Service creates new symmetric keys with a default length of
            32 bytes when new enrollments are saved with the Auto-generate keys option enabled.
            Users can provide their own symmetric keys for enrollments by disabling this option
            within 16 bytes and 64 bytes and in valid Base64 format.
        :param bool websockets: The switch for enabling MQTT over websockets. Defaults to false (no websockets).
        :returns: A ProvisioningDeviceClient instance which can register via Symmetric Key.
        """
        security_client = SymmetricKeySecurityClient(
            provisioning_host, registration_id, id_scope, symmetric_key
        )
        pipeline_configuration = BasePipelineConfig(**kwargs)
        mqtt_provisioning_pipeline = ProvisioningPipeline(security_client, pipeline_configuration)
        return cls(mqtt_provisioning_pipeline)

    @classmethod
    def create_from_x509_certificate(
        cls, provisioning_host, registration_id, id_scope, x509, **kwargs
    ):
        """
        Create a client which can be used to run the registration of a device with
        provisioning service using X509 certificate authentication.

        :param str provisioning_host: Host running the Device Provisioning Service. Can be found in
            the Azure portal in the Overview tab as the string Global device endpoint.
        :param str registration_id: The registration ID used to uniquely identify a device in the
            Device Provisioning Service. The registration ID is alphanumeric, lowercase string
            and may contain hyphens.
        :param str id_scope: The ID scope is used to uniquely identify the specific
            provisioning service the device will register through. The ID scope is assigned to a
            Device Provisioning Service when it is created by the user and is generated by the
            service and is immutable, guaranteeing uniqueness.
        :param x509: The x509 certificate, To use the certificate the enrollment object needs to
            contain cert (either the root certificate or one of the intermediate CA certificates).
            If the cert comes from a CER file, it needs to be base64 encoded.
        :type x509: :class:`azure.iot.device.X509`
        :param bool websockets: The switch for enabling MQTT over websockets. Defaults to false (no websockets).
        :returns: A ProvisioningDeviceClient which can register via Symmetric Key.
        """
        security_client = X509SecurityClient(provisioning_host, registration_id, id_scope, x509)
        pipeline_configuration = BasePipelineConfig(**kwargs)
        mqtt_provisioning_pipeline = ProvisioningPipeline(security_client, pipeline_configuration)
        return cls(mqtt_provisioning_pipeline)

    @abc.abstractmethod
    def register(self):
        """
        Register the device with the Device Provisioning Service.
        """
        pass

    @property
    def provisioning_payload(self):
        return self._provisioning_payload

    @provisioning_payload.setter
    def provisioning_payload(self, provisioning_payload):
        """
        Set the payload that will form the request payload in a registration request.

        :param provisioning_payload: The payload that can be supplied by the user.
        :type provisioning_payload: This can be an object or dictionary or a string or an integer.
        """
        self._provisioning_payload = provisioning_payload


def log_on_register_complete(result=None):
    # This could be a failed/successful registration result from DPS
    # or a error from polling machine. Response should be given appropriately
    if result is not None:
        if result.status == "assigned":
            logger.info("Successfully registered with Provisioning Service")
        else:  # There be other statuses
            logger.error("Failed registering with Provisioning Service")
