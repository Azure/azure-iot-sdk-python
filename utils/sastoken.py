# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import time
import base64
import hmac
import hashlib

import six.moves.urllib as urllib


class SasTokenError(Exception):
    
    def __init__(self, message, cause=None):
        super(self.__class__, self).__init__(message)
        self.cause = cause


class SasTokenFactory(object):
    """
    Factory that generates SasToken objects

    Parameters:
    resource_uri (str): URI of the resource to be accessed
    key_name (str): Shared Access Key Name
    key (str): Shared Access Key
    custom_ttl (int)[optional]: Custom time to live for tokens, in seconds

    Data Attributes:
    Same as Parameters
    """
    
    def __init__(self, resource_uri, key_name, key, custom_ttl=None):
        self.resource_uri = resource_uri
        self.key_name = key_name
        self.key = key
        self.custom_ttl = custom_ttl

    def generate_sastoken(self):
        """
        Generate a new SasToken object

        Returns:
        SasToken
        """
        if self.custom_ttl:
            token =  SasToken(self.resource_uri, self.key_name, self.key, self.ttl)
        else:
            token = SasToken(self.resource_uri, self.key_name, self.key)

        return token


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
    """

    _encoding_type = 'utf-8'
    _token_format = "SharedAccessSignature sr={}&sig={}&se={}&skn={}"

    def __init__(self, uri, key_name, key, ttl=3600):
        self._uri = urllib.parse.quote_plus(uri)
        self._key_name = key_name
        self._key = key
        self.refresh(ttl)

    def __repr__(self):
        return self.__token

    @property
    def expiry_time(self):
        """Get the expiry time, in UTC (since epoch)"""
        return self.__expiry_time

    def refresh(self, new_ttl=None):
        """
        Refresh the SasToken lifespan, giving it a new expiry time

        Parameters:
        new_ttl (int)[optional]: New time to live for the token in seconds
        """
        if new_ttl:
            self.__ttl = new_ttl
        self.__expiry_time = int(time.time() + self.__ttl)
        self.__token = self._build_token()

    def _build_token(self):
        """Buid SasToken representation
        
        Returns:
        String representation of the token
        """
        try:
            message = (self._uri + '\n' + str(self.__expiry_time)).encode(self._encoding_type)
            signing_key = base64.b64decode(self._key.encode(self._encoding_type))
            signed_hmac = hmac.HMAC(signing_key, message, hashlib.sha256)
            signature = urllib.parse.quote(base64.b64encode(signed_hmac.digest()))
            return self._token_format.format(self._uri, signature, str(self.__expiry_time), self._key_name)
        except TypeError as e:
            raise SasTokenError("Unable to build SasToken from given values", e)
