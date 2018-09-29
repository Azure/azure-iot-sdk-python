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

    def __init__(self, connection_string, tpm_security_provider=None):

        self.hostname = connection_string[HOST_NAME]
        self.device_id = connection_string[DEVICE_ID]

        self.username = self.hostname + "/" + self.device_id

        uri = self.hostname + "/devices/" + self.device_id
        self.sas_token = SasToken(uri, connection_string[SHARED_ACCESS_KEY])

        # no actual implementation yet , but just a different option for authentication
        self.tpm = tpm_security_provider

    @classmethod
    def create_sharedaccesspolicykey_auth_provider(cls, connection_string):
        return AuthenticationProvider(connection_string, None)

    @classmethod
    def create_symmetrickey_auth_provider(cls, connection_string):
        return AuthenticationProvider(connection_string, None)

    @classmethod
    def create_X509_auth_provider(cls, certificate):
        return AuthenticationProvider(None, None)

    @classmethod
    def create_authentication_from_connection_string(cls, connection_string):
        connection_string_obj = ConnectionString(connection_string)
        # if connection_string_obj[SHARED_ACCESS_KEY_NAME]:
        #     auth_provider = cls.create_sharedaccesspolicykey_auth_provider(connection_string_obj)
        if connection_string_obj[SHARED_ACCESS_KEY]:
            auth_provider = cls.create_symmetrickey_auth_provider(connection_string_obj)
        else:
            auth_provider = cls.create_X509_auth_provider(connection_string_obj)

        return auth_provider
