# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from .sk_authentication_provider import SymmetricKeyAuthenticationProvider
from .sas_authentication_provider import SharedAccessSignatureAuthenticationProvider
from .iotedge_authentication_provider import IotEdgeAuthenticationProvider


def from_connection_string(connection_string):
    """
    Provides an AuthenticationProvider object that can be created simply with a connection string
    :param connection_string: The connecting string
    :return: a Symmetric Key AuthenticationProvider
    """
    return SymmetricKeyAuthenticationProvider.parse(connection_string)


def from_shared_access_signature(sas_token_str):
    """
    Provides an `AuthenticationProvider` object that can be created simply with a shared access signature
    :param sas_token_str: The shared access signature
    :return: Shared Access Signature AuthenticationProvider
    """
    return SharedAccessSignatureAuthenticationProvider.parse(sas_token_str)

def from_environment():
    """
    Provides an `AuthenticationProvider` object that can be used inside of an IoTEdge module
    :return: iotedge AuthenticationProvider
    """
    return IotEdgeAuthenticationProvider()
