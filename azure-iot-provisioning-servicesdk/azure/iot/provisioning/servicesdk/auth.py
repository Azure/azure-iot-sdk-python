# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

"""Provides authentication classes for use with the msrest library
"""

from msrest.authentication import Authentication
from azure.iot.common.connection_string import ConnectionString
from azure.iot.common.connection_string import HOST_NAME, SHARED_ACCESS_KEY_NAME, SHARED_ACCESS_KEY
from azure.iot.common.sastoken import SasToken

__all__ = ["ConnectionStringAuthentication"]


class ConnectionStringAuthentication(ConnectionString, Authentication):
    """ConnectionString class that can be used with msrest to provide SasToken authentication

    :param connection_string: The connection string to generate SasToken with
    """

    def __init__(self, connection_string):
        super(ConnectionStringAuthentication, self).__init__(
            connection_string
        )  # ConnectionString __init__

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
