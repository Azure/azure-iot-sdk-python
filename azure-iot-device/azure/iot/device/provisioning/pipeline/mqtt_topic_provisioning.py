# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import six.moves.urllib as urllib

logger = logging.getLogger(__name__)

# NOTE: Whenever using standard URL encoding via the urllib.parse.quote() API
# make sure to specify that there are NO safe values (e.g. safe=""). By default
# "/" is skipped in encoding, and that is not desirable.
#
# DO NOT use urllib.parse.quote_plus(), as it turns ' ' characters into '+',
# which is invalid for MQTT publishes.
#
# DO NOT use urllib.parse.unquote_plus(), as it turns '+' characters into ' ',
# which is also invalid.


def _get_topic_base():
    """
    return the string that creates the beginning of all topics for DPS
    """
    return "$dps/registrations/"


def get_register_topic_for_subscribe():
    """
    :return: The topic string used to subscribe for receiving future responses from DPS.
    It is of the format "$dps/registrations/res/#"
    """
    return _get_topic_base() + "res/#"


def get_register_topic_for_publish(request_id):
    """
    :return: The topic string used to send a registration. It is of the format
    "$dps/registrations/PUT/iotdps-register/?$rid=<request_id>
    """
    return (_get_topic_base() + "PUT/iotdps-register/?$rid={request_id}").format(
        request_id=urllib.parse.quote(str(request_id), safe="")
    )


def get_query_topic_for_publish(request_id, operation_id):
    """
    :return: The topic string used to send a query. It is of the format
    "$dps/registrations/GET/iotdps-get-operationstatus/?$rid=<request_id>&operationId=<operation_id>
    """
    return (
        _get_topic_base()
        + "GET/iotdps-get-operationstatus/?$rid={request_id}&operationId={operation_id}"
    ).format(
        request_id=urllib.parse.quote(str(request_id), safe=""),
        operation_id=urllib.parse.quote(str(operation_id), safe=""),
    )


def _get_topic_for_response():
    """
    return the topic string used to publish telemetry
    """
    return _get_topic_base() + "res/"


def is_dps_response_topic(topic):
    """
    Topics for responses from DPS are of the following format:
    $dps/registrations/res/<statuscode>/?$<key1>=<value1>&<key2>=<value2>...&<keyN>=<valueN>
    :param topic: The topic string
    """
    if _get_topic_for_response() in topic:
        return True
    return False


def extract_properties_from_dps_response_topic(topic):
    """
    Topics for responses from DPS are of the following format:
    $dps/registrations/res/<statuscode>/?$<key1>=<value1>&<key2>=<value2>...&<keyN>=<valueN>
    Extract key=value pairs from the latter part of the topic.
    :param topic: The topic string
    :return: a dictionary of property keys mapped to property values.
    """
    topic_parts = topic.split("$")
    properties = topic_parts[2]

    # NOTE: we cannot use urllib.parse.parse_qs because it always decodes '+' as ' ',
    # and the behavior cannot be overriden. Must parse key/value pairs manually.

    if properties:
        key_value_pairs = properties.split("&")
        key_value_dict = {}
        for entry in key_value_pairs:
            pair = entry.split("=")
            key = urllib.parse.unquote(pair[0])
            value = urllib.parse.unquote(pair[1])
            if key_value_dict.get(key):
                raise ValueError("Duplicate keys in DPS response topic")
            else:
                key_value_dict[key] = value

    return key_value_dict


def extract_status_code_from_dps_response_topic(topic):
    """
    Topics for responses from DPS are of the following format:
    $dps/registrations/res/<statuscode>/?$<key1>=<value1>&<key2>=<value2>...&<keyN>=<valueN>
    Extract the status code part from the topic.
    :param topic: The topic string
    :return: The status code from the DPS response topic, as a string
    """
    POS_STATUS_CODE_IN_TOPIC = 3
    topic_parts = topic.split("$")
    url_parts = topic_parts[1].split("/")
    status_code = url_parts[POS_STATUS_CODE_IN_TOPIC]
    return urllib.parse.unquote(status_code)
