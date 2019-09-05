# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module provides a base class for renewable token authentication providers"""

import time
import abc
import logging
import math
import six
from threading import Timer
import six.moves.urllib as urllib
from .authentication_provider import AuthenticationProvider

logger = logging.getLogger(__name__)

_device_keyname_token_format = "SharedAccessSignature sr={}&sig={}&se={}&skn={}"
_device_token_format = "SharedAccessSignature sr={}&sig={}&se={}"

# Length of time, in seconds, that a SAS token is valid for.
DEFAULT_TOKEN_VALIDITY_PERIOD = 3600

# Length of time, in seconds, before a token expires that we want to begin renewing it.
DEFAULT_TOKEN_RENEWAL_MARGIN = 120


@six.add_metaclass(abc.ABCMeta)
class BaseRenewableTokenAuthenticationProvider(AuthenticationProvider):
    """A base class for authentication providers which are based on SAS (Shared
    Authentication Signature) strings which are able to be renewed.

    The SAS token string renewal is based on a signing function that is used
    to create the sig field of the SAS string.  This base implements all
    functionality for SAS string creation except for the signing function,
    which is expected to be provided by derived objects.  This base also
    implements the functionality necessary for timing and executing the
    token renewal operation.
    """

    def __init__(self, hostname, device_id, module_id=None):
        """Initializer for Renewable Token Authentication Provider.

        This object is intended as a base class and cannot be used directly.
        A derived class which provides a signing function (such as
        SymmetricKeyAuthenticationProvider or IoTEdgeAuthenticationProvider)
        should be used instead.

        :param str hostname: The hostname
        :param str device_id: The device ID
        :param str module_id: The module ID (optional)
        """

        super(BaseRenewableTokenAuthenticationProvider, self).__init__(
            hostname=hostname, device_id=device_id, module_id=module_id
        )
        self.token_validity_period = DEFAULT_TOKEN_VALIDITY_PERIOD
        self.token_renewal_margin = DEFAULT_TOKEN_RENEWAL_MARGIN
        self._token_update_timer = None
        self.shared_access_key_name = None
        self.sas_token_str = None
        self.on_sas_token_updated_handler = None

    def disconnect(self):
        """Cancel updates to the SAS Token"""
        self._cancel_token_update_timer()

    def generate_new_sas_token(self):
        """Force the SAS token to update itself.

        This will cause a new sas token to be created using the _sign function.
        This token is valid for roughly self.token_validity_period second.

        This validity period can only be roughly enforced because it relies on the
        coordination of clocks between the client device and the service.  If the two
        different machines have different definitions of "now", most likely because
        of clock drift, then they will also have different notions of when a token will
        expire.  This algorithm atempts to compensate for clock drift by taking
        self.token_renewal_margin into account when deciding when to renew a token.

        If self.token_udpate_callback is set, this callback will be called to notify the
        pipeline that a new token is available.  The pipeline is responsible for doing
        whatever is necessary to leverage the new token when the on_sas_token_updated_handler
        function is called.

        The token that is generated expires at some point in the future, based on the token
        renewal interval and the token renewal margin.  When a token is first generated, the
        authorization provider object will set a timer which will be responsible for renewing
        the token before the it expires.  When this timer fires, it will automatically generate
        a new sas token and notify the pipeline by calling self.on_sas_token_updated_handler.

        The token update timer is set based on two numbers: self.token_validity_period and
        self.token_renewal_margin

        The first number is the validity period.  This defines the amount of time that the token
        is valid.  The interval is encoded in the token as an offset from the current time,
        as based on the Unix epoch.  In other words, the expiry (se=) value in the token
        is the number of seconds after 00:00 on January 1, 1970 that the token expires.

        The second number that defines the token renewal behavior is the margin.  This is
        the number of seconds before expiration that we want to generate a new token.  Since
        the clocks on different computers can drift over time, they will all have different
        definitions of what "now" is, so the margin needs to be set so there is a
        very small chance that there is no time overlap where one computer thinks the token
        is expired and another doesn't.

        When the timer is set to renew the SAS token, the timer is set for
        (token_validity_period - token_renewal_margin) seconds in the future.  In this way,
        the token will be renewed close to it's expiration time, but not so close that
        we risk a problem caused by clock drift.

        :return: None
        """
        logger.info(
            "Generating new SAS token for (%s,%s) that expires %d seconds in the future",
            self.device_id,
            self.module_id,
            self.token_validity_period,
        )
        expiry = int(math.floor(time.time()) + self.token_validity_period)
        resource_uri = self.hostname + "/devices/" + self.device_id
        if self.module_id:
            resource_uri += "/modules/" + self.module_id
        quoted_resource_uri = urllib.parse.quote_plus(resource_uri)

        signature = self._sign(quoted_resource_uri, expiry)

        if self.shared_access_key_name:
            token = _device_keyname_token_format.format(
                quoted_resource_uri, signature, str(expiry), self.shared_access_key_name
            )
        else:
            token = _device_token_format.format(quoted_resource_uri, signature, str(expiry))

        self.sas_token_str = str(token)
        self._schedule_token_update(self.token_validity_period - self.token_renewal_margin)
        self._notify_token_updated()

    def _cancel_token_update_timer(self):
        """Cancel any future token update operations.  This is typically done as part of a
        teardown operation.
        """
        t = self._token_update_timer
        self._token_update_timer = None
        if t:
            logger.debug("Canceling token update timer for (%s,%s)", self.device_id, self.module_id)
            t.cancel()

    def _schedule_token_update(self, seconds_until_update):
        """Schedule an automatic sas token update to take place seconds_until_update seconds in
        the future.  If an update was previously scheduled, this method shall cancel the
        previously-scheduled update and schedule a new update.
        """
        self._cancel_token_update_timer()
        logger.debug(
            "Scheduling token update for (%s,%s) for %d seconds in the future",
            self.device_id,
            self.module_id,
            seconds_until_update,
        )

        def timerfunc():
            logger.debug("Timed SAS update for (%s,%s)", self.device_id, self.module_id)
            self.generate_new_sas_token()

        self._token_update_timer = Timer(seconds_until_update, timerfunc)
        self._token_update_timer.daemon = True
        self._token_update_timer.start()

    def _notify_token_updated(self):
        """Notify clients that the SAS token has been updated by calling self.on_sas_token_updated.
        In response to this event, clients should re-initiate their connection in order to use
        the updated sas token.
        """
        if self.on_sas_token_updated_handler:
            logger.debug(
                "sending token update notification for (%s, %s)", self.device_id, self.module_id
            )
            self.on_sas_token_updated_handler()
        else:
            logger.warning(
                "_notify_token_updated: on_sas_token_updated_handler not set.  Doing nothing."
            )

    def get_current_sas_token(self):
        """Get the current SharedAuthenticationSignature string.

        This string can be used to authenticate with an Azure IoT Hub or Azure IoT Edge Hub service.

        If a SAS token has not yet been created yet, this function call the generate_new_sas_token
        function to create a new token and schedule the update timer.  See the documentation for
        generate_new_sas_token for more detail.

        :return: The current shared access signature token in string form.
        """
        if not self.sas_token_str:
            self.generate_new_sas_token()
        return self.sas_token_str

    @abc.abstractmethod
    def _sign(self, quoted_resource_uri, expiry):
        """Create and return a new signature for this object.  The caller is responsible
        for placing the signature inside the sig field of a SAS token string.
        """
        pass
