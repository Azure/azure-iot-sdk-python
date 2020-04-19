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

prefix = "$iotin:"


class PnpProperties(object):
    def __init__(self, top_key, **kwargs):
        self._top_key = top_key
        for name in kwargs:
            setattr(self, name, kwargs[name])

    def _to_dict(self):
        all_attrs = list((x for x in self.__dict__ if not x.startswith("_")))
        inner = {key: {"value": getattr(self, key)} for key in all_attrs}
        return {self._top_key: inner}


async def pnp_send_telemetry(device_client, device_name, telemetry_msg):
    """
    Coroutine to send telemetry from a PNP device. This method will take the raw telemetry message
    in the form of a dictionary from the user and then send message after creating a message object.
    :param device_client: The device client
    :param device_name: The name of the device like "sensor"
    :param telemetry_msg: A dictionary of items to be sent as telemetry.
    """
    msg = Message(json.dumps(telemetry_msg))
    msg.content_encoding = "utf-8"
    msg.content_type = "application/json"
    msg.custom_properties["$.sub"] = device_name
    print("Sent message")
    await device_client.send_message(msg)


async def pnp_update_property(device_client, interface_name, **prop_kwargs):
    """
    Coroutine that updates properties for a PNP device. This method will take in the user properties passed as
    key word arguments and then patches twin with a object constructed internally.
    :param device_client: The device client
    :param interface_name: The name of the interface. Like "sampleDeviceInfo".
    :param prop_kwargs: The user passed keyword arguments.
    """
    # Method 1 : Get only 1 top level dict with a complex class as value.
    # Will NOT WORK now as internal implementation does not support it yet
    # prop_dict = construct_properties_from_top_level_dict_and_classes(interface)
    # await device_client.patch_twin_reported_properties(prop_dict)

    # Method 2 : Get all multi level dictionary. WORKS.
    # prop_dict = construct_properties_from_all_dict_and_no_classes(interface)
    # await device_client.patch_twin_reported_properties(prop_dict)

    # METHOD 3
    key = prefix + interface_name
    prop_object = PnpProperties(key, **prop_kwargs)
    prop_dict = prop_object._to_dict()
    await device_client.patch_twin_reported_properties(prop_dict)


async def execute_listener(device_client, device_name, method_name=None, user_handler=None):
    """
    Coroutines for execution listeners. These will listen for command requests.
    They will take in a user provided handler and call the user provided handler
    according to the command request received.
    :param device_client: The device client
    :param device_name: The name of the device like "sensor"
    :param method_name: The specific method name to listen for. Eg could be "blink", "turnon" etc.
    :param user_handler: The user provided handler that needs to be executed after receiving "command requests"
    :return:
    """
    while True:
        if method_name:
            command_name = prefix + device_name + "*" + method_name
        else:
            command_name = None

        command_request = await device_client.receive_method_request(command_name)

        values = pnp_helper.retrieve_values_dict_from_payload(command_request)

        if user_handler:
            await user_handler(values)
        else:
            print("No handler provided to execute")

        if method_name:
            response_status = 200
        else:
            response_status = 404

        response_payload = pnp_helper.create_command_response_payload(method_name)
        command_response = MethodResponse.create_from_method_request(
            command_request, response_status, response_payload
        )

        try:
            await device_client.send_method_response(command_response)
        except Exception:
            print("responding to the {command} command failed".format(command=method_name))
