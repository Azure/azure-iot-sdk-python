# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# Temporary path hack (replace once monorepo path solution implemented)
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..\..\python_shared_utils"))
# ---------------------------------------------------------------------

from connection_string import ConnectionString, HOST_NAME, SHARED_ACCESS_KEY_NAME, SHARED_ACCESS_KEY, SHARED_ACCESS_SIGNATURE, DEVICE_ID, MODULE_ID, GATEWAY_HOST_NAME
from sastoken import SasToken


class AuthenticationProvider(object):
    """
    A provider for authentication mechanism based on known authentication mechanisms ,
    including x509 and SAS based authentication.
    """

    def __init__(self, connection_string):

        self.hostname = connection_string[HOST_NAME]
        self.device_id = connection_string[DEVICE_ID]

        if connection_string._dict.get(MODULE_ID) is not None:
            self.module_id = connection_string[MODULE_ID]
        if connection_string._dict.get(GATEWAY_HOST_NAME) is not None:
            self.gateway_hostname = connection_string[GATEWAY_HOST_NAME]

        self.shared_access_signature_token = None
        self.shared_access_keyname = None
        self.shared_access_key = None

    def create_symmetrickey_auth_provider(self, connection_string_obj):
        uri = self.hostname + "/devices/" + self.device_id
        self.shared_access_signature_token = SasToken(uri, connection_string_obj[SHARED_ACCESS_KEY])

    def create_sharedaccesspolicykey_auth_provider(self, connection_string_obj):
        uri = self.hostname + "/devices/" + self.device_id
        self.shared_access_signature_token = SasToken(uri, connection_string_obj[SHARED_ACCESS_KEY], connection_string_obj[SHARED_ACCESS_KEY_NAME])

    @classmethod
    def create_authentication_from_connection_string(cls, connection_string):
        connection_string_obj = ConnectionString(connection_string)
        auth_provider = AuthenticationProvider(connection_string_obj)

        if connection_string_obj._dict.get(SHARED_ACCESS_KEY_NAME) is not None:
            auth_provider.create_sharedaccesspolicykey_auth_provider(connection_string_obj)
        elif connection_string_obj._dict.get(SHARED_ACCESS_KEY) is not None:
            auth_provider.create_symmetrickey_auth_provider(connection_string_obj)
        else:
            pass

        return auth_provider
