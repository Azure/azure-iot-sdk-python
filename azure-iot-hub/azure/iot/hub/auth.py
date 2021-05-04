# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Provides authentication classes for use with the msrest library
"""

from msrest.authentication import Authentication, BasicTokenAuthentication
from .connection_string import ConnectionString
from .connection_string import HOST_NAME, SHARED_ACCESS_KEY_NAME, SHARED_ACCESS_KEY
from .sastoken import SasToken
from azure.core.pipeline.policies import BearerTokenCredentialPolicy
from azure.core.pipeline import PipelineRequest, PipelineContext
from azure.core.pipeline.transport import HttpRequest

__all__ = ["ConnectionStringAuthentication", "AzureIdentityCredentialAdapter"]


class ConnectionStringAuthentication(ConnectionString, Authentication):
    """ConnectionString class that can be used with msrest to provide SasToken authentication

    :param connection_string: The connection string to generate SasToken with
    """

    def __init__(self, connection_string):
        super(ConnectionStringAuthentication, self).__init__(
            connection_string
        )  # ConnectionString __init__

    @classmethod
    def create_with_parsed_values(cls, host_name, shared_access_key_name, shared_access_key):
        connection_string = (
            HOST_NAME
            + "="
            + host_name
            + ";"
            + SHARED_ACCESS_KEY_NAME
            + "="
            + shared_access_key_name
            + ";"
            + SHARED_ACCESS_KEY
            + "="
            + shared_access_key
        )
        return cls(connection_string)

    def signed_session(self, session=None):
        """Create requests session with any required auth headers applied.

        If a session object is provided, configure it directly. Otherwise,
        create a new session and return it.

        :param session: The session to configure for authentication
        :type session: requests.Session
        :rtype: requests.Session
        """
        session = super(ConnectionStringAuthentication, self).signed_session(session)

        # Authorization header
        sastoken = SasToken(self[HOST_NAME], self[SHARED_ACCESS_KEY], self[SHARED_ACCESS_KEY_NAME])
        session.headers[self.header] = str(sastoken)
        return session


class AzureIdentityCredentialAdapter(BasicTokenAuthentication):
    def __init__(self, credential, resource_id="https://iothubs.azure.net/.default", **kwargs):
        """Adapt any azure-identity credential to work with SDK that needs azure.common.credentials or msrestazure.
        Default resource is ARM (syntax of endpoint v2)
        :param credential: Any azure-identity credential (DefaultAzureCredential by default)
        :param str resource_id: The scope to use to get the token (default ARM)
        """
        super(AzureIdentityCredentialAdapter, self).__init__(None)
        self._policy = BearerTokenCredentialPolicy(credential, resource_id, **kwargs)

    def _make_request(self):
        return PipelineRequest(
            HttpRequest("AzureIdentityCredentialAdapter", "https://fakeurl"), PipelineContext(None)
        )

    def set_token(self):
        """Ask the azure-core BearerTokenCredentialPolicy policy to get a token.
        Using the policy gives us for free the caching system of azure-core.
        We could make this code simpler by using private method, but by definition
        I can't assure they will be there forever, so mocking a fake call to the policy
        to extract the token, using 100% public API."""
        request = self._make_request()
        self._policy.on_request(request)
        # Read Authorization, and get the second part after Bearer
        token = request.http_request.headers["Authorization"].split(" ", 1)[1]
        self.token = {"access_token": token}

    def signed_session(self, session=None):
        self.set_token()
        return super(AzureIdentityCredentialAdapter, self).signed_session(session)
