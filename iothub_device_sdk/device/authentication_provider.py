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

    def __init__(self, connection_string, tpm_security_provider=None):

        self.hostname = connection_string[HOST_NAME]
        self.device_id = connection_string[DEVICE_ID]

        self.username = None
        self.password = None

        self.sas_token = None

        # no actual implementation yet , but just a different option for authentication
        self.tpm = tpm_security_provider

    def create_symmetrickey_auth_provider(self, connection_string_obj):
        uri = self.hostname + "/devices/" + self.device_id
        self.sas_token = SasToken(uri, connection_string_obj[SHARED_ACCESS_KEY])

    def create_sharedaccesspolicykey_auth_provider(self, connection_string_obj):
        uri = self.hostname + "/devices/" + self.device_id
        self.sas_token = SasToken(uri, connection_string_obj[SHARED_ACCESS_KEY], connection_string_obj[SHARED_ACCESS_KEY_NAME])

    def create_X509_auth_provider(self, certificate):
        pass

    def create_username_password_mqtt(self):
        self.username = self.hostname + "/" + self.device_id
        self.password = str(self.sas_token)

    @classmethod
    def create_authentication_from_connection_string(cls, connection_string):
        connection_string_obj = ConnectionString(connection_string)
        auth_provider = AuthenticationProvider(connection_string_obj)

        if connection_string_obj._dict.get(SHARED_ACCESS_KEY_NAME) is not None:
            auth_provider.create_sharedaccesspolicykey_auth_provider(connection_string_obj)
        elif connection_string_obj._dict.get(SHARED_ACCESS_KEY) is not None:
            auth_provider.create_symmetrickey_auth_provider(connection_string_obj)
        else:
            auth_provider.create_X509_auth_provider(connection_string_obj)

        return auth_provider
