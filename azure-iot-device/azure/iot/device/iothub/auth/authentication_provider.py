# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class AuthenticationProvider(object):
    """Super class for all providing known types of authentication mechanism like
    x509 and SAS based authentication.

    :ivar str hostname: Hostname
    :ivar str device_id: Device ID
    :ivar str module_id: Module ID
    """

    def __init__(self, hostname, device_id, module_id=None):
        """Initializer for AuthenticationProvider

        :param str hostname: Hostname
        :param str device_id: Device ID
        :param str module_id: Module ID (optional)
        """
        self.hostname = hostname
        self.device_id = device_id
        self.module_id = module_id


# TODO: Potentially some additional abstract class that defines an abstract .get_current_sas_token()
# in order to enforce sas token retrieval in various sas-affiliated auths (sas, sk)?
