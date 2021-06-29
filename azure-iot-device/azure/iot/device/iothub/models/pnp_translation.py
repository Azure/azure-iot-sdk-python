# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains utility functions to translate basic IoTHub objects
into PNP objects
"""

from .commands import Command
from .properties import PropertiesCollection, ClientProperties


def method_request_to_command(method_request):
    """Given a MethodRequest, returns a Command"""
    pass
    # return Command(
    #     request_id=method_request.request_id,
    #     component_name="",
    #     command_name=method_request.name,
    #     payload=method_request.payload,
    # )


def twin_patch_to_properties_collection(twin_patch):
    """Given a Twin Patch (`dict`), returns a `PropertiesCollection` object"""
    obj = PropertiesCollection()
    obj.backing_object = twin_patch
    return obj


def twin_to_client_properties(twin):
    """Given a `Twin` object, return a `ClientPropertie`s object"""
    obj = ClientProperties()
    obj.backing_object = twin.reported_properties
    obj.writable_properties_requests.backing_object = twin.desired_properties


def properties_collection_to_twin_patch(properties_collection):
    """Given a `PropertiesCollection` object, return a twin patch (`dict`)"""
    return properties_collection.backing_object
