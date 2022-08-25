# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import test_config
from dev_utils import test_env
import logging
import sys
from azure.iot.device.iothub import Message

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


fault_injection_types = {
    "KillTcp": " severs the TCP connection ",
    "ShutDownMqtt": " cleanly shutdowns the MQTT connection ",
}


def get_fault_injection_message(fault_injection_type):
    fault_message = Message(" ")
    fault_message.custom_properties["AzIoTHub_FaultOperationType"] = fault_injection_type
    fault_message.custom_properties["AzIoTHub_FaultOperationCloseReason"] = fault_injection_types[
        fault_injection_type
    ]
    fault_message.custom_properties["AzIoTHub_FaultOperationDelayInSecs"] = 5
    return fault_message


def create_client_object(device_identity, client_kwargs, DeviceClass, ModuleClass):

    if test_config.config.identity in [
        test_config.IDENTITY_DEVICE,
        test_config.IDENTITY_EDGE_LEAF_DEVICE,
    ]:
        ClientClass = DeviceClass
    elif test_config.config.identity in [
        test_config.IDENTITY_MODULE,
        test_config.IDENTITY_EDGE_MODULE,
    ]:
        ClientClass = ModuleClass
    else:
        raise Exception("config.identity invalid")

    if test_config.config.auth == test_config.AUTH_CONNECTION_STRING:
        logger.info(
            "Creating {} using create_from_connection_string with kwargs={}".format(
                ClientClass, client_kwargs
            )
        )

        client = ClientClass.create_from_connection_string(
            device_identity.connection_string, **client_kwargs
        )
    elif test_config.config.auth == test_config.AUTH_SYMMETRIC_KEY:
        logger.info(
            "Creating {} using create_from_symmetric_key with kwargs={}".format(
                ClientClass, client_kwargs
            )
        )

        client = ClientClass.create_from_symmetric_key(
            device_identity.primary_key,
            test_env.IOTHUB_HOSTNAME,
            device_identity.device_id,
            **client_kwargs
        )
    elif test_config.config.auth == test_config.AUTH_SAS_TOKEN:
        logger.info(
            "Creating {} using create_from_sastoken with kwargs={}".format(
                ClientClass, client_kwargs
            )
        )

        client = ClientClass.create_from_sastoken(device_identity.sas_token, **client_kwargs)

    elif test_config.config.auth in test_config.AUTH_CHOICES:
        # need to implement
        raise Exception("{} Auth not yet implemented".format(test_config.config.auth))
    else:
        raise Exception("config.auth invalid")

    return client


def is_windows():
    return sys.platform.startswith("win")
