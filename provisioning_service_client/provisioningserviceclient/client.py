# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

from .utils import sastoken, auth
from .protocol import ProvisioningServiceClient as GeneratedProvisioningServiceClient
from .models import (BulkEnrollmentOperation, BulkEnrollmentOperationResult, \
    BulkEnrollmentOperationError, QuerySpecification, IndividualEnrollment, EnrollmentGroup, \
    DeviceRegistrationState, ProvisioningServiceErrorDetailsException)


CS_DELIMITER = ";"
CS_VAL_SEPARATOR = "="
HOST_NAME_LABEL = "HostName"
SHARED_ACCESS_KEY_NAME_LABEL = "SharedAccessKeyName"
SHARED_ACCESS_KEY_LABEL = "SharedAccessKey"


def _unwrap_model(model):
    if model.initial_twin: #LBYL for efficiency - nothing exceptional about this situation
        model.initial_twin = model.initial_twin._unwrap()


def _wrap_model(model):
    if model.initial_twin:
        model.initial_twin = model.initial_twin._wrap()


class ProvisioningServiceError(Exception):
    """
    An error from the Device Provisioning Service

    :param str message: Error message
    :param Exception cause: Error that causes this error (optional)
    """
    def __init__(self, message, cause=None):
        super(ProvisioningServiceError, self).__init__(message)
        self.cause = cause


