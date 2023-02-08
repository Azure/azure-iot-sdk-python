# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import urllib.parse
from typing import Optional, Union, Dict

logger = logging.getLogger(__name__)

# TODO: Can TypeDicts be used for properties?

# NOTE: Whenever using standard URL encoding via the urllib.parse.quote() API
# make sure to specify that there are NO safe values (e.g. safe=""). By default
# "/" is skipped in encoding, and that is not desirable.
#
# DO NOT use urllib.parse.quote_plus(), as it turns ' ' characters into '+',
# which is invalid for MQTT publishes.
#
# DO NOT use urllib.parse.unquote_plus(), as it turns '+' characters into ' ',
# which is also invalid.


# NOTE (Oct 2020): URL encoding policy is currently inconsistent in this module due to restrictions
# with the Hub, as Hub does not do URL decoding on most values.
# (see: https://github.com/Azure/azure-iot-sdk-python/wiki/URL-Encoding-(MQTT)).
# Currently, as much as possible is URL encoded while keeping in line with the policy outlined
# in the above linked wiki article. This is to say that Device ID and Module ID are never
# encoded, however other values are. By convention, it's probably fine to be encoding/decoding most
# values that are not Device ID or Module ID, since it won't make a difference in production as
# the narrow range of acceptable values for, say, status code, or request ID don't contain any
# characters that require URL encoding/decoding in the first place. Thus it doesn't break on Hub,
# but it's still done here as a client-side best practice - Hub will eventually be doing a new API
# that does correctly URL encode/decode all values, so it's not good to roll back more than
# is currently necessary to avoid errors.


def _get_topic_base(device_id: str, module_id: Optional[str] = None) -> str:
    """
    return the string that is at the beginning of all topics for this
    device/module
    """

    # NOTE: Neither Device ID nor Module ID should be URL encoded in a topic string.
    # See the repo wiki article for details:
    # https://github.com/Azure/azure-iot-sdk-python/wiki/URL-Encoding-(MQTT)
    topic = "devices/" + str(device_id)
    if module_id:
        topic = topic + "/modules/" + str(module_id)
    return topic


def get_c2d_topic_for_subscribe(device_id: str) -> str:
    """
    :return: The topic for cloud to device messages.It is of the format
    "devices/<deviceid>/messages/devicebound/#"
    """
    return _get_topic_base(device_id) + "/messages/devicebound/#"


def get_input_topic_for_subscribe(device_id: str, module_id: str) -> str:
    """
    :return: The topic for input messages. It is of the format
    "devices/<deviceId>/modules/<moduleId>/inputs/#"
    """
    return _get_topic_base(device_id, module_id) + "/inputs/#"


def get_method_topic_for_subscribe() -> str:
    """
    :return: The topic for ALL incoming methods. It is of the format
    "$iothub/methods/POST/#"
    """
    return "$iothub/methods/POST/#"


def get_twin_response_topic_for_subscribe() -> str:
    """
    :return: The topic for ALL incoming twin responses. It is of the format
    "$iothub/twin/res/#"
    """
    return "$iothub/twin/res/#"


def get_twin_patch_topic_for_subscribe() -> str:
    """
    :return: The topic for ALL incoming twin patches. It is of the format
    "$iothub/twin/PATCH/properties/desired/#
    """
    return "$iothub/twin/PATCH/properties/desired/#"


def get_telemetry_topic_for_publish(device_id: str, module_id: Optional[str] = None) -> str:
    """
    return the topic string used to publish telemetry
    """
    return _get_topic_base(device_id, module_id) + "/messages/events/"


def get_method_topic_for_publish(request_id: str, status: Union[str, int]) -> str:
    """
    :return: The topic for publishing method responses. It is of the format
    "$iothub/methods/res/<status>/?$rid=<requestId>"
    """
    return "$iothub/methods/res/{status}/?$rid={request_id}".format(
        status=urllib.parse.quote(str(status), safe=""),
        request_id=urllib.parse.quote(str(request_id), safe=""),
    )


def get_twin_request_topic_for_publish(request_id: str) -> str:
    """
    :return: The topic for publishing a get twin request. It is of the format
    "$iothub/twin/GET/?$rid=<request_id>"
    """
    return "$iothub/twin/GET/?$rid={request_id}".format(
        request_id=urllib.parse.quote(str(request_id), safe="")
    )


def get_twin_patch_topic_for_publish(request_id: str) -> str:
    """
    :return: The topic for publishing a twin patch. It is of the format
    "$iothub/twin/PATCH/properties/reported?$rid=<request_id>"
    """
    return "$iothub/twin/PATCH/properties/reported/?$rid={request_id}".format(
        request_id=urllib.parse.quote(str(request_id), safe="")
    )


