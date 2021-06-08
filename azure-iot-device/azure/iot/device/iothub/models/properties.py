# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains classes related to Digital Twin properties and components.
"""


class UndefinedValue(object):
    pass


_undefined = UndefinedValue()


class Component(object):
    def __init__(self, **kwargs):
        # fail if any kwargs are not value types
        self.property_values = dict(kwargs)

    def to_dict(self):
        pass


class Properties(object):
    def __init__(self, **kwargs):
        self.components = {k: v for k, v in dict(**kwargs) if type(k) in component_types}
        self.property_values = {k: v for k, v in dict(**kwargs) if type(k) in value_types}
        # assert all kwargs are components or values

    @classmethod
    def from_dict(cls, src_dict):
        # ignores __t and $version when enumerating the dict
        # fails if dict has extra levels or is otherwise not a valid PNP object
        pass

    def to_dict(self):
        pass


class WritablePropertyResponse(object):
    def __init__(self, value, ac, ad, version):
        self.value = value
        self.ac = ac
        self.ad = ad
        self.version = version

    def to_dict(self):
        pass


class WritableProperties(Properties):
    def __init__(self, **kwargs):
        super(WritableProperties, self).__init(**kwargs)
        self.version = 0

    @classmethod
    def from_dict(cls, src_dict):
        # call base class and also populate versionA
        pass


value_types = [int, str, float, WritablePropertyResponse]
component_types = [Component]
