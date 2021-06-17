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
import json
from azure.iot.device import Properties, Component, WritablePropertyResponse


# TODO: this talk of "reported" and "desired" is not using the right PNP lingo
def create_reported_properties_from_desired(writable_props):
    """
    Function to create properties for a plug and play device. This method will take in the desired properties patch.
    and then create plug and play specific reported properties.
    :param patch: The patch of desired properties.
    :return: The dictionary of properties.
    """
    print("the data in the desired properties patch was: {}".format(writable_props.to_dict()))

    # TODO: this assumes the writable props are not from the root and only have a single component
    component_name = list(writable_props.components.keys())[0]
    values = writable_props.components[component_name].property_values
    print("Values received are :-")
    print(values)

    reported_properties = Properties()
    reported_properties.components[component_name] = Component()

    for prop_name, prop_value in values.items():
        reported_properties.components[component_name].property_values[
            prop_name
        ] = WritablePropertyResponse(
            ac=200, ad="Successfully executed patch", av=writable_props.version, value=prop_value
        )

    return reported_properties
