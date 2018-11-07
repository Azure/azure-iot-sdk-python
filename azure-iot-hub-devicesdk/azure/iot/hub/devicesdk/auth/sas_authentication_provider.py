# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import logging
from .authentication_provider import AuthenticationProvider
"""
The urllib, urllib2, and urlparse modules from Python 2 have been combined in the urllib package in Python 3
The six.moves.urllib package is a python version-independent location of the above functionality.
"""
import six.moves.urllib as urllib

logger = logging.getLogger(__name__)

URI_SEPARATOR = "/"
DELIMITER = "&"
VALUE_SEPARATOR = "="
PARTS_SEPARATOR = " "

SIGNATURE = "sig"
SHARED_ACCESS_KEY_NAME = "skn"
RESOURCE_URI = "sr"
EXPIRY = "se"

_valid_keys = [
    SIGNATURE,
    SHARED_ACCESS_KEY_NAME,
    RESOURCE_URI,
    EXPIRY
]


class SharedAccessSignatureAuthenticationProvider(AuthenticationProvider):
    """
    The Shared Access Signature Authentication Provider.
    This provider already contains the sas token which will be needed to authenticate with The IoT hub.
    """
    def __init__(self, hostname, device_id, module_id, sas_token_str):
        """
        Constructor for Shared Access Signature Authentication Provider
        """
        logger.info("Using SAS authentication for (%s,%s) ", device_id, module_id)
        AuthenticationProvider.__init__(self, hostname, device_id, module_id)
        self.sas_token_str = sas_token_str

    def get_current_sas_token(self):
        """
        :return: the string representation of the current Shared Access Signature
        """
        return self.sas_token_str

    @staticmethod
    def parse(sas_token_str):
        """
        This method creates a Shared Access Signature Authentication Provider from a string, and sets properties for each of the parsed
        fields in the string. Also validates the required properties of the shared access signature.
        :param sas_token_str: The ampersand-delimited string of 'name=value' pairs.
        The input may look like the following formations:-
        SharedAccessSignature sr=<resource_uri>&sig=<signature>&se=<expiry>
        SharedAccessSignature sr=<resource_uri>&sig=<signature>&skn=<keyname>&se=<expiry>
        :return: The Shared Access Signature Authentication Provider constructed
        """
        parts = sas_token_str.split(PARTS_SEPARATOR)
        if len(parts) != 2:
            raise ValueError(
                "The Shared Access Signature must be of the format 'SharedAccessSignature sr=<resource_uri>&sig=<signature>&se=<expiry>' or/and it can additionally contain an optional skn=<keyname> name=value pair.")

        sas_args = parts[1].split(DELIMITER)
        d = dict(arg.split(VALUE_SEPARATOR, 1) for arg in sas_args)
        if len(sas_args) != len(d):
            raise ValueError("Invalid Shared Access Signature - Unable to parse")
        if not all(key in _valid_keys for key in d.keys()):
            raise ValueError(
                "Invalid keys in Shared Access Signature. The valid keys are sr, sig, se and an optional skn.")

        _validate_required_keys(d)

        unquoted_resource_uri = urllib.parse.unquote_plus(d.get(RESOURCE_URI))
        url_segments = unquoted_resource_uri.split(URI_SEPARATOR)

        module_id = None
        hostname = url_segments[0]
        device_id = url_segments[2]

        if len(url_segments) > 4:
            module_id = url_segments[4]

        return SharedAccessSignatureAuthenticationProvider(hostname, device_id, module_id, sas_token_str)


def _validate_required_keys(d):
    """
    Validates that required keys are present.
    Raise ValueError if incorrect combination of keys
    """
    resource_uri = d.get(RESOURCE_URI)
    signature = d.get(SIGNATURE)
    expiry = d.get(EXPIRY)

    if resource_uri and signature and expiry:
        pass
    else:
        raise ValueError("Invalid Shared Access Signature. It must be of the format 'SharedAccessSignature sr=<resource_uri>&sig=<signature>&se=<expiry>' or/and it can additionally contain an optional skn=<keyname> name=value pair.")


