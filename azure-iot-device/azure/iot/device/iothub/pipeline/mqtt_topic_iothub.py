# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
from datetime import date
import six.moves.urllib as urllib

logger = logging.getLogger(__name__)


def _get_topic_base(device_id, module_id):
    """
    return the string that is at the beginning of all topics for this
    device/module
    """

    if module_id:
        return "devices/" + device_id + "/modules/" + module_id
    else:
        return "devices/" + device_id


def get_telemetry_topic_for_publish(device_id, module_id):
    """
    return the topic string used to publish telemetry
    """
    return _get_topic_base(device_id, module_id) + "/messages/events/"


def get_c2d_topic_for_subscribe(device_id, module_id):
    """
    :return: The topic for cloud to device messages.It is of the format
    "devices/<deviceid>/messages/devicebound/#"
    """
    return _get_topic_base(device_id, module_id) + "/messages/devicebound/#"


def get_input_topic_for_subscribe(device_id, module_id):
    """
    :return: The topic for input messages. It is of the format
    "devices/<deviceId>/modules/<moduleId>/inputs/#"
    """
    return _get_topic_base(device_id, module_id) + "/inputs/#"


def get_method_topic_for_publish(request_id, status):
    """
    :return: The topic for publishing method responses. It is of the format
    "$iothub/methods/res/<status>/?$rid=<requestId>
    """
    return "$iothub/methods/res/{status}/?$rid={rid}".format(
        status=urllib.parse.quote_plus(status), rid=urllib.parse.quote_plus(request_id)
    )


def get_method_topic_for_subscribe():
    """
    :return: The topic for ALL incoming methods. It is of the format
    "$iothub/methods/POST/#"
    """
    return "$iothub/methods/POST/#"


def is_c2d_topic(topic):
    """
    Topics for c2d message are of the following format:
    devices/<deviceId>/messages/devicebound
    :param topic: The topic string
    """
    if "messages/devicebound" in topic:
        return True
    return False


def is_input_topic(topic):
    """
    Topics for inputs are of the following format:
    devices/<deviceId>/modules/<moduleId>/inputs/<inputName>
    :param topic: The topic string
    """
    if "/inputs/" in topic:
        return True
    return False


def get_input_name_from_topic(topic):
    """
    Extract the input channel from the topic name
    Topics for inputs are of the following format:
    devices/<deviceId>/modules/<moduleId>/inputs/<inputName>
    :param topic: The topic string
    """
    parts = topic.split("/")
    if len(parts) > 5 and parts[4] == "inputs":
        return parts[5]
    else:
        raise ValueError("topic has incorrect format")


def is_method_topic(topic):
    """
    Topics for methods are of the following format:
    "$iothub/methods/POST/{method name}/?$rid={request id}"

    :param str topic: The topic string.
    """
    if "$iothub/methods/POST" in topic:
        return True
    return False


def get_method_name_from_topic(topic):
    """
    Extract the method name from the method topic.
    Topics for methods are of the following format:
    "$iothub/methods/POST/{method name}/?$rid={request id}"

    :param str topic: The topic string
    """
    parts = topic.split("/")
    if is_method_topic(topic) and len(parts) >= 4:
        return parts[3]
    else:
        raise ValueError("topic has incorrect format")


# TODO: leverage this helper in all property extraction functions
def _extract_properties(properties_str):
    """Return a dictionary of properties from a string in the format
    ${key1}={value1}&${key2}={value2}&...{keyn}={valuen}
    """
    d = {}
    kv_pairs = properties_str.split("&")

    for entry in kv_pairs:
        pair = entry.split("=")
        key = urllib.parse.unquote_plus(pair[0]).lstrip("$")
        value = urllib.parse.unquote_plus(pair[1])
        d[key] = value

    return d


def get_method_request_id_from_topic(topic):
    """
    Extract the Request ID (RID) from the method topic.
    Topics for methods are of the following format:
    "$iothub/methods/POST/{method name}/?$rid={request id}"

    :param str topic: the topic string
    :raises: ValueError if topic has incorrect format
    :returns: request id from topic string
    """
    parts = topic.split("/")
    if is_method_topic(topic) and len(parts) >= 4:

        properties = _extract_properties(topic.split("?")[1])
        return properties["rid"]
    else:
        raise ValueError("topic has incorrect format")


# TODO: this has too generic a name, given that it's only for messages
def extract_properties_from_topic(topic, message_received):
    """
    Extract key=value pairs from custom properties and set the properties on the received message.
    :param topic: The topic string
    :param message_received: The message received with the payload in bytes
    """

    parts = topic.split("/")
    if len(parts) > 5 and parts[4] == "inputs":
        properties = parts[6]
    elif len(parts) > 4 and parts[3] == "devicebound":
        properties = parts[4]
    else:
        raise ValueError("topic has incorrect format")

    key_value_pairs = properties.split("&")

    for entry in key_value_pairs:
        pair = entry.split("=")
        key = urllib.parse.unquote_plus(pair[0])
        value = urllib.parse.unquote_plus(pair[1])

        if key == "$.mid":
            message_received.message_id = value
        elif key == "$.cid":
            message_received.correlation_id = value
        elif key == "$.uid":
            message_received.user_id = value
        elif key == "$.to":
            message_received.to = value
        elif key == "$.ct":
            message_received.content_type = value
        elif key == "$.ce":
            message_received.content_encoding = value
        else:
            message_received.custom_properties[key] = value


# TODO: this has too generic a name, given that it's only for messages
def encode_properties(message_to_send, topic):
    """
    uri-encode the system properties of a message as key-value pairs on the topic with defined keys.
    Additionally if the message has user defined properties, the property keys and values shall be
    uri-encoded and appended at the end of the above topic with the following convention:
    '<key>=<value>&<key2>=<value2>&<key3>=<value3>(...)'
    :param message_to_send: The message to send
    :param topic: The topic which has not been encoded yet. For a device it looks like
    "devices/<deviceId>/messages/events/" and for a module it looks like
    "devices/<deviceId>/modules/<moduleId>/messages/events/
    :return: The topic which has been uri-encoded
    """
    system_properties = {}
    if message_to_send.output_name:
        system_properties["$.on"] = message_to_send.output_name
    if message_to_send.message_id:
        system_properties["$.mid"] = message_to_send.message_id

    if message_to_send.correlation_id:
        system_properties["$.cid"] = message_to_send.correlation_id

    if message_to_send.user_id:
        system_properties["$.uid"] = message_to_send.user_id

    if message_to_send.to:
        system_properties["$.to"] = message_to_send.to

    if message_to_send.content_type:
        system_properties["$.ct"] = message_to_send.content_type

    if message_to_send.content_encoding:
        system_properties["$.ce"] = message_to_send.content_encoding

    if message_to_send.expiry_time_utc:
        system_properties["$.exp"] = (
            message_to_send.expiry_time_utc.isoformat()
            if isinstance(message_to_send.expiry_time_utc, date)
            else message_to_send.expiry_time_utc
        )

    system_properties_encoded = urllib.parse.urlencode(system_properties)
    topic += system_properties_encoded

    if message_to_send.custom_properties and len(message_to_send.custom_properties) > 0:
        topic += "&"
        user_properties_encoded = urllib.parse.urlencode(message_to_send.custom_properties)
        topic += user_properties_encoded

    return topic
