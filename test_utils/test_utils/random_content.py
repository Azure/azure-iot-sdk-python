# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import random
import string
import json
import uuid
from azure.iot.device.iothub import Message

JSON_CONTENT_TYPE = "application/json"
JSON_CONTENT_ENCODING = "utf-8"


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
    message.content_type = JSON_CONTENT_TYPE
    message.content_encoding = JSON_CONTENT_ENCODING
    message.message_id = str(uuid.uuid4())
    return message
