# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------


class RegistrationResult(object):
    """
    The final result of a completed or failed registration attempt
    :ivar:request_id: The request id to which the response is being obtained
    :ivar:operation_id: The id of the operation as returned by the registration request.
    :ivar status: The status of the registration process as returned by the Hub
    Values can be "unassigned", "assigning", "assigned", "failed", "disabled"
    :ivar registration_state : Details like device id, assigned hub , date times etc returned
    from the provisioning service.
    """

    def __init__(self, rid, operation_id, status, registration_state=None):
        """
        :param rid: The request id to which the response is being obtained
        :param operation_id: The id of the operation as returned by the initial registration request.
        :param status: The status of the registration process.
        Values can be "unassigned", "assigning", "assigned", "failed", "disabled"
        :param registration_state : Details like device id, assigned hub , date times etc returned
        from the provisioning service.
        """
        self._request_id = rid
        self._operation_id = operation_id
        self._status = status
        self._registration_state = registration_state

    @property
    def request_id(self):
        return self._request_id

    @property
    def operation_id(self):
        return self._operation_id

    @property
    def status(self):
        return self._status

    @property
    def registration_state(self):
        return self._registration_state


class RegistrationState(object):
    """
    The registration state regarding the device.
    :ivar device_id: Desired device id for the provisioned device
    :ivar assigned_hub: Desired  IoT Hub where the provisioned device is located
    :ivar sub_status: Substatus for 'Assigned' devices. Possible values are
    "initialAssignment", "deviceDataMigrated", "deviceDataReset"
    :ivar created_date_time: Registration create date time (in UTC).
    :ivar last_update_date_time: Last updated date time (in UTC).
    :ivar etag: The entity tag associated with the resource.
    """

    def __init__(
        self,
        device_id=None,
        assigned_hub=None,
        sub_status=None,
        created_date_time=None,
        last_update_date_time=None,
        etag=None,
    ):
        """
        :param device_id: Desired device id for the provisioned device
        :param assigned_hub: Desired  IoT Hub where the provisioned device is located
        :param sub_status: Substatus for 'Assigned' devices. Possible values are
        "initialAssignment", "deviceDataMigrated", "deviceDataReset"
        :param created_date_time: Registration create date time (in UTC).
        :param last_update_date_time: Last updated date time (in UTC).
        :param etag: The entity tag associated with the resource.
        """
        self._device_id = device_id
        self._assigned_hub = assigned_hub
        self._sub_status = sub_status
        self._created_date_time = created_date_time
        self._last_update_date_time = last_update_date_time
        self._etag = etag

    @property
    def device_id(self):
        return self._device_id

    @property
    def assigned_hub(self):
        return self._assigned_hub

    @property
    def sub_status(self):
        return self._sub_status

    @property
    def created_date_time(self):
        return self._created_date_time

    @property
    def last_update_date_time(self):
        return self._last_update_date_time

    @property
    def etag(self):
        return self._etag
