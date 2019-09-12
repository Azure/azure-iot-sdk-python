# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module defines errors that may be raised from a service result.

Consider splitting these up into service specific definitions in the
.iothub or .provisioning subpackages of azure.iot.device instead of .common

NOTE: This module is not yet in use"""


class ArgumentError(Exception):
    """
    Service returned 400
    """

    pass


class UnauthorizedError(Exception):
    """
    Service returned 401
    """

    pass


class QuotaExceededError(Exception):
    """
    Service returned 403
    """

    pass


class NotFoundError(Exception):
    """
    Service returned 404
    """

    pass


class DeviceTimeoutError(Exception):
    """
    Service returned 408
    """

    # TODO: is this a method call error?  If so, do we retry?
    pass


class DeviceAlreadyExistsError(Exception):
    """
    Service returned 409
    """

    pass


class InvalidEtagError(Exception):
    """
    Service returned 412
    """

    pass


class MessageTooLargeError(Exception):
    """
    Service returned 413
    """

    pass


class ThrottlingError(Exception):
    """
    Service returned 429
    """

    pass


class InternalServiceError(Exception):
    """
    Service returned 500
    """

    pass


class BadDeviceResponseError(Exception):
    """
    Service returned 502
    """

    # TODO: is this a method invoke thing?
    pass


class ServiceUnavailableError(Exception):
    """
    Service returned 503
    """

    pass


class TimeoutError(Exception):
    """
    Operation timed out or service returned 504
    """

    pass


class FailedStatusCodeError(Exception):
    """
    Service returned unknown status code
    """

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
    504: TimeoutError,
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
