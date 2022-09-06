# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import base64
import hmac
import hashlib
import time
import six.moves.urllib as urllib

__all__ = ["SasToken", "SasTokenError"]


class SasTokenError(Exception):
    def __init__(self, message, cause=None):
        super(self.__class__, self).__init__(message)
        self.cause = cause


class SasToken(object):
    """
    Shared Access Signature Token used to authenticate a request

    Parameters:
    uri (str): URI of the resouce to be accessed
    key_name (str): Shared Access Key Name
    key (str): Shared Access Key (base64 encoded)
    ttl (int)[default 3600]: Time to live for the token, in seconds

    Data Attributes:
    expiry_time (int): Time that token will expire (in UTC, since epoch)
    ttl (int): Time to live for the token, in seconds

    Raises:
    SasTokenError if trying to build a SasToken from invalid values
    """

    _encoding_type = "utf-8"
    _service_token_format = "SharedAccessSignature sr={}&sig={}&se={}&skn={}"
    _device_token_format = "SharedAccessSignature sr={}&sig={}&se={}"

    def __init__(self, uri, key, key_name=None, ttl=3600):
        self._uri = urllib.parse.quote_plus(uri)
        self._key = key
        self._key_name = key_name
        self.ttl = ttl
        self.refresh()

    def __repr__(self):
        return self._token

    def refresh(self):
        """
        Refresh the SasToken lifespan, giving it a new expiry time
        """
        self.expiry_time = int(time.time() + self.ttl)
        self._token = self._build_token()

    def _build_token(self):
        """Buid SasToken representation

        Returns:
        String representation of the token
        """
        try:
            message = (self._uri + "\n" + str(self.expiry_time)).encode(self._encoding_type)
            signing_key = base64.b64decode(self._key.encode(self._encoding_type))
            signed_hmac = hmac.HMAC(signing_key, message, hashlib.sha256)
            signature = urllib.parse.quote(base64.b64encode(signed_hmac.digest()))
        except (TypeError, base64.binascii.Error) as e:
            raise SasTokenError("Unable to build SasToken from given values", e)
        if self._key_name:
            token = self._service_token_format.format(
                self._uri, signature, str(self.expiry_time), self._key_name
            )
        else:
            token = self._device_token_format.format(self._uri, signature, str(self.expiry_time))
        return token
