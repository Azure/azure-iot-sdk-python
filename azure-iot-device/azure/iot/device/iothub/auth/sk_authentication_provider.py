# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import base64
import hmac
import hashlib
import logging
import six.moves.urllib as urllib
from .base_renewable_token_authentication_provider import BaseRenewableTokenAuthenticationProvider

logger = logging.getLogger(__name__)

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


class SymmetricKeyAuthenticationProvider(BaseRenewableTokenAuthenticationProvider):
    """
    A Symmetric Key Authentication Provider. This provider needs to create the i
    Shared Access Signature that would be needed to connect to the IoT Hub.
    """

    def __init__(
        self,
        hostname,
        device_id,
        module_id,
        shared_access_key,
        shared_access_key_name=None,
        gateway_hostname=None,
    ):
        """

        Constructor for SymmetricKey Authentication Provider
        """
        logger.info(
            "Using Shared Key authentication for {%s, %s, %s}", hostname, device_id, module_id
        )

        super(SymmetricKeyAuthenticationProvider, self).__init__(
            hostname=hostname, device_id=device_id, module_id=module_id
        )
        self.shared_access_key = shared_access_key
        self.shared_access_key_name = shared_access_key_name
        self.gateway_hostname = gateway_hostname
        self.ca_cert = None  # TODO: rename to ca_cert?

    @staticmethod
    def parse(connection_string):
        """
        This method creates a Symmetric Key Authentication Provider from a given connection string, and sets properties for each of the parsed
        fields in the string. Also validates the required properties of the connection string.
        :param connection_string: The semicolon-delimited string of 'name=value' pairs.
        The input may look like the following formations:-
        HostName=<hostname>;DeviceId=<device_id>;SharedAccessKey=<shared_access_key>
        HostName=<hostname>;DeviceId=<device_id>;SharedAccessKeyName=<shared_access_key_name>;SharedAccessKey=<shared_access_key>
        HostName=<hostname>;DeviceId=<device_id>;ModuleId=<module_id>;SharedAccessKey=<shared_access_key>
        :return: The Symmetric Key Authentication Provider constructed
        """
        try:
            cs_args = connection_string.split(DELIMITER)
            d = dict(arg.split(VALUE_SEPARATOR, 1) for arg in cs_args)
        except (ValueError, AttributeError):
            raise ValueError(
                "Connection string is required and should not be empty or blank and must be supplied as a string"
            )
        if len(cs_args) != len(d):
            raise ValueError("Invalid Connection String - Unable to parse")
        if not all(key in _valid_keys for key in d.keys()):
            raise ValueError("Invalid Connection String - Invalid Key")

        _validate_keys(d)

        return SymmetricKeyAuthenticationProvider(
            d.get(HOST_NAME),
            d.get(DEVICE_ID),
            d.get(MODULE_ID),
            d.get(SHARED_ACCESS_KEY),
            d.get(SHARED_ACCESS_KEY_NAME),
            d.get(GATEWAY_HOST_NAME),
        )

    def _sign(self, quoted_resource_uri, expiry):
        """
        Creates the base64-encoded HMAC-SHA256 hash of the string to sign. The string to sign is constructed from the
        resource_uri and expiry and the signing key is constructed from the device_key.
        :param  quoted_resource_uri: the resource URI to encode into the token, already URI-encoded
        :param expiry: an integer value representing the number of seconds since the epoch 00:00:00 UTC on 1 January 1970 at which the token will expire.
        :return: The signature portion of the Sas Token.
        """
        try:
            message = (quoted_resource_uri + "\n" + str(expiry)).encode("utf-8")
            signing_key = base64.b64decode(self.shared_access_key.encode("utf-8"))
            signed_hmac = hmac.HMAC(signing_key, message, hashlib.sha256)
            signature = urllib.parse.quote(base64.b64encode(signed_hmac.digest()))
        except (TypeError, base64.binascii.Error):
            raise ValueError("Unable to build shared access signature from given values")
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
