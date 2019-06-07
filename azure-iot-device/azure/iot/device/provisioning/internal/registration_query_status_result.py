# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------


class RegistrationQueryStatusResult(object):
    """
    The result of any registration attempt
    :ivar:request_id: The request id to which the response is being obtained
    :ivar:operation_id: The id of the operation as returned by the registration request.
    :ivar status: The status of the registration process as returned by the Hub
    Values can be "unassigned", "assigning", "assigned", "failed", "disabled"
    from the provisioning service.
    """

    def __init__(self, request_id=None, retry_after=None, operation_id=None, status=None):
        """
        :param request_id: The request id to which the response is being obtained
        :param retry_after : Number of secs after which to retry again.
        :param operation_id: The id of the operation as returned by the initial registration request.
        :param status: The status of the registration process.
        Values can be "unassigned", "assigning", "assigned", "failed", "disabled"
        from the provisioning service.
        """
        self._request_id = request_id
        self._operation_id = operation_id
        self._status = status
        self._retry_after = retry_after

    @property
    def request_id(self):
        return self._request_id

    @property
    def retry_after(self):
        return self._retry_after

    @retry_after.setter
    def retry_after(self, val):
        self._retry_after = val

    @property
    def operation_id(self):
        return self._operation_id

    @operation_id.setter
    def operation_id(self, val):
        self._operation_id = val

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, val):
        self._status = val