class ProvisioningServiceClient(object):
    """
    API for connecting to, and conducting operations on a Device Provisioning Service

    :param str host_name: The host name of the Device Provisioning Service
    :param str shared_access_key_name: The shared access key name of the
     Device Provisioning Service
    :param str shared_access_key: The shared access key of the Device Provisioning Service
    """

    authorization_header = "Authorization"
    err_msg = "Service Error {} - {}"

    def __init__(self, host_name, shared_access_key_name, shared_access_key):
        self.host_name = host_name
        self.shared_access_key_name = shared_access_key_name
        self.shared_access_key = shared_access_key

        #Build connection string
        cs_auth = auth.ConnectionStringAuthentication.create_with_parsed_values(
            self.host_name, self.shared_access_key_name, self.shared_access_key)
        self._runtime_client = GeneratedProvisioningServiceClient(cs_auth,
            "https://" + self.host_name)

    @classmethod
    def create_from_connection_string(cls, connection_string):
        """
        Create a Provisioning Service Client from a connection string

        :param str connection_string: The connection string for the Device Provisioning Service
        :return: A new instance of :class:`ProvisioningServiceClient
         <provisioningserviceclient.ProvisioningServiceClient>`
        :rtype: :class:`ProvisioningServiceClient
         <provisioningserviceclient.ProvisioningServiceClient>`
        :raises: ValueError if connection string is invalid
        """
        cs_args = connection_string.split(CS_DELIMITER)

        if len(cs_args) != 3:
            raise ValueError("Too many or too few values in the connection string")
        if len(cs_args) > len(set(cs_args)):
            raise ValueError("Duplicate label in connection string")

        for arg in cs_args:
            tokens = arg.split(CS_VAL_SEPARATOR, 1)

            if tokens[0] == HOST_NAME_LABEL:
                host_name = tokens[1]
            elif tokens[0] == SHARED_ACCESS_KEY_NAME_LABEL:
                shared_access_key_name = tokens[1]
            elif tokens[0] == SHARED_ACCESS_KEY_LABEL:
                shared_access_key = tokens[1]
            else:
                raise ValueError("Connection string contains incorrect values")

        return cls(host_name, shared_access_key_name, shared_access_key)

    def create_or_update(self, provisioning_model):
        """
        Create or update an object on the Provisioning Service

        :param provisioning_model: The model of the object to be created/updated
        :type provisioning_model: :class:`IndividualEnrollment
         <provisioningserviceclient.models.IndividualEnrollment>` or :class:`EnrollmentGroup
         <provisioningserviceclient.models.EnrollmentGroup>`

        :returns: The model of the created/updated object as stored on the Provisiong Service
        :rtype: :class:`IndividualEnrollment
         <provisioningserviceclient.models.IndividualEnrollment>` or :class:`EnrollmentGroup
         <provisioningserviceclient.models.EnrollmentGroup>`
        :raises: TypeError if invalid provisioning model type or :class:`ProvisioningServiceError
         <provisioningserviceclient.ProvisioningServiceError>` if an error occurs on the
         Provisioning Service
        """
        if isinstance(provisioning_model, IndividualEnrollment):
            operation = self._runtime_client.create_or_update_individual_enrollment
            id = provisioning_model.registration_id
        elif isinstance(provisioning_model, EnrollmentGroup):
            operation = self._runtime_client.create_or_update_enrollment_group
            id = provisioning_model.enrollment_group_id
        else:
            raise TypeError("given object must be IndividualEnrollment or EnrollmentGroup")

        _unwrap_model(provisioning_model)

        try:
            result = operation(id, provisioning_model, provisioning_model.etag)
        except ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(
                self.err_msg.format(e.response.status_code, e.response.reason), e)

        _wrap_model(result)
        return result

    def get_individual_enrollment(self, registration_id):
        """
        Retrieve an Individual Enrollment from the Provisioning Service

        :param str registration_id: The registration id of the target Individual Enrollment
        :returns: Individual Enrollment from the Provisioning Service corresponding to the given
         registration id
        :rtype: :class:`IndividualEnrollment<provisioningserviceclient.models.IndividualEnrollment>`
        :raises: :class:ProvisioningServiceError
         <provisioningserviceclient.ProvisioningServiceError>` if an error occurs on the
         Provisioning Service
        """
        try:
            result = self._runtime_client.get_individual_enrollment(registration_id)
        except ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(
                self.err_msg.format(e.response.status_code, e.response.reason), e)

        _wrap_model(result)
        return result

    def get_enrollment_group(self, group_id):
        """
        Retrieve an Enrollment Group from the Provisioning Service

        :param str group_id: The group id of the target Enrollment Group
        :returns: Enrollment Group from the Provisioning Service corresponding to the given
         group id
        :rtype: :class:`EnrollmentGroup<provisioningserviceclient.models.EnrollmentGroup>`
        :raises: :class:ProvisioningServiceError
         <provisioningserviceclient.ProvisioningServiceError>` if an error occurs on the
         Provisioning Service
        """
        try:
            result = self._runtime_client.get_enrollment_group(
                group_id)
        except ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(
                self.err_msg.format(e.response.status_code, e.response.reason), e)

        _wrap_model(result)
        return result

    def get_registration_state(self, registration_id):
        """
        Retrieve a Device Registration State from the Provisioning Service

        :param str registration_id: The registration id of the target Device Registration State
        :returns: The Device Registration State from the Provisioning Service corresponding to the
         given registration id
        :rtype: :class:`DeviceRegistrationState
         <provisioningserviceclient.models.DeviceRegistrationState>`
        :raises: :class:ProvisioningServiceError
         <provisioningserviceclient.ProvisioningServiceError>` if an error occurs on the
         Provisioning Service
        """
        try:
            result = self._runtime_client.get_device_registration_state(\
                registration_id)
        except ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(
                self.err_msg.format(e.response.status_code, e.response.reason), e)

        return result

    def delete(self, provisioning_model):
        """
        Delete an object on the Provisioning Service

        :param provisioning_model: The model of the object to be deleted
        :type provisioning_model: :class:`IndividualEnrollment
         <provisioningserviceclient.models.IndividualEnrollment>` or :class:`EnrollmentGroup
         <provisioningserviceclient.models.EnrollmentGroup>` or :class:`DeviceRegistrationState
         <provisioningserviceclient.models.DeviceRegistrationState>`
        :raises: :class:ProvisioningServiceError
         <provisioningserviceclient.ProvisioningServiceError>` if an error occurs on the
         Provisioning Service
        """
        if isinstance(provisioning_model, IndividualEnrollment):
            self.delete_individual_enrollment_by_param(provisioning_model.registration_id, \
                provisioning_model.etag)
        elif isinstance(provisioning_model, EnrollmentGroup):
            self.delete_enrollment_group_by_param(provisioning_model.enrollment_group_id, \
                provisioning_model.etag)
        elif isinstance(provisioning_model, DeviceRegistrationState):
            self.delete_registration_state_by_param(provisioning_model.registration_id, \
            provisioning_model.etag)
        else:
            raise TypeError("Given model must be IndividualEnrollment, EnrollmentGroup or DeviceRegistrationState")
        return

    def delete_individual_enrollment_by_param(self, registration_id, etag=None):
        """
        Delete an Individual Enrollment on the Provisioning Service

        :param str registration_id: The registration id of the Individual Enrollment to be deleted
        :param str etag: The etag of the Individual Enrollment to be deleted (optional)
        :raises: :class:ProvisioningServiceError
         <provisioningserviceclient.ProvisioningServiceError>` if an error occurs on the
         Provisioning Service
        """
        try:
            self._runtime_client.delete_individual_enrollment(registration_id, etag)
        except ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(
                self.err_msg.format(e.response.status_code, e.response.reason), e)
        return

    def delete_enrollment_group_by_param(self, group_id, etag=None):
        """
        Delete an Enrollment Group on the Provisioning Service

        :param str group_id: The registration id of the Individual Enrollment to be deleted
        :param str etag: The etag of the Individual Enrollment to be deleted (optional)
        :raises: :class:ProvisioningServiceError
         <provisioningserviceclient.ProvisioningServiceError>` if an error occurs on the
         Provisioning Service
        """
        try:
            self._runtime_client.delete_enrollment_group(group_id, etag)
        except ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(
                self.err_msg.format(e.response.status_code, e.response.reason), e)
        return

    def delete_registration_state_by_param(self, registration_id, etag=None):
        """
        Delete a Device Registration State on the Provisioning Service

        :param str registration_id: The registration id of the Device Registration State to be
         deleted
        :param str etag: The etag of the Device Registration State to be deleted (optional)
        :raises: :class:ProvisioningServiceError
         <provisioningserviceclient.ProvisioningServiceError>` if an error occurs on the
         Provisioning Service
        """
        try:
            self._runtime_client.delete_device_registration_state(registration_id, etag)
        except ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(self.err_msg.format(e.response.status_code, e.response.reason), e)
        return

    def run_bulk_operation(self, bulk_op):
        """
        Run a Bulk Enrollment Operation on the Provisioning Service

        :param bulk_op: Details of the operations to be run
        :type bulk_op: :class:`BulkEnrollmentOperation`
         <provisioningserviceclient.BulkEnrollmentOperation>`
        :returns: Bulk Enrollment Operation Result describing results of the
         Bulk Enrollment Operation
        :rtype: :class:`BulkEnrollmentOperationResult
         <provisioningserviceclient.BulkEnrollmentOperationResult>`
        :raises: :class:ProvisioningServiceError
         <provisioningserviceclient.ProvisioningServiceError>` if an error occurs on the
         Provisioning Service
        """
        for enrollment in bulk_op.enrollments:
            _unwrap_model(enrollment)

        try:
            result = self._runtime_client.run_bulk_enrollment_operation(bulk_op)
        except ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(self.err_msg.format(e.response.status_code, e.response.reason), e)
        return result

    def create_individual_enrollment_query(self, query_spec, page_size=None):
        """
        Create a Query object to access results of a Provisioning Service query
        for Individual Enrollments

        :param query_spec: The specification for the query
        :type query_spec: :class:`QuerySpecification<provisioningserviceclient.QuerySpecification>`
        :param int page_size: The max results per page (optional)
        :returns: Query object that can iterate over results of the query
        :rtype: :class:`Query<provisioningserviceclient.Query>`
        """
        query_fn = self._runtime_client.query_individual_enrollments
        return Query(query_spec, query_fn, page_size)

    def create_enrollment_group_query(self, query_spec, page_size=None):
        """
        Create a Query object to access results of a Provisioning Service query
        for Enrollment Groups

        :param query_spec: The specification for the query
        :type query_spec: :class:`QuerySpecification<provisioningserviceclient.QuerySpecification>`
        :param int page_size: The max results per page (optional)
        :returns: Query object that can iterate over results of the query
        :rtype: :class:`Query<provisioningserviceclient.Query>`
        """
        query_fn = self._runtime_client.query_enrollment_groups
        return Query(query_spec, query_fn, page_size)

    def create_registration_state_query(self, reg_id, page_size=None):
        """
        Create a Query object to access results of a Provisioning Service query
        for Device Registration States

        :param query_spec: The specification for the query
        :type query_spec: :class:`QuerySpecification<provisioningserviceclient.QuerySpecification>`
        :param int page_size: The max results per page (optional)
        :returns: Query object that can iterate over results of the query
        :rtype: :class:`Query<provisioningserviceclient.Query>`
        """
        query_fn = self._runtime_client.query_device_registration_states
        return Query(reg_id, query_fn, page_size)

