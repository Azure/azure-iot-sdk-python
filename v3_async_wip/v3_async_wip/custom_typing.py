# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from typing import Union, Dict, List, Tuple, Any

# typing does not support recursion, so unfortunately, we have to use Any for elements of
# collections rather than another reference to JSONSerializable. This means that this type isn't
# exactly accurate, as some nested object that can't be serialized would pass static analysis
JSONSerializable = Union[Dict[str, Any], List[Any], Tuple[Any, ...], str, int, float, bool, None]
# TODO: verify that the JSON specification requires str as keys in dict. Not sure why that's defined here.

Twin = Dict[str, Dict[str, JSONSerializable]]
TwinPatch = Dict[str, JSONSerializable]
