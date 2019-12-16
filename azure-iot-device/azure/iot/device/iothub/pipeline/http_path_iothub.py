# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import six.moves.urllib as urllib

logger = logging.getLogger(__name__)


def get_method_invoke_path(device_id, module_id=None):
    """
    :return: The path for invoking methods from one module to a device or module. It is of the format
    twins/uri_encode($device_id)/modules/uri_encode($module_id)/methods
    """
    if module_id:
        return "twins/{device_id}/modules/{module_id}/methods".format(
            device_id=urllib.parse.quote_plus(device_id),
            module_id=urllib.parse.quote_plus(module_id),
        )
    else:
        return "twins/{device_id}/methods".format(device_id=urllib.parse.quote_plus(device_id))


def get_storage_info_for_blob_path(device_id):
    """
    This does not take a module_id since get_storage_info_for_blob_path should only ever be invoked on device clients.

    :return: The path for getting the storage sdk credential information from IoT Hub. It is of the format
    devices/uri_encode($device_id)/files
    """
    return "devices/{}/files".format(urllib.parse.quote_plus(device_id))


def get_notify_blob_upload_status_path(device_id):
    """
    This does not take a module_id since get_notify_blob_upload_status_path should only ever be invoked on device clients.

    :return: The path for getting the storage sdk credential information from IoT Hub. It is of the format
    devices/uri_encode($device_id)/files/notifications
    """
    return "devices/{}/files/notifications".format(urllib.parse.quote_plus(device_id))
