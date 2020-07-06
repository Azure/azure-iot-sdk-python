# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""
This module knows how to convert device SDK functionality into a PNP functionality.
These methods formats the telemetry, methods, properties to PNP relevant telemetry,
command requests and pnp properties.
"""
from azure.iot.device import Message, MethodResponse
import json
import pnp_helper
import asyncio


class PnpProperties(object):
    def __init__(self, top_key, **kwargs):
        self._top_key = top_key
        for name in kwargs:
            setattr(self, name, kwargs[name])

    def _to_value_dict(self):
        all_attrs = list((x for x in self.__dict__ if x != "_top_key"))
        inner = {key: {"value": getattr(self, key)} for key in all_attrs}
        return inner

    def _to_simple_dict(self):
        all_simple_attrs = list((x for x in self.__dict__ if x != "_top_key"))
        inner = {key: getattr(self, key) for key in all_simple_attrs}
        return inner


def create_telemetry(telemetry_msg, component_name=None):
    """
    Coroutine to send telemetry from a PNP device. This method will take the raw telemetry message
    in the form of a dictionary from the user and then send message after creating a message object.
    :param device_client: The device client
    :param component_name: The name of the device like "sensor"
    :param telemetry_msg: A dictionary of items to be sent as telemetry.
    """
    msg = Message(json.dumps(telemetry_msg))
    msg.content_encoding = "utf-8"
    msg.content_type = "application/json"
    if component_name:
        msg.custom_properties["$.sub"] = component_name
    return msg


def create_reported_properties(component_name=None, **prop_kwargs):
    """
    Coroutine that updates properties for a PNP device. This method will take in the user properties passed as
    key word arguments and then patches twin with a object constructed internally.
    :param device_client: The device client
    :param component_name: The name of the component. Like "deviceinformation" or "sdkinformation"
    :param prop_kwargs: The user passed keyword arguments which are the properties that the user wants to update.
    """
    if component_name:
        print("Updating pnp properties for {component_name}".format(component_name=component_name))
    else:
        print("Updating pnp properties for root interface")
    prop_object = PnpProperties(component_name, **prop_kwargs)
    inner_dict = prop_object._to_simple_dict()
    if component_name:
        inner_dict["__t"] = "c"
        prop_dict = {}
        prop_dict[component_name] = inner_dict
    else:
        prop_dict = inner_dict

    print(prop_dict)
    return prop_dict


def retrieve_values_from_command_request(command_request):
    """
    Helper method to retrieve the values portion of the response payload.
    :param command_request: The full dictionary of the command request which contains the payload.
    :return: The values dictionary from the payload.
    """
    pnp_key = "commandRequest"
    values = {}
    if not command_request.payload:
        print("Payload was empty.")
    elif pnp_key not in command_request.payload:
        print("There was no payload for {key}.".format(key=pnp_key))
    else:
        command_request_payload = command_request.payload
        values = command_request_payload[pnp_key]["value"]
    return values


def create_response_payload_with_status(command_request, method_name, create_user_response=None):
    """
    Helper method to create the payload for responding to a command request.
    This method is used for all methid responses unless the user provides another
     method to construct responses to specific command requests.
    :param method_name: The method name for which we are responding to.
    :return: The response payload.
    """
    if method_name:
        response_status = 200
    else:
        response_status = 404

    if not create_user_response:
        result = True if method_name else False
        data = "executed " + method_name if method_name else "unknown method"
        response_payload = {"result": result, "data": data}
    else:
        # TODO should npt need this once the command request envelope is removed.
        request_values = retrieve_values_from_command_request(command_request)
        response_payload = create_user_response(request_values)

    return (response_status, response_payload)


def create_reported_properties_from_desired(patch):
    print("the data in the desired properties patch was: {}".format(patch))

    ignore_keys = ["__t", "$version"]
    component_prefix = list(patch.keys())[0]
    values = patch[component_prefix]
    print("Values received are :-")
    print(values)

    version = patch["$version"]
    inner_dict = {}

    for prop_name, prop_value in values.items():
        if prop_name in ignore_keys:
            continue
        else:
            inner_dict["ac"] = 200
            inner_dict["ad"] = "Successfully executed patch"
            inner_dict["av"] = version
            inner_dict["value"] = prop_value
            values[prop_name] = inner_dict

    properties_dict = dict()
    if component_prefix:
        properties_dict[component_prefix] = values
        # print(iotin_dict)
    else:
        properties_dict = values

    return properties_dict
