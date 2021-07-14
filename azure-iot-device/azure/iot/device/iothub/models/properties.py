# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains classes related to Digital Twin properties and components.
"""


def WritablePropertyResponse(value, ack_code, ack_description, ack_version):
    return {
        "value": value,
        "ac": ack_code,
        "ad": ack_description,
        "av": ack_version,
    }


class ClientPropertyCollection(object):
    def __init__(self):
        self.backing_object = {}

    @property
    def version(self):
        return self.backing_object.get("$version")

    def set_property(self, property_name, property_value):
        self.backing_object[property_name] = property_value

    def get_property(self, property_name, default=None):
        return self.backing_object.get(property_name, default)

    def set_component_property(self, component_name, property_name, property_value):
        if component_name not in self.backing_object:
            self.backing_object[component_name] = {"__t": "c"}
        self.backing_object[component_name][property_name] = property_value

    def get_component_property(self, component_name, property_name, default=None):
        return self.backing_object.get(component_name, {}).get(property_name, default)


class ClientProperties(object):
    def __init__(self):
        self.writable_properties_requests = ClientPropertyCollection()
        self.reported_from_device = ClientPropertyCollection()
