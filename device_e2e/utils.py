# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import random
import string
import json
import uuid
import const
from azure.iot.device.iothub import Message


def get_random_dict():
    return {
        "random_guid": str(uuid.uuid4()),
        "sub_object": {
            "string_value": "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(10)
            ),
            "bool_value": random.random() > 0.5,
            "int_value": random.randint(-65535, 65535),
        },
    }


def get_random_message():
    message = Message(json.dumps(get_random_dict()))
    message.content_type = const.JSON_CONTENT_TYPE
    message.content_encoding = const.JSON_CONTENT_ENCODING
    return message


def make_pnp_desired_property_patch(component_name, property_name, property_value):
    if component_name:
        return [
            {
                "op": "add",
                "path": "/{}".format(component_name),
                "value": {property_name: property_value, "$metadata": {}},
            }
        ]
    else:
        return [{"op": "add", "path": "/{}".format(property_name), "value": property_value}]
