# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import urllib.parse
from typing import Dict

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


def get_response_topic_for_subscribe() -> str:
    """
    :return: The topic string used to subscribe for receiving registration responses from DPS.
    It is of the format "$dps/registrations/res/#"
    """
    return "$dps/registrations/res/#"


def get_register_topic_for_publish(request_id: str) -> str:
    """
    :return: The topic string used to send a registration. It is of the format
    "$dps/registrations/PUT/iotdps-register/?$rid=<request_id>
    """
    return "$dps/registrations/PUT/iotdps-register/?$rid={request_id}".format(
        request_id=urllib.parse.quote(str(request_id), safe="")
    )


def get_status_query_topic_for_publish(request_id: str, operation_id: str) -> str:
    """
    :return: The topic string used to send an operation status query. It is of the format
    "$dps/registrations/GET/iotdps-get-operationstatus/?$rid=<request_id>&operationId=<operation_id>
    """
    return "$dps/registrations/GET/iotdps-get-operationstatus/?$rid={request_id}&operationId={operation_id}".format(
        request_id=urllib.parse.quote(str(request_id), safe=""),
        operation_id=urllib.parse.quote(str(operation_id), safe=""),
    )


def extract_properties_from_response_topic(topic: str) -> Dict[str, str]:
    """Extract key/value pairs from the response topic, returning them as a dictionary.
    If a key has no matching value, the value will be set to empty string.

    Topics for responses from DPS are of the following format:
    $dps/registrations/res/<statuscode>/?$<key1>=<value1>&<key2>=<value2>...&<keyN>=<valueN>

    :param topic: The topic string
    :return: a dictionary of property keys mapped to property values.
    """
    parts = topic.split("/")
    if topic.startswith("$dps/registrations/res/") and len(parts) == 5:
        properties_string = parts[4].split("?")[1]
        return _extract_properties(properties_string)
    else:
        raise ValueError("topic has incorrect format")


def extract_status_code_from_response_topic(topic):
    """
    Extract the status code from the response topic

    Topics for responses from DPS are of the following format:
    $dps/registrations/res/<statuscode>/?$<key1>=<value1>&<key2>=<value2>...&<keyN>=<valueN>
    Extract the status code part from the topic.
    :param topic: The topic string
    :return: The status code from the DPS response topic, as a string
    """
    parts = topic.split("/")
    if topic.startswith("$dps/registrations/res/") and len(parts) >= 4:
        return urllib.parse.unquote(parts[3])
    else:
        raise ValueError("topic has incorrect format")


# NOTE: This is duplicated from mqtt_topic_iothub. If changing, change there too.
# Consider putting this in a separate module at some point.
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
