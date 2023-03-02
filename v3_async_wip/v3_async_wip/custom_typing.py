# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from typing import Union, Dict, List, Tuple, Callable, Awaitable, TypeVar
from typing_extensions import TypedDict, ParamSpec

# import sys

P = ParamSpec("P")
T = TypeVar("T")

# if sys.version_info >= (3, 10):
#     # NOTE: Despite the backport of ParamSpec to pre-3.10 Python, it doesn't work when passing
#     # 0 arguments
#     FunctionOrCoroutine = Union[Callable[P, T], Callable[P, Awaitable[T]]]
# else:
#     # TODO: is there a better way to do this?
#     FunctionOrCoroutine = Any

FunctionOrCoroutine = Callable[P, Union[T, Awaitable[T]]]

# typing does not support recursion, so we must use forward references here (PEP484)
JSONSerializable = Union[
    Dict[str, "JSONSerializable"],
    List["JSONSerializable"],
    Tuple["JSONSerializable", ...],
    str,
    int,
    float,
    bool,
    None,
]
# TODO: verify that the JSON specification requires str as keys in dict. Not sure why that's defined here.


Twin = Dict[str, Dict[str, JSONSerializable]]
TwinPatch = Dict[str, JSONSerializable]


class DirectMethodParameters(TypedDict):
    methodName: str
    payload: JSONSerializable
    connectTimeoutInSeconds: int
    responseTimeoutInSeconds: int


class DirectMethodResult(TypedDict):
    status: int
    payload: str


class StorageInfo(TypedDict):
    correlationId: str
    hostName: str
    containerName: str
    blobName: str
    sasToken: str
