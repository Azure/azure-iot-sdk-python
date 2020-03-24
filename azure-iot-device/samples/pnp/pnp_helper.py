# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""
This module will include all the helper methods.
"""


def retrieve_values_dict_from_payload(command_request):
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


# TODO : Ask if any other response payload needs to be constructed.
def create_command_response_payload(method_name):
    """
    Helper method to create the payload for responding to a command request.
    :param method_name: The method name for which we are responding to.
    :return: The rersponse payload.
    """
    result = True if method_name else False
    data = "executed " + method_name if method_name else "unknown method"
    response_payload = {"result": result, "data": data}
    print(response_payload)
    return response_payload
