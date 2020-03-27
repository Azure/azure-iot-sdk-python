# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
from datetime import date
import six.moves.urllib as urllib
from azure.iot.device.common import version_compat

logger = logging.getLogger(__name__)

# NOTE: Whenever using standard URL encoding via the urllib.parse.quote() API
# make sure to specify that there are NO safe values (e.g. safe=""). By default
# "/" is skipped in encoding, and that is not desirable.
#
# DO NOT use urllib.parse.quote_plus(), as it turns ' ' characters into '+',
# which is invalid for MQTT publishes.
#
# DO NOT use urllib.parse.unquote_plus(). as it turns '+' characters into ' ',
# which is invalid.


def _get_topic_base(device_id, module_id=None):
    """
    return the string that is at the beginning of all topics for this
    device/module
    """

    topic = "devices/" + urllib.parse.quote(device_id, safe="")
    if module_id:
        topic = topic + "/modules/" + urllib.parse.quote(module_id, safe="")
    return topic


def get_c2d_topic_for_subscribe(device_id):
    """
    :return: The topic for cloud to device messages.It is of the format
    "devices/<deviceid>/messages/devicebound/#"
    """
    return _get_topic_base(device_id) + "/messages/devicebound/#"


def get_input_topic_for_subscribe(device_id, module_id):
    """
    :return: The topic for input messages. It is of the format
    "devices/<deviceId>/modules/<moduleId>/inputs/#"
    """
    return _get_topic_base(device_id, module_id) + "/inputs/#"


def get_method_topic_for_subscribe():
    """
    :return: The topic for ALL incoming methods. It is of the format
    "$iothub/methods/POST/#"
    """
    return "$iothub/methods/POST/#"


def get_twin_response_topic_for_subscribe():
    """
    :return: The topic for ALL incoming twin responses. It is of the format
    "$iothub/twin/res/#"
    """
    return "$iothub/twin/res/#"


def get_twin_patch_topic_for_subscribe():
    """
    :return: The topic for ALL incoming twin patches. It is of the format
    "$iothub/twin/PATCH/properties/desired/#
    """
    return "$iothub/twin/PATCH/properties/desired/#"


def get_telemetry_topic_for_publish(device_id, module_id):
    """
    return the topic string used to publish telemetry
    """
    return _get_topic_base(device_id, module_id) + "/messages/events/"


def get_method_topic_for_publish(request_id, status):
    """
    :return: The topic for publishing method responses. It is of the format
    "$iothub/methods/res/<status>/?$rid=<requestId>

    Note that all inputs MUST be strings (not ints!)
    """
    return "$iothub/methods/res/{status}/?$rid={request_id}".format(
        status=urllib.parse.quote(status, safe=""),
        request_id=urllib.parse.quote(request_id, safe=""),
    )


# NOTE: Consider splitting this into separate logic for Twin Requests / Twin Patches
# This is the only method that is shared. Would probably simplify code if it was split.
# Please consider refactoring.
def get_twin_topic_for_publish(method, resource_location, request_id):
    """
    :return: The topic for publishing twin requests / patches. It is of the format
    "$iothub/twin/<method><resourceLocation>?$rid=<requestId>

    Note that all inputs MUST be strings (not ints!)
    """
    return "$iothub/twin/{method}{resource_location}?$rid={request_id}".format(
        method=method,
        resource_location=resource_location,
        request_id=urllib.parse.quote(request_id, safe=""),
    )


def is_c2d_topic(topic, device_id):
    """
    Topics for c2d message are of the following format:
    devices/<deviceId>/messages/devicebound
    :param topic: The topic string
    """
    if "devices/{}/messages/devicebound".format(urllib.parse.quote(device_id, safe="")) in topic:
        return True
    return False


def is_input_topic(topic, device_id, module_id):
    """
    Topics for inputs are of the following format:
    devices/<deviceId>/modules/<moduleId>/inputs/<inputName>
    :param topic: The topic string
    """
    if not device_id or not module_id:
        return False
    if (
        "devices/{}/modules/{}/inputs/".format(
            urllib.parse.quote(device_id, safe=""), urllib.parse.quote(module_id, safe="")
        )
        in topic
    ):
        return True
    return False


def is_method_topic(topic):
    """
    Topics for methods are of the following format:
    "$iothub/methods/POST/{method name}/?$rid={request id}"

    :param str topic: The topic string.
    """
    if "$iothub/methods/POST" in topic:
        return True
    return False


def is_twin_response_topic(topic):
    """Topics for twin responses are of the following format:
    $iothub/twin/res/{status}/?$rid={rid}

    :param str topic: The topic string
    """
    return topic.startswith("$iothub/twin/res/")


def is_twin_desired_property_patch_topic(topic):
    """Topics for twin desired property patches are of the following format:
    $iothub/twin/PATCH/properties/desired

    :param str topic: The topic string
    """
    return topic.startswith("$iothub/twin/PATCH/properties/desired")


def get_input_name_from_topic(topic):
    """
    Extract the input channel from the topic name
    Topics for inputs are of the following format:
    devices/<deviceId>/modules/<moduleId>/inputs/<inputName>

    :param topic: The topic string
    """
    parts = topic.split("/")
    if len(parts) > 5 and parts[4] == "inputs":
        return urllib.parse.unquote(parts[5])
    else:
        raise ValueError("topic has incorrect format")


