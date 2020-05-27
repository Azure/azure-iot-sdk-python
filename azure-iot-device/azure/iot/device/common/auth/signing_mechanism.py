# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module defines an abstract SigningMechanism, as well as common child implementations of it
"""

import six
import abc
import hmac
import hashlib
import base64
from six.moves import urllib


@six.add_metaclass(abc.ABCMeta)
class SigningMechanism(object):
    @abc.abstractmethod
    def sign(self, data_str):
        pass


class SymmetricKeySigningMechanism(SigningMechanism):
    def __init__(self, key):
        """
        A mechanism that signs data using a symmetric key

        :param key: Symmetric Key (base64 encoded)
        :type key: str or bytes
        """
        # Convert key to bytes
        try:
            key = key.encode("utf-8")
        except AttributeError:
            # If byte string, no need to encode
            pass

        # Derives the signing key
        # CT-TODO: is "signing key" the right term?
        try:
            self._signing_key = base64.b64decode(key)
        except (base64.binascii.Error, TypeError):
            # NOTE: TypeError can only be raised in Python 2.7
            raise ValueError("Invalid Symmetric Key")

    def sign(self, data_str):
        """
        Sign a data string with symmetric key and the HMAC-SHA256 algorithm.

        :param data_str: Data string to be signed
        :type data_str: str or bytes

        :returns: The signed data
        :rtype: str
        """
        # Convert data_str to bytes
        try:
            data_str = data_str.encode("utf-8")
        except AttributeError:
            # If byte string, no need to encode
            pass

        # Derive signature via HMAC-SHA256 algorithm
        try:
            hmac_digest = hmac.HMAC(
                key=self._signing_key, msg=data_str, digestmod=hashlib.sha256
            ).digest()
            signed_data = base64.b64encode(hmac_digest)
        except (TypeError):
            raise ValueError("Unable to sign string using the provided symmetric key")
        # Convert from bytes to string
        return signed_data.decode("utf-8")
