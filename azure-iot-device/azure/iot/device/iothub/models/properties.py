# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains classes related to Digital Twin properties and components.
"""
from typing import Union, Dict, Any


class Component(object):
    def __init__(self, properties: Dict[str, Any] = {}):
        self.properties = properties


class WritablePropertyResponse(object):
    def __init__(self, value: Any, ac: int, ad: str, version: int) -> None:
        self.value = value
        self.ac = ac
        self.ad = ad
        self.version = version


class ClientProperties(object):
    def __init__(
        self,
        components: Dict[str, Component] = {},
        properties: Dict[str, Any] = {},
        version: Union[int, None] = None,
    ):
        self.components: Dict[str, Component] = components
        self.properties: Dict[str, Any] = properties
        self.version = version


class WritableProperty(object):
    def __init__(
        self,
        value: Any = None,
        response: WritablePropertyResponse = None,
    ):
        self.value = value
        self.response = response
