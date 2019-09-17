# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module defines an exception surface, exposed as part of the azure.iot.device library API"""

# ~~~ CLIENT ERRORS ~~~


class ClientError(Exception):  # Could unexpected use this?
    """Generic error for a clients"""

    pass


class ConnectionFailedError(ClientError):
    """Failed to establish a connection"""

    pass


class ConnectionDroppedError(ClientError):
    """Lost connection while executing operation"""

    pass


class AuthorizationError(ClientError):
    """Could not authorize client using given credentials"""

    pass


# ~~~ SERVICE ERRORS ~~~
# NOTE: These are not (yet) in use


class ServiceError(Exception):
    """Error received from an Azure IoT service"""

    pass


class ArgumentError(ServiceError):
    """Service returned 400"""

    pass


class UnauthorizedError(ServiceError):
    """Service returned 401"""

    pass


class QuotaExceededError(ServiceError):
    """Service returned 403"""

    pass


class NotFoundError(ServiceError):
    """Service returned 404"""

    pass


class DeviceTimeoutError(ServiceError):
    """Service returned 408"""

    # TODO: is this a method call error?  If so, do we retry?
    pass


class DeviceAlreadyExistsError(ServiceError):
    """Service returned 409"""

    pass


class InvalidEtagError(ServiceError):
    """Service returned 412"""

    pass


class MessageTooLargeError(ServiceError):
    """Service returned 413"""

    pass


class ThrottlingError(ServiceError):
    """Service returned 429"""

    pass


class InternalServiceError(ServiceError):
    """Service returned 500"""

    pass


class BadDeviceResponseError(ServiceError):
    """Service returned 502"""

    # TODO: is this a method invoke thing?
    pass


class ServiceUnavailableError(ServiceError):
    """Service returned 503"""

    pass


class ServiceTimeoutError(Exception):
    """Service returned 504"""

    pass


class FailedStatusCodeError(Exception):
    """Service returned unknown status code"""

    pass


status_code_to_error = {
    400: ArgumentError,
    401: UnauthorizedError,
    403: QuotaExceededError,
    404: NotFoundError,
    408: DeviceTimeoutError,
    409: DeviceAlreadyExistsError,
    412: InvalidEtagError,
    413: MessageTooLargeError,
    429: ThrottlingError,
    500: InternalServiceError,
    502: BadDeviceResponseError,
    503: ServiceUnavailableError,
    504: ServiceTimeoutError,
}


def error_from_status_code(status_code, message=None):
    """
    Return an Error object from a failed status code

    :param int status_code: Status code returned from failed operation
    :returns: Error object
    """
    if status_code in status_code_to_error:
        return status_code_to_error[status_code](message)
    else:
        return FailedStatusCodeError(message)
