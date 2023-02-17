# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import abc
import base64
import binascii
import hmac
import hashlib
from typing import AnyStr

# TODO: remove commented signatures


class SigningMechanism(abc.ABC):
    @abc.abstractmethod
    # async def sign(self, data_str: Union[str, bytes]) -> str:
    async def sign(self, data_str: AnyStr) -> str:
        # NOTE: This is defined as a coroutine to allow for flexibility of implementation.
        # Some implementations may not require a coroutine, but others may, so we err on the side
        # of a coroutine for consistent interface.
        pass


class SymmetricKeySigningMechanism(SigningMechanism):
    # def __init__(self, key: Union[str, bytes]) -> None:
    def __init__(self, key: AnyStr) -> None:
        """
        A mechanism that signs data using a symmetric key

        :param key: Symmetric Key (base64 encoded)
        :type key: str or bytes

        :raises: ValueError if provided key is invalid
        """
        # Convert key to bytes (if not already)
        if isinstance(key, str):
            key_bytes = key.encode("utf-8")
        else:
            key_bytes = key

        # Derives the signing key
        try:
            self._signing_key = base64.b64decode(key_bytes)
        except (binascii.Error):
            raise ValueError("Invalid Symmetric Key")

    # def sign(self, data_str: Union[str, bytes]) -> str:
    async def sign(self, data_str: AnyStr) -> str:
        """
        Sign a data string with symmetric key and the HMAC-SHA256 algorithm.

        :param data_str: Data string to be signed
        :type data_str: str or bytes

        :returns: The signed data
        :rtype: str

        :raises: ValueError if an invalid data string is provided
        """
        # NOTE: This implementation doesn't take advantage of being a coroutine, but this is by
        # design. See the definition of the abstract base class above.

        # Convert data_str to bytes (if not already)
        if isinstance(data_str, str):
            data_bytes = data_str.encode("utf-8")
        else:
            data_bytes = data_str

        # Derive signature via HMAC-SHA256 algorithm
        try:
            hmac_digest = hmac.HMAC(
                key=self._signing_key, msg=data_bytes, digestmod=hashlib.sha256
            ).digest()
            signed_data = base64.b64encode(hmac_digest)
        except (TypeError):
            raise ValueError("Unable to sign string using the provided symmetric key")
        # Convert from bytes to string
        return signed_data.decode("utf-8")