class Query(object):
    """
    Query object that can be used to iterate over Provisioning Service data.
    Note that for general usage, Query objects should be generated using a
    :class:`ProvisioningServiceClient<provisioningserviceclient.ProvisioningServiceClient>`
    instance, not directly constructed.

    :param query_spec_or_id: The Query Specification or registration id
    :type query_spec_or_id: :class:`QuerySpecification
     <provisioningserviceclient.QuerySpecification>` or str
    :param query_fn: Function pointer to make HTTP query request. Note well that it must take args
     in the format query_fn(qs: QuerySpecification, cust_headers: dict, raw_resp: bool) or
     query_fn(id: str, cust_headers: dict, raw_resp:bool) and return an instance of
     :class:`ClientRawResponse<msrest.pipeline.ClientRawResponse>` when raw_resp == True
    :type query_fn: Function pointer
    :param sastoken_factory: Sas Token Factory to generate Sas Tokens
    :type sastoken_factory: :class:`SasTokenFactory<utils.sastoken.SasTokenFactory>`
    :param int page_size: Max number of results per page of query response
    :ivar page_size: Max number of results per page of query response
    :ivar has_next: Indicates if the Query has more results to return
    :ivar continuation_token: Token indicating current position in list of results
    :raises: TypeError if given invalid type
    """

    page_size_header = "x-ms-max-item-count"
    continuation_token_header = "x-ms-continuation"
    item_type_header = "x-ms-item-type"

    err_msg = "Service Error {} - {}"

    def __init__(self, query_spec_or_id, query_fn, page_size=None):
        self._query_spec_or_id = query_spec_or_id
        self._query_fn = query_fn
        self.page_size = page_size
        self.has_next = True
        self.continuation_token = None

    def __iter__(self):
        self.continuation_token = None
        return self

    def __next__(self):
        return self.next()

    @property
    def page_size(self):
        return self._page_size

    @page_size.setter
    def page_size(self, value):
        if value is None or value > 0:
            self._page_size = value
        else:
            raise ValueError("Page size must be a positive number")

    def next(self, continuation_token=None):
        """
        Get the next page of query results

        :param str continuation_token: Token indicating a specific starting point in the set
         of all results
        :returns: The next page of results
        :rtype: list[:class:`IndividualEnrollment
         <provisioningserviceclient.models.IndividualEnrollment>`]
        :raises: StopIteration if there are no more results or
         :class:`ProvisioningServiceError<provisioningserviceclient.ProvisioningServiceError>` if an
         error occurs on the Provisioning Service
        """
        if not self.has_next:
            raise StopIteration("No more results")

        if not continuation_token:
            continuation_token = self.continuation_token

        if self.page_size is not None:
            page_size = str(self._page_size)
        else:
            page_size = self._page_size

        try:
            raw_resp = self._query_fn(self._query_spec_or_id, page_size, continuation_token, raw=True)
        except ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(self.err_msg.format(e.response.status_code, e.response.reason), e)

        if not raw_resp.output:
            raise StopIteration("No more results")

        self.continuation_token = raw_resp.headers[Query.continuation_token_header]
        self.has_next = self.continuation_token != None

        #wrap results
        output = []
        for item in raw_resp.output:
            output.append(_wrap_model(item))

        return output
