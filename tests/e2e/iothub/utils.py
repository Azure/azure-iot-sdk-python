# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import random
import string
import json
import uuid
import const
import test_config
import e2e_settings
import logging
import sys
from azure.iot.device.iothub import Message

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


def get_random_string(length, random_length=False):
    if random_length:
        length = random.randint(0, length)

    return "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))


def get_random_dict(total_payload_length=0):
    obj = {
        "random_guid": str(uuid.uuid4()),
        "sub_object": {
            "string_value": get_random_string(10),
            "bool_value": random.random() > 0.5,
            "int_value": random.randint(-65535, 65535),
        },
    }

    if total_payload_length:
        length = len(json.dumps(obj))
        extra_characters = total_payload_length - length - len(', "extra": ""')
        if extra_characters > 0:
            obj["extra"] = get_random_string(extra_characters)

        assert len(json.dumps(obj)) == total_payload_length

    return obj


def get_random_message(total_payload_length=0):
    message = Message(json.dumps(get_random_dict(total_payload_length)))
    message.content_type = const.JSON_CONTENT_TYPE
    message.content_encoding = const.JSON_CONTENT_ENCODING
    message.message_id = str(uuid.uuid4())
    return message


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
            e2e_settings.IOTHUB_HOSTNAME,
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