def insert_message_properties_in_topic(
    topic: str,
    system_properties: Dict[str, str],
    custom_properties: Dict[str, str],
) -> str:
    """
    URI encode system and custom properties into a message topic.

    :param dict system_properties: A dictionary mapping system properties to their values
    :param dict custom_properties: A dictionary mapping custom properties to their values.
    :return: The modified topic containing the encoded properties
    """
    if system_properties:
        encoded_system_properties = urllib.parse.urlencode(
            system_properties, quote_via=urllib.parse.quote
        )
        topic += encoded_system_properties
    if system_properties and custom_properties:
        topic += "&"
    if custom_properties:
        encoded_custom_properties = urllib.parse.urlencode(
            custom_properties, quote_via=urllib.parse.quote
        )
        topic += encoded_custom_properties
    return topic


def extract_properties_from_message_topic(topic: str) -> Dict[str, str]:
    """
    Extract key=value pairs from an incoming message topic, returning them as a dictionary.
    If a key has no matching value, the value will be set to empty string.

    :param str topic: The topic string
    :returns: dictionary mapping keys to values.
    """
    parts = topic.split("/")
    # Input Message Topic
    if len(parts) > 4 and parts[4] == "inputs":
        if len(parts) > 6:
            properties_string = parts[6]
        else:
            properties_string = ""
    # C2D Message Topic
    elif len(parts) > 3 and parts[3] == "devicebound":
        if len(parts) > 4:
            properties_string = parts[4]
        else:
            properties_string = ""
    else:
        raise ValueError("topic has incorrect format")

    return _extract_properties(properties_string)


def extract_name_from_method_request_topic(topic: str) -> str:
    """
    Extract the method name from the method topic.
    Topics for methods are of the following format:
    "$iothub/methods/POST/{method name}/?$rid={request id}"

    :param str topic: The topic string
    :return: method name from topic string
    """
    parts = topic.split("/")
    if topic.startswith("$iothub/methods/POST") and len(parts) >= 4:
        return urllib.parse.unquote(parts[3])
    else:
        raise ValueError("topic has incorrect format")


def extract_request_id_from_method_request_topic(topic: str) -> str:
    """
    Extract the Request ID (RID) from the method topic.
    Topics for methods are of the following format:
    "$iothub/methods/POST/{method name}/?$rid={request id}"

    :param str topic: the topic string
    :raises: ValueError if topic has incorrect format
    :returns: request id from topic string
    """
    parts = topic.split("/")
    if topic.startswith("$iothub/methods/POST") and len(parts) >= 4:
        properties = _extract_properties(topic.split("?")[1])
        rid = properties.get("$rid")
        if not rid:
            raise ValueError("No request id in topic")
        return rid
    else:
        raise ValueError("topic has incorrect format")


def extract_status_code_from_twin_response_topic(topic: str) -> str:
    """
    Extract the status code from the twin response topic.
    Topics for twin response are in the following format:
    "$iothub/twin/res/{status}/?$rid={rid}"

    :param str topic: The topic string
    :raises: ValueError if the topic has incorrect format
    :returns status code from topic string
    """
    parts = topic.split("/")
    if topic.startswith("$iothub/twin/res/") and len(parts) >= 4:
        return urllib.parse.unquote(parts[3])
    else:
        raise ValueError("topic has incorrect format")


def extract_request_id_from_twin_response_topic(topic: str) -> str:
    """
    Extract the Request ID (RID) from the twin response topic.
    Topics for twin response are in the following format:
    "$iothub/twin/res/{status}/?$rid={rid}"

    :param str topic: The topic string
    :raises: ValueError if topic has incorrect format
    :returns: request id from topic string
    """
    parts = topic.split("/")
    if topic.startswith("$iothub/twin/res/") and len(parts) >= 4:
        properties = _extract_properties(topic.split("?")[1])
        rid = properties.get("$rid")
        if not rid:
            raise ValueError("No request id in topic")
        return rid
    else:
        raise ValueError("topic has incorrect format")


def _extract_properties(properties_str: str) -> Dict[str, str]:
    """Return a dictionary of properties from a string in the format
    {key1}={value1}&{key2}={value2}...&{keyn}={valuen}

    For extracting values corresponding to keys the following rules are followed:-
    If there is a just a key with no "=", the value is an empty string
    """
    d: Dict[str, str] = {}
    if len(properties_str) == 0:
        # There are no properties, return empty
        return d

    kv_pairs = properties_str.split("&")
    for entry in kv_pairs:
        pair = entry.split("=")
        key = urllib.parse.unquote(pair[0])
        if len(pair) > 1:
            # Key/Value Pair
            value = urllib.parse.unquote(pair[1])
        else:
            # Key with no value -> value = None
            value = ""
        d[key] = value

    return d
