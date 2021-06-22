# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains utility functions to translate basic IoTHub objects
into PNP objects
"""

from .commands import Command


def method_request_to_command(method_request):
    """Given a MethodRequest, returns a Command"""
    pass
    # return Command(
    #     request_id=method_request.request_id,
    #     component_name="",
    #     command_name=method_request.name,
    #     payload=method_request.payload,
    # )


def twin_patch_to_writable_property(twin_patch):
    """Given a Twin Patch (dict), returns a WritableProperty"""
    pass
