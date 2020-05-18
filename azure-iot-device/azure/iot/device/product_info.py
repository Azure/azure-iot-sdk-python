# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module is for creating product identifiers or agent strings for IotHub as well as Provisioning."""

# TODO: Should this be renamed to user_agent.py?

import platform
from azure.iot.device.constant import VERSION, IOTHUB_IDENTIFIER, PROVISIONING_IDENTIFIER

python_runtime = platform.python_version()
os_type = platform.system()
os_release = platform.version()
architecture = platform.machine()


def _get_common_user_agent():
    return "({python_runtime};{os_type} {os_release};{architecture})".format(
        python_runtime=python_runtime,
        os_type=os_type,
        os_release=os_release,
        architecture=architecture,
    )


def get_iothub_user_agent():
    """
    Create the user agent for IotHub
    """
    return "{iothub_iden}/{version}{common}".format(
        iothub_iden=IOTHUB_IDENTIFIER, version=VERSION, common=_get_common_user_agent()
    )


def get_provisioning_user_agent():
    """
    Create the user agent for Provisioning
    """
    return "{provisioning_iden}/{version}{common}".format(
        provisioning_iden=PROVISIONING_IDENTIFIER, version=VERSION, common=_get_common_user_agent()
    )
