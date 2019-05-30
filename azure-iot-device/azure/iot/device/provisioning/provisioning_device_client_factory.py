# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""
This module provides factory methods for creating clients which would
communicate with Device Provisioning Service.
"""
from .security.sk_security_client import SymmetricKeySecurityClient
from .sk_provisioning_device_client import SymmetricKeyProvisioningDeviceClient
from azure.iot.device.provisioning.pipeline.provisioning_pipeline import ProvisioningPipeline


def create_from_security_client(security_client, protocol_name):
    """
    Creates different types of registration clients which can enable devices to communicate with Device Provisioning
    Service based on parameters passed.
    :param security_client: Instance of Security client object which can be either of SymmetricKeySecurityClient,  TPMSecurtiyClient or X509SecurityClient
    :param protocol_name: A string representing the name of the communication protocol the user wants
    :return: A specific registration client based on parameters and validations.
    """
    protocol_name = protocol_name.lower()
    if protocol_name == "mqtt":
        if isinstance(security_client, SymmetricKeySecurityClient):
            mqtt_provisioning_pipeline = ProvisioningPipeline(security_client)
            return SymmetricKeyProvisioningDeviceClient(mqtt_provisioning_pipeline)
            # TODO : other instances of security provider can also be checked before creating mqtt and client
        else:
            raise ValueError("A symmetric key security provider must be provided for MQTT")

    else:
        raise NotImplementedError("This communication protocol has not yet been implemented")
        # TODO : Message must be enhanced later for other security providers. MQTT can also support X509.
