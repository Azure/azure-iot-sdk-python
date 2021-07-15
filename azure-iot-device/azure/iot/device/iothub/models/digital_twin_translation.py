# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains utility functions to translate basic IoTHub objects
into Plug and Play objects
"""

from .methods import MethodResponse
from .commands import CommandRequest
from .properties import ClientPropertyCollection, ClientProperties


def method_request_to_command_request(method_request):
    """Given a MethodRequest, returns a CommandRequest"""
    method_name_tokens = method_request.name.split("*")
    if len(method_name_tokens) > 1:
        component_name = method_name_tokens[0]
        command_name = method_name_tokens[1]
    else:
        component_name = None
        command_name = method_name_tokens[0]

    return CommandRequest(
        request_id=method_request.request_id,
        component_name=component_name,
        command_name=command_name,
        payload=method_request.payload,
    )


def command_response_to_method_response(command_response):
    return MethodResponse(
        request_id=command_response.request_id,
        status=command_response.status,
        payload=command_response.payload,
    )


def twin_patch_to_client_property_collection(twin_patch):
    """Given a Twin Patch (`dict`), returns a `ClientPropertyCollection` object"""
    obj = ClientPropertyCollection()
    obj.backing_object = twin_patch
    return obj


def twin_to_client_properties(twin):
    """Given a Twin JSON, return a `ClientProperties` object"""
    obj = ClientProperties()
    obj.reported_from_device.backing_object = twin["reported"]
    obj.writable_properties_requests.backing_object = twin["desired"]
    return obj


def client_property_collection_to_twin_patch(client_property_collection):
    """Given a `ClientPropertyCollection` object, return a twin patch (`dict`)"""
    return client_property_collection.backing_object
