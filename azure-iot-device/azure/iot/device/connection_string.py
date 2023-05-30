# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains tools for working with Connection Strings"""

__all__ = ["ConnectionString"]

CS_DELIMITER = ";"
CS_VAL_SEPARATOR = "="

HOST_NAME = "HostName"
SHARED_ACCESS_KEY_NAME = "SharedAccessKeyName"
SHARED_ACCESS_KEY = "SharedAccessKey"
SHARED_ACCESS_SIGNATURE = "SharedAccessSignature"
DEVICE_ID = "DeviceId"
MODULE_ID = "ModuleId"
GATEWAY_HOST_NAME = "GatewayHostName"
X509 = "x509"

_valid_keys = [
    HOST_NAME,
    SHARED_ACCESS_KEY_NAME,
    SHARED_ACCESS_KEY,
    SHARED_ACCESS_SIGNATURE,
    DEVICE_ID,
    MODULE_ID,
    GATEWAY_HOST_NAME,
    X509,
]


class ConnectionString(object):
    """Key/value mappings for connection details.
    Uses the same syntax as dictionary
    """

    def __init__(self, connection_string):
        """Initializer for ConnectionString

        :param str connection_string: String with connection details provided by Azure
        :raises: ValueError if provided connection_string is invalid
        """
        self._dict = _parse_connection_string(connection_string)
        self._strrep = connection_string

    def __contains__(self, item):
        return item in self._dict

    def __getitem__(self, key):
        return self._dict[key]

    def __repr__(self):
        return self._strrep

    def get(self, key, default=None):
        """Return the value for key if key is in the dictionary, else default

        :param str key: The key to retrieve a value for
        :param str default: The default value returned if a key is not found
        :returns: The value for the given key
        """
        try:
            return self._dict[key]
        except KeyError:
            return default


def _parse_connection_string(connection_string):
    """Return a dictionary of values contained in a given connection string"""
    try:
        cs_args = connection_string.split(CS_DELIMITER)
    except (AttributeError, TypeError):
        raise TypeError("Connection String must be of type str")
    try:
        d = dict(arg.split(CS_VAL_SEPARATOR, 1) for arg in cs_args)
    except ValueError:
        # This occurs in an extreme edge case where a dictionary cannot be formed because there
        # is only 1 token after the split (dict requires two in order to make a key/value pair)
        raise ValueError("Invalid Connection String - Unable to parse")
    if len(cs_args) != len(d):
        # various errors related to incorrect parsing - duplicate args, bad syntax, etc.
        raise ValueError("Invalid Connection String - Unable to parse")
    if not all(key in _valid_keys for key in d.keys()):
        raise ValueError("Invalid Connection String - Invalid Key")
    _validate_keys(d)
    return d


def _validate_keys(d):
    """Raise ValueError if incorrect combination of keys in dict d"""
    host_name = d.get(HOST_NAME)
    shared_access_key = d.get(SHARED_ACCESS_KEY)
    shared_access_signature = d.get(SHARED_ACCESS_SIGNATURE)
    device_id = d.get(DEVICE_ID)
    x509 = d.get(X509)

    # Validate only one type of auth included
    auth_count = 0
    if shared_access_key:
        auth_count += 1
    if x509 and x509.lower() == "true":
        auth_count += 1
    if shared_access_signature:
        auth_count += 1

    if auth_count > 1:
        raise ValueError("Invalid Connection String - Mixed authentication scheme")
    elif auth_count < 1:
        raise ValueError("Invalid Connection String - No authentication scheme")

    # Validate connection details
    if not host_name or not device_id:
        raise ValueError("Invalid Connection String - Missing connection details")
