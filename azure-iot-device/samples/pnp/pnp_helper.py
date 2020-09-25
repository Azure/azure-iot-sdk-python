# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""
This module knows how to convert device SDK functionality into a plug and play functionality.
These methods formats the telemetry, methods, properties to plug and play relevant telemetry,
command requests and pnp properties.
"""
from azure.iot.device import Message
import json


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
    Function to create telemetry for a plug and play device. This function will take the raw telemetry message
    in the form of a dictionary from the user and then create a plug and play specific message.
    :param telemetry_msg: A dictionary of items to be sent as telemetry.
    :param component_name: The name of the device like "sensor"
    :return: The message.
    """
    msg = Message(json.dumps(telemetry_msg))
    msg.content_encoding = "utf-8"
    msg.content_type = "application/json"
    if component_name:
        msg.custom_properties["$.sub"] = component_name
    return msg


def create_reported_properties(component_name=None, **prop_kwargs):
    """
    Function to create properties for a plug and play device. This method will take in the user properties passed as
    key word arguments and then creates plug and play specific reported properties.
    :param component_name: The name of the component. Like "deviceinformation" or "sdkinformation"
    :param prop_kwargs: The user passed keyword arguments which are the properties that the user wants to update.
    :return: The dictionary of properties.
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


def create_response_payload_with_status(command_request, method_name, create_user_response=None):
    """
    Helper method to create the payload for responding to a command request.
    This method is used for all method responses unless the user provides another
    method to construct responses to specific command requests.
    :param command_request: The command request for which the response is being sent.
    :param method_name: The method name for which we are responding to.
    :param create_user_response: Function to create user specific response.
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
        response_payload = create_user_response(command_request.payload)

    return (response_status, response_payload)


def create_reported_properties_from_desired(patch):
    """
    Function to create properties for a plug and play device. This method will take in the desired properties patch.
    and then create plug and play specific reported properties.
    :param patch: The patch of desired properties.
    :return: The dictionary of properties.
    """
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
    else:
        properties_dict = values

    return properties_dict
