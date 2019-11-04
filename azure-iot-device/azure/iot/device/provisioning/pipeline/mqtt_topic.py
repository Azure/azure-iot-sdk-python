# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import six.moves.urllib as urllib

logger = logging.getLogger(__name__)


def _get_topic_base():
    """
    return the string that creates the beginning of all topics for DPS
    """
    return "$dps/registrations/"


def get_topic_for_subscribe():
    """
    return the topic string used to subscribe for receiving future responses from DPS
    """
    return _get_topic_base() + "res/#"


def get_topic_for_register(method, request_id):
    """
    return the topic string used to publish telemetry
    """
    return (_get_topic_base() + "{method}/iotdps-register/?$rid={request_id}").format(
        method=method, request_id=request_id
    )


def get_topic_for_query(method, request_id, operation_id):
    """
    :return: The topic for cloud to device messages.It is of the format
    "devices/<deviceid>/messages/devicebound/#"
    """
    return (
        _get_topic_base()
        + "{method}/iotdps-get-operationstatus/?$rid={request_id}&operationId={operation_id}"
    ).format(method=method, request_id=request_id, operation_id=operation_id)


def get_topic_for_response():
    """
    return the topic string used to publish telemetry
    """
    return _get_topic_base() + "res/"


def is_query_topic(topic):
    if "GET/iotdps-get-operationstatus" in topic:
        return True
    return False


def is_dps_response_topic(topic):
    """
    Topics for responses from DPS are of the following format:
    $dps/registrations/res/<statuscode>/?$<key1>=<value1>&<key2>=<value2>&<key3>=<value3>
    :param topic: The topic string
    """
    if get_topic_for_response() in topic:
        return True
    return False


def extract_properties_from_topic(topic):
    """
    Topics for responses from DPS are of the following format:
    $dps/registrations/res/<statuscode>/?$<key1>=<value1>&<key2>=<value2>&<key3>=<value3>
    Extract key=value pairs from the latter part of the topic.
    :param topic: The topic string
    :return key_values_dict : a dictionary of key mapped to a list of values.
    """
    topic_parts = topic.split("$")
    key_value_dict = urllib.parse.parse_qs(topic_parts[2])
    return key_value_dict


def extract_status_code_from_topic(topic):
    """
    Topics for responses from DPS are of the following format:
    $dps/registrations/res/<statuscode>/?$<key1>=<value1>&<key2>=<value2>&<key3>=<value3>
    Extract the status code part from the topic.
    :param topic: The topic string
    """
    POS_STATUS_CODE_IN_TOPIC = 3
    topic_parts = topic.split("$")
    url_parts = topic_parts[1].split("/")
    status_code = url_parts[POS_STATUS_CODE_IN_TOPIC]
    return status_code
