# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains a class representing messages that are sent or received.
"""


class CertificateSigningRequest(object):
    """Represents a message to or from IoTHub

    :ivar device_id: The ID of the device associated with the certificate signing request.
    :ivar csr: The base64-encoded certificate signing request.
    :ivar replace: Replace any active credential operation for this device.
    """

    def __init__(self, request_id, device_id, csr, replace):
        """
        Initializer for CertificateSigningRequest

        :param str device_id: The ID of the device associated with the certificate signing request.
        :param str csr: The base64-encoded certificate signing request.
        :param str replace: Replace any active credential operation for this device.
        """
        self.request_id = request_id
        self.id = device_id  # TODO(ewertons): do not expose to customer, grab it from the internal state of the client.
        self.csr = csr
        self.replace = replace

    def __str__(self):
        return str(self.csr)

    def to_dict(obj):
        data = obj.__dict__.copy()
        data.pop("request_id", None)
        return data


class CertificateSigningResponse(object):
    """Represents a message to or from IoTHub

    :ivar device_id: The ID of the device associated with the certificate signing request.
    :ivar csr: The base64-encoded certificate signing request.
    :ivar replace: Replace any active credential operation for this device.
    """

    def __init__(self, request_id, status, certificates):
        """
        Initializer for CertificateSigningRequest

        :param str device_id: The ID of the device associated with the certificate signing request.
        :param str csr: The base64-encoded certificate signing request.
        :param str replace: Replace any active credential operation for this device.
        """
        self.request_id = request_id
        self.status = status
        self.certificates = certificates
