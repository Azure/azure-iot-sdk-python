
__all__ = [
    "ConnectionString"
    ]

CS_DELIMITER = ";"
CS_VAL_SEPARATOR = "="

HOST_NAME = "HostName"
SHARED_ACCESS_KEY_NAME = "SharedAccessKeyName"
SHARED_ACCESS_KEY = "SharedAccessKey"
SHARED_ACCESS_SIGNATURE = "SharedAccessSignature"
DEVICE_ID = "DeviceId"
MODULE_ID = "ModuleId"
GATEWAY_HOST_NAME = "GatewayHostName"

_valid_keys = [HOST_NAME, SHARED_ACCESS_KEY_NAME, SHARED_ACCESS_KEY, SHARED_ACCESS_SIGNATURE, DEVICE_ID, MODULE_ID, GATEWAY_HOST_NAME]


def _parse_connection_string(connection_string):
    """Return a dictionary of values contained in a given connection string
    """
    cs_args = connection_string.split(CS_DELIMITER)
    d = dict(arg.split(CS_VAL_SEPARATOR, 1) for arg in cs_args)
    if len(cs_args) != len(d):
        #various errors related to incorrect parsing - duplicate args, bad syntax, etc.
        raise ValueError("Invalid Connection String - Unable to parse")
    if not all(key in _valid_keys for key in d.keys()):
        raise ValueError("Invalid Connection String - Invalid Key")
    _validate_keys(d)
    return d


def _validate_keys(d):
    """Raise ValueError if incorrect combination of keys
    """
    host_name = d.get(HOST_NAME)
    shared_access_key_name = d.get(SHARED_ACCESS_KEY_NAME)
    shared_access_key = d.get(SHARED_ACCESS_KEY)
    device_id = d.get(DEVICE_ID)
    
    #This logic could be expanded to return the category of ConnectionString
    if (host_name and device_id and shared_access_key):
        pass
    elif (host_name and shared_access_key and shared_access_key_name):
        pass
    else:
        raise ValueError("Invalid Connection String - Incomplete")


class ConnectionString(object):
    """
    Key/value mappings with connection details. Uses the same syntax as dictionary

    Parameters:
    connection_string(str): string with connection details provided by Azure

    Raises:
    ValueError if provided connection_string is invalid
    """

    def __init__(self, connection_string):
        cs_args = connection_string.split(CS_DELIMITER)
        self._dict = _parse_connection_string(connection_string)
        self._strrep = connection_string

    def __getitem__(self, key):
        return self._dict[key]

    def __repr__(self):
        return self._strrep
