# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains classes related to Digital Twin properties and components.
"""


class Component(object):
    def __init__(self, properties):
        self.properties = properties


class WritablePropertyResponse(object):
    def __init__(self, value, ac, ad, version):
        self.value = value
        self.ac = ac
        self.ad = ad
        self.version = version


class ClientProperties(object):
    def __init__(
        self,
        components={},
        properties={},
        version=None,
    ):
        self.components = components
        self.properties = properties
        self.version = version


class WritableProperty(object):
    def __init__(
        self,
        value=None,
        response=None,
    ):
        self.value = value
        self.response = response
