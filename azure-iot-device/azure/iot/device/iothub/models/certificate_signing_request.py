# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains a class representing messages that are sent or received.
"""
import sys


class CertificateSigningRequest(object):
    """Represents a message to or from IoTHub

    :ivar device_id: The ID of the device associated with the certificate signing request.
    :ivar csr: The base64-encoded certificate signing request.
    :ivar replace: Replace any active credential operation for this device.
    """

    def __init__(self, request_id, device_id, csr, replace=None):
        """
        Initializer for CertificateSigningRequest

        :param str device_id: The ID of the device associated with the certificate signing request.
        :param str csr: The base64-encoded certificate signing request.
        :param str replace: Replace any active credential operation for this device.
        """
        self.request_id = request_id
        self.device_id = device_id
        self.csr = csr
        self.replace = replace

    def __str__(self):
        return str(self.csr)

    def get_size(self) -> int:
        total = 0
        total = total + sum(sys.getsizeof(v) for v in self.__dict__.values() if v is not None)
        return total

    def to_json(obj):
        data = obj.__dict__.copy()
        data.pop("request_id", None)
        return data


class CertificateSigningResponse(object):
    """Represents a message to or from IoTHub

    :ivar device_id: The ID of the device associated with the certificate signing request.
    :ivar csr: The base64-encoded certificate signing request.
    :ivar replace: Replace any active credential operation for this device.
    """

    def __init__(self, correlation_id, certificates):
        """
        Initializer for CertificateSigningRequest

        :param str device_id: The ID of the device associated with the certificate signing request.
        :param str csr: The base64-encoded certificate signing request.
        :param str replace: Replace any active credential operation for this device.
        """
        self.correlation_id = correlation_id
        self.certificates = certificates
