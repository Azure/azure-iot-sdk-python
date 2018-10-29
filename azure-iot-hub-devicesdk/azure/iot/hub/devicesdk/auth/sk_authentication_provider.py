# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import base64
import hmac
import hashlib
import time
from .authentication_provider import AuthenticationProvider
"""
The urllib, urllib2, and urlparse modules from Python 2 have been combined in the urllib package in Python 3
The six.moves.urllib package is a python version-independent location of the above functionality.
"""
import six.moves.urllib as urllib

DELIMITER = ";"
VALUE_SEPARATOR = "="

HOST_NAME = "HostName"
SHARED_ACCESS_KEY_NAME = "SharedAccessKeyName"
SHARED_ACCESS_KEY = "SharedAccessKey"
SHARED_ACCESS_SIGNATURE = "SharedAccessSignature"
DEVICE_ID = "DeviceId"
MODULE_ID = "ModuleId"
GATEWAY_HOST_NAME = "GatewayHostName"

_valid_keys = [
    HOST_NAME,
    SHARED_ACCESS_KEY_NAME,
    SHARED_ACCESS_KEY,
    SHARED_ACCESS_SIGNATURE,
    DEVICE_ID,
    MODULE_ID,
    GATEWAY_HOST_NAME,
]

_device_keyname_token_format = "SharedAccessSignature sr={}&sig={}&se={}&skn={}"
_device_token_format = "SharedAccessSignature sr={}&sig={}&se={}"


class SymmetricKeyAuthenticationProvider(AuthenticationProvider):
    """
    A Symmetric Key Authentication Provider. This provider needs to create the Shared Access Signature that would be needed to conenct to the IoT Hub.
    """
    def __init__(self, hostname, device_id, module_id, sas_token_str):
        """
        Constructor for SymmetricKey Authentication Provider
        """
        AuthenticationProvider.__init__(self, hostname, device_id, module_id)
        self.sas_token_str = sas_token_str

    def get_current_sas_token(self):
        """
        :return: The current shared access signature token
        """
        return self.sas_token_str

    @staticmethod
    def parse(connection_string):
        """
        This method creates a Symmetric Key Authentication Provider from a given connection string, and sets properties for each of the parsed
        fields in the string. Also validates the required properties of the connection string.
        :param connection_string: The semicolon-delimited string of 'name=value' pairs.
        The input may look like the following formations:-
        SharedAccessSignature sr=<resource_uri>&sig=<signature>&se=<expiry>
        SharedAccessSignature sr=<resource_uri>&sig=<signature>&skn=<keyname>&se=<expiry>
        :return: The Symmetric Key Authentication Provider constructed
        """
        cs_args = connection_string.split(DELIMITER)
        d = dict(arg.split(VALUE_SEPARATOR, 1) for arg in cs_args)
        if len(cs_args) != len(d):
            raise ValueError("Invalid Connection String - Unable to parse")
        if not all(key in _valid_keys for key in d.keys()):
            raise ValueError("Invalid Connection String - Invalid Key")

        _validate_keys(d)

        sas_token_str = _create_sas(d.get(HOST_NAME), d.get(DEVICE_ID), d.get(SHARED_ACCESS_KEY), d.get(MODULE_ID), d.get(SHARED_ACCESS_KEY_NAME))

        return SymmetricKeyAuthenticationProvider(d.get(HOST_NAME), d.get(DEVICE_ID), d.get(MODULE_ID), sas_token_str)


def _create_sas(hostname, device_id, shared_access_key, module_id=None, shared_access_key_name=None):
    resource_uri = hostname + "/devices/" + device_id
    if module_id:
        resource_uri += "/modules/" + module_id

    quoted_resource_uri = urllib.parse.quote_plus(resource_uri)
    expiry = int(time.time() + 3600)
    signature = _signature(quoted_resource_uri, expiry, shared_access_key)

    if shared_access_key_name:
        token = _device_keyname_token_format.format(
            quoted_resource_uri, signature, str(expiry), shared_access_key_name
        )
    else:
        token = _device_token_format.format(quoted_resource_uri, signature, str(expiry))
    return str(token)


def _signature(resource_uri, expiry, device_key):
    """
    Creates the base64-encoded HMAC-SHA256 hash of the string to sign. The string to sign is constructed from the
    resource_uri and expiry and the signing key is constructed from the device_key.
    :param resource_uri: the resource URI to encode into the token
    :param expiry: an integer value representing the number of seconds since the epoch 00:00:00 UTC on 1 January 1970 at which the token will expire.
    :param device_key: Symmetric key to use to create SasTokens.
    :return: The signature portion of the Sas Token.
    """
    try:
        message = (resource_uri + "\n" + str(expiry)).encode("utf-8")
        signing_key = base64.b64decode(device_key.encode("utf-8"))
        signed_hmac = hmac.HMAC(signing_key, message, hashlib.sha256)
        signature = urllib.parse.quote(base64.b64encode(signed_hmac.digest()))
    except (TypeError, base64.binascii.Error) as e:
        raise TypeError("Unable to build shared access signature from given values", e)
    return signature


def _validate_keys(d):
    """Raise ValueError if incorrect combination of keys
    """
    host_name = d.get(HOST_NAME)
    shared_access_key_name = d.get(SHARED_ACCESS_KEY_NAME)
    shared_access_key = d.get(SHARED_ACCESS_KEY)
    device_id = d.get(DEVICE_ID)

    if host_name and device_id and shared_access_key:
        pass
    elif host_name and shared_access_key and shared_access_key_name:
        pass
    else:
        raise ValueError("Invalid Connection String - Incomplete")
