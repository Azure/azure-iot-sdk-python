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
    shared_access_key_name = d.get(SHARED_ACCESS_KEY_NAME)
    shared_access_key = d.get(SHARED_ACCESS_KEY)
    device_id = d.get(DEVICE_ID)
    x509 = d.get(X509)

    if shared_access_key and x509:
        raise ValueError("Invalid Connection String - Mixed authentication scheme")

    # This logic could be expanded to return the category of ConnectionString
    if host_name and device_id and (shared_access_key or x509):
        pass
    elif host_name and shared_access_key and shared_access_key_name:
        pass
    else:
        raise ValueError("Invalid Connection String - Incomplete")


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
