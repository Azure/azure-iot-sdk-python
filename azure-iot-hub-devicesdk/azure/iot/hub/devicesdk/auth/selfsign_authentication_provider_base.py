# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import time
import abc
import logging
import math
import weakref
from threading import Timer
import six.moves.urllib as urllib
from .authentication_provider import AuthenticationProvider

logger = logging.getLogger(__name__)

_device_keyname_token_format = "SharedAccessSignature sr={}&sig={}&se={}&skn={}"
_device_token_format = "SharedAccessSignature sr={}&sig={}&se={}"

# Length of time, in seconds, that a SAS token is valid for.
DEFAULT_TOKEN_RENEWAL_INTERVAL = 3600

# Length of time, in seconds, before a token expires that we want to begin renewing it.
DEFAULT_TOKEN_RENEWAL_MARGIN = 120


class SelfSignAuthenticationProviderBase(AuthenticationProvider):
    """
    A base class for authentication providers which are able to sign themselves
    """

    def __init__(self, hostname, device_id, module_id):
        """
        Constructor for SymmetricKey Authentication Provider
        """
        logger.info(
            "Using symetric key authentication for (%s, %s, %s)", hostname, device_id, module_id
        )

        AuthenticationProvider.__init__(self, hostname, device_id, module_id)
        self.token_renewal_interval = DEFAULT_TOKEN_RENEWAL_INTERVAL
        self.token_renewal_margin = DEFAULT_TOKEN_RENEWAL_MARGIN
        self.shared_access_key_name = None
        self.sas_token_str = None

    def generate_new_sas_token(self):
        """
        Force the SAS token to update itself.  This will cause a new sas token to be
        created, and self.on_sas_token_updated to be called.  The token update will
        be rescheduled based on the current time.
        """
        logger.info(
            "Generating new SAS token for (%s,%s) that expires %d seconds in the future",
            self.device_id,
            self.module_id,
            self.token_renewal_interval,
        )
        expiry = int(math.floor(time.time()) + self.token_renewal_interval)
        resource_uri = self.hostname + "/devices/" + self.device_id
        if self.module_id:
            resource_uri += "/modules/" + self.module_id
        quoted_resource_uri = urllib.parse.quote_plus(resource_uri)

        signature = self._do_sign(quoted_resource_uri, expiry)

        if self.shared_access_key_name:
            token = _device_keyname_token_format.format(
                quoted_resource_uri, signature, str(expiry), self.shared_access_key_name
            )
        else:
            token = _device_token_format.format(
                quoted_resource_uri, signature, str(expiry)
            )

        self.sas_token_str = str(token)

    def get_current_sas_token(self):
        """
        :return: The current shared access signature token
        """
        if not self.sas_token_str:
            self.generate_new_sas_token()
        return self.sas_token_str
                

    @abc.abstractmethod
    def _do_sign(self, quoted_resource_uri, expiry):
        """
        Create and return a new signature for this object.  Caller is responsible for placing the
        signature inside the context of a SAS token string.
        """
        pass
