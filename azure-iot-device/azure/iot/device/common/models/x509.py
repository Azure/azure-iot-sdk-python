# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module represents a certificate that is responsible for providing client provided x509 certificates
that will eventually establish the authenticity of devices to IotHub and Provisioning Services.
"""


class X509(object):
    """
    A class with references to the certificate, key, and optional pass-phrase used to authenticate
    a TLS connection using x509 certificates
    """

    def __init__(self, cert_file, key_file, pass_phrase=None):
        """
        Initializer for X509 Certificate
        :param cert_file: The file path to contents of the certificate (or certificate chain)
         used to authenticate the device.
        :param key_file: The file path to the key associated with the certificate
        :param pass_phrase: (optional) The pass_phrase used to encode the key file
        """
        self._cert_file = cert_file
        self._key_file = key_file
        self._pass_phrase = pass_phrase

    @property
    def certificate_file(self):
        return self._cert_file

    @property
    def key_file(self):
        return self._key_file

    @property
    def pass_phrase(self):
        return self._pass_phrase
