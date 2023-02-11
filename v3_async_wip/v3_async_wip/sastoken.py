# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains tools for working with Shared Access Signature (SAS) Tokens"""

import abc
import time
import urllib
from typing import Optional, Dict
from .signing_mechanism import SigningMechanism


class SasTokenError(Exception):
    """Error in SasToken"""

    pass


class SasToken(abc.ABC):
    """Abstract parent class for SAS Tokens.

    Doesn't do much, but helps with type hints
    """

    @property
    @abc.abstractmethod
    def expiry_time(self) -> int:
        pass


class RenewableSasToken(SasToken):
    """Renewable Shared Access Signature Token used to authenticate a request.

    This token is 'renewable', which means that it can be updated when necessary to
    prevent expiry, by using the .refresh() method.

    Data Attributes:
    expiry_time (int): Time that token will expire (in UTC, since epoch)
    ttl (int): Time to live for the token, in seconds
    """

    _auth_rule_token_format = (
        "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}&skn={keyname}"
    )
    _simple_token_format = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}"

    def __init__(
        self,
        uri: str,
        signing_mechanism: SigningMechanism,
        key_name: Optional[str] = None,
        ttl: int = 3600,
    ) -> None:
        """
        :param str uri: URI of the resource to be accessed
        :param signing_mechanism: The signing mechanism to use in the SasToken
        :type signing_mechanism: Child classes of :class:`azure.iot.common.SigningMechanism`
        :param str key_name: Symmetric Key Name (optional)
        :param int ttl: Time to live for the token, in seconds (default 3600)

        :raises: SasTokenError if an error occurs building a SasToken
        """
        self._uri = uri
        self._signing_mechanism = signing_mechanism
        self._key_name = key_name
        # These two values will be set by the .refresh() call
        self._expiry_time: int
        self._token: str

        self.ttl = ttl
        self.refresh()

    def __str__(self) -> str:
        return self._token

    def refresh(self) -> None:
        """
        Refresh the SasToken lifespan, giving it a new expiry time, and generating a new token.
        """
        self._expiry_time = int(time.time() + self.ttl)
        self._token = self._build_token()

    def _build_token(self) -> str:
        """Build SasToken representation

        :returns: String representation of the token
        """
        url_encoded_uri = urllib.parse.quote(self._uri, safe="")
        message = url_encoded_uri + "\n" + str(self.expiry_time)
        try:
            signature = self._signing_mechanism.sign(message)
        except Exception as e:
            # Because of variant signing mechanisms, we don't know what error might be raised.
            # So we catch all of them.
            raise SasTokenError("Unable to build SasToken from given values") from e
        url_encoded_signature = urllib.parse.quote(signature, safe="")
        if self._key_name:
            token = self._auth_rule_token_format.format(
                resource=url_encoded_uri,
                signature=url_encoded_signature,
                expiry=str(self.expiry_time),
                keyname=self._key_name,
            )
        else:
            token = self._simple_token_format.format(
                resource=url_encoded_uri,
                signature=url_encoded_signature,
                expiry=str(self.expiry_time),
            )
        return token

    @property
    def expiry_time(self) -> int:
        """Expiry Time is READ ONLY"""
        return self._expiry_time


class NonRenewableSasToken(SasToken):
    """NonRenewable Shared Access Signature Token used to authenticate a request.

    This token is 'non-renewable', which means that it is invalid once it expires, and there
    is no way to keep it alive. Instead, a new token must be created.

    Data Attributes:
    expiry_time (int): Time that token will expire (in UTC, since epoch)
    resource_uri (str): URI for the resource the Token provides authentication to access
    """

    def __init__(self, sastoken_string) -> None:
        """
        :param str sastoken_string: A string representation of a SAS token
        """
        self._token = sastoken_string
        self._token_info = get_sastoken_info_from_string(self._token)

    def __str__(self) -> str:
        return self._token

    @property
    def expiry_time(self) -> int:
        """Expiry Time is READ ONLY"""
        return int(self._token_info["se"])

    @property
    def resource_uri(self) -> str:
        """Resource URI is READ ONLY"""
        uri = self._token_info["sr"]
        return urllib.parse.unquote(uri)


REQUIRED_SASTOKEN_FIELDS = ["sr", "sig", "se"]
VALID_SASTOKEN_FIELDS = REQUIRED_SASTOKEN_FIELDS + ["skn"]


def get_sastoken_info_from_string(sastoken_string: str) -> Dict[str, str]:
    pieces = sastoken_string.split("SharedAccessSignature ")
    if len(pieces) != 2:
        raise SasTokenError("Invalid SasToken string: Not a SasToken ")

    # Get sastoken info as dictionary
    try:
        # TODO: fix this typehint later, it needs some kind of cast
        sastoken_info = dict(map(str.strip, sub.split("=", 1)) for sub in pieces[1].split("&"))  # type: ignore
    except Exception as e:
        raise SasTokenError("Invalid SasToken string: Incorrectly formatted") from e

    # Validate that all required fields are present
    if not all(key in sastoken_info for key in REQUIRED_SASTOKEN_FIELDS):
        raise SasTokenError("Invalid SasToken string: Not all required fields present")

    # Validate that no unexpected fields are present
    if not all(key in VALID_SASTOKEN_FIELDS for key in sastoken_info):
        raise SasTokenError("Invalid SasToken string: Unexpected fields present")

    return sastoken_info
