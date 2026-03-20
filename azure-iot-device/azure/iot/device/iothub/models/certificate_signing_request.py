# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains a class representing messages that are sent or received.
"""


class CertificateSigningRequest(object):
    """Represents a Certificate Signing Request message to Azure IoT Hub

    :ivar csr: The base64-encoded certificate signing request.
    :ivar replace: Replace any active credential operation for this device.
    """

    def __init__(self, request_id, csr, replace):
        """
        Initializer for CertificateSigningRequest

        :param str request_id: The unique identifier for the certificate signing request.
        :param str csr: The base64-encoded certificate signing request.
        :param str replace: Replace any active credential operation for this device.
        """

        self.request_id = request_id
        self.id = None  # The device id, filled internally by the pipeline configuration.
        self.csr = csr
        self.replace = replace

    def __str__(self):
        return str(self.csr)

    # Used for json serialization of CertificateSigningRequest.
    def to_dict(obj):
        data = obj.__dict__.copy()
        data.pop("request_id") # request_id should not be serialized
        return data


class CertificateSigningResponse(object):
    """Represents a Certificate Signing Response message from Azure IoT Hub

    :ivar status_code: The result code for the certificate signing request.
    :ivar certificates: An array with the base64-encoded issued certificate chain (leaf, intermediate and root, in this order).
    """

    def __init__(self, status_code, certificates):
        """
        Initializer for CertificateSigningResponse

        :param status_code: The result code for the certificate signing request.
        :param certificates: An array with the base64-encoded issued certificate chain (leaf, intermediate and root, in this order).
        """
        self.status_code = status_code
        self.certificates = certificates
