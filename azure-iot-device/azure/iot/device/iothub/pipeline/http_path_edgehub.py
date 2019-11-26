# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
from datetime import date
import six.moves.urllib as urllib

logger = logging.getLogger(__name__)


def _get_path_base(device_id, module_id):
    """
    return the string that is at the beginning of all topics for this
    device/module
    """

    if module_id:
        return "devices/" + device_id + "/modules/" + module_id
    else:
        return "devices/" + device_id


def get_method_invoke_path(device_id, module_id):
    """
    return the path string used to get the info for uploading via
    Method Invoke API
    """
    return "twins/" + _get_path_base(device_id, module_id)


# def get_telemetry_topic_for_publish(device_id, module_id):
#     """
#     return the topic string used to publish telemetry
#     """
#     return _get_path_base(device_id, module_id) + "/messages/events/"


# # TODO: leverage this helper in all property extraction functions
# def _extract_properties(properties_str):
#     """Return a dictionary of properties from a string in the format
#     ${key1}={value1}&${key2}={value2}&...{keyn}={valuen}
#     """
#     d = {}
#     kv_pairs = properties_str.split("&")

#     for entry in kv_pairs:
#         pair = entry.split("=")
#         key = urllib.parse.unquote_plus(pair[0]).lstrip("$")
#         value = urllib.parse.unquote_plus(pair[1])
#         d[key] = value

#     return d
