# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import test_config
from dev_utils import test_env
import logging
import sys
from azure.iot.device import Message, IoTHubSession

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


def create_session_object(device_identity, client_kwargs):

    if test_config.config.auth == test_config.AUTH_CONNECTION_STRING:
        logger.info(
            "Creating session using create_from_connection_string with kwargs={}".format(
                client_kwargs
            )
        )

        session = IoTHubSession.from_connection_string(
            device_identity.connection_string, **client_kwargs
        )
    elif test_config.config.auth == test_config.AUTH_SYMMETRIC_KEY:
        logger.info(
            "Creating session using create_from_symmetric_key with kwargs={}".format(client_kwargs)
        )

        session = IoTHubSession(
            shared_access_key=device_identity.primary_key,
            hostname=test_env.IOTHUB_HOSTNAME,
            device_id=device_identity.device_id,
            **client_kwargs
        )
    elif test_config.config.auth == test_config.AUTH_SAS_TOKEN:
        logger.info(
            "Creating session using create_from_sastoken with kwargs={}".format(client_kwargs)
        )

        # client = ClientClass.create_from_sastoken(device_identity.sas_token, **client_kwargs)

        raise Exception("{} Auth not yet implemented".format(test_config.config.auth))

    elif test_config.config.auth in test_config.AUTH_CHOICES:
        # need to implement
        raise Exception("{} Auth not yet implemented".format(test_config.config.auth))
    else:
        raise Exception("config.auth invalid")

    return session


def is_windows():
    return sys.platform.startswith("win")
