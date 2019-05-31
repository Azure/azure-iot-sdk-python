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
from azure.iot.device.provisioning.pipeline.provisioning_pipeline import ProvisioningPipeline

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
        """
        self._provisioning_pipeline = provisioning_pipeline

    @classmethod
    def create_from_security_client(cls, security_client, protocol_name):
        """
        Creates different types of provisioning clients which can enable devices to communicate with Device Provisioning
        Service based on parameters passed.
        :param security_client: Instance of Security client object which can be either of SymmetricKeySecurityClient,  TPMSecurtiyClient or X509SecurityClient
        :param protocol_name: A string representing the name of the communication protocol the user wants
        :return: A specific provisioning client based on parameters and validations.
        """
        protocol_name = protocol_name.lower()
        if protocol_name == "mqtt":
            if isinstance(security_client, SymmetricKeySecurityClient):
                mqtt_provisioning_pipeline = ProvisioningPipeline(security_client)
                return cls(mqtt_provisioning_pipeline)
                # TODO : other instances of security provider can also be checked before creating mqtt and client
            else:
                raise ValueError("A symmetric key security provider must be provided for MQTT")

        else:
            raise NotImplementedError("This communication protocol has not yet been implemented")
            # TODO : Message must be enhanced later for other security providers. MQTT can also support X509.

    @abc.abstractmethod
    def register(self):
        """
        Register the device with the Device Provisioning Service.
        """
        pass

    @abc.abstractmethod
    def cancel(self):
        """
        Cancel an in progress registration of the device with the Device Provisioning Service.
        """
        pass


def log_on_register_complete(result=None, error=None):
    # This could be a failed/successful registration result from the HUB
    # or a error from polling machine. Response should be given appropriately
    if result is not None:
        if result.status == "assigned":
            logger.info("Successfully registered with Hub")
        else:  # There be other statuses
            logger.error("Failed registering with Hub")
    if error is not None:  # This can only happen when the polling machine runs into error
        logger.info(error)