def get_method_name_from_topic(topic):
    """
    Extract the method name from the method topic.
    Topics for methods are of the following format:
    "$iothub/methods/POST/{method name}/?$rid={request id}"

    :param str topic: The topic string
    """
    parts = topic.split("/")
    if is_method_topic(topic) and len(parts) >= 4:
        return urllib.parse.unquote(parts[3])
    else:
        raise ValueError("topic has incorrect format")


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


def get_twin_request_id_from_topic(topic):
    """
    Extract the Request ID (RID) from the twin response topic.
    Topics for twin response are in the following format:
    "$iothub/twin/res/{status}/?$rid={rid}"

    :param str topic: The topic string
    :raises: ValueError if topic has incorrect format
    :returns: request id from topic string
    """
    parts = topic.split("/")
    if is_twin_response_topic(topic) and len(parts) >= 4:
        properties = _extract_properties(topic.split("?")[1])
        return properties["rid"]
    else:
        raise ValueError("topic has incorrect format")


def get_twin_status_code_from_topic(topic):
    """
    Extract the status code from the twin response topic.
    Topics for twin response are in the following format:
    "$iothub/twin/res/{status}/?$rid={rid}"

    :param str topic: The topic string
    :raises: ValueError if the topic has incorrect format
    :returns status code from topic string
    """
    parts = topic.split("/")
    if is_twin_response_topic(topic) and len(parts) >= 4:
        return parts[3]
    else:
        raise ValueError("topic has incorrect format")


def extract_message_properties_from_topic(topic, message_received):
    """
    Extract key=value pairs from custom properties and set the properties on the received message.
    :param topic: The topic string
    :param message_received: The message received with the payload in bytes
    """

    parts = topic.split("/")
    # Input Message Topic
    if len(parts) > 4 and parts[4] == "inputs":
        if len(parts) > 6:
            properties = parts[6]
        else:
            properties = None
    # C2D Message Topic
    elif len(parts) > 3 and parts[3] == "devicebound":
        if len(parts) > 4:
            properties = parts[4]
        else:
            properties = None
    else:
        raise ValueError("topic has incorrect format")

    # We do not want to extract values corresponding to these keys
    ignored_extraction_values = ["iothub-ack", "$.to"]

    if properties:
        key_value_pairs = properties.split("&")

        for entry in key_value_pairs:
            pair = entry.split("=")
            key = urllib.parse.unquote(pair[0])
            value = urllib.parse.unquote(pair[1])

            if key in ignored_extraction_values:
                continue
            elif key == "$.mid":
                message_received.message_id = value
            elif key == "$.cid":
                message_received.correlation_id = value
            elif key == "$.uid":
                message_received.user_id = value
            elif key == "$.ct":
                message_received.content_type = value
            elif key == "$.ce":
                message_received.content_encoding = value
            elif key == "$.exp":
                message_received.expiry_time_utc = value
            else:
                message_received.custom_properties[key] = value


def encode_message_properties_in_topic(message_to_send, topic):
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
    system_properties = []
    if message_to_send.output_name:
        system_properties.append(("$.on", message_to_send.output_name))
    if message_to_send.message_id:
        system_properties.append(("$.mid", message_to_send.message_id))

    if message_to_send.correlation_id:
        system_properties.append(("$.cid", message_to_send.correlation_id))

    if message_to_send.user_id:
        system_properties.append(("$.uid", message_to_send.user_id))

    if message_to_send.content_type:
        system_properties.append(("$.ct", message_to_send.content_type))

    if message_to_send.content_encoding:
        system_properties.append(("$.ce", message_to_send.content_encoding))

    if message_to_send.iothub_interface_id:
        system_properties.append(("$.ifid", message_to_send.iothub_interface_id))

    if message_to_send.expiry_time_utc:
        system_properties.append(
            (
                "$.exp",
                message_to_send.expiry_time_utc.isoformat()
                if isinstance(message_to_send.expiry_time_utc, date)
                else message_to_send.expiry_time_utc,
            )
        )

    system_properties_encoded = version_compat.urlencode(
        system_properties, quote_via=urllib.parse.quote
    )
    topic += system_properties_encoded

    if message_to_send.custom_properties and len(message_to_send.custom_properties) > 0:
        if system_properties and len(system_properties) > 0:
            topic += "&"
        # Convert the custom properties to a sorted list in order to ensure the
        # resulting ordering in the topic string is consistent across versions of Python
        custom_prop_seq = list(message_to_send.custom_properties.items())
        custom_prop_seq.sort()
        user_properties_encoded = version_compat.urlencode(
            custom_prop_seq, quote_via=urllib.parse.quote
        )
        topic += user_properties_encoded

    return topic


def _extract_properties(properties_str):
    """Return a dictionary of properties from a string in the format
    ${key1}={value1}&${key2}={value2}...&${keyn}={valuen}
    """
    d = {}
    kv_pairs = properties_str.split("&")

    for entry in kv_pairs:
        pair = entry.split("=")
        key = urllib.parse.unquote(pair[0]).lstrip("$")
        value = urllib.parse.unquote(pair[1])
        d[key] = value

    return d
