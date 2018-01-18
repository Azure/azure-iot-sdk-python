# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

from utils import sastoken
from serviceswagger import DeviceProvisioningServiceServiceRuntimeClient
import serviceswagger.models as genmodels
import provisioningserviceclient.models as models
from provisioningserviceclient.models import IndividualEnrollment, EnrollmentGroup, \
    DeviceRegistrationState
import provisioningserviceclient


def _is_successful(status_code):
    """
    Return true if HTTP operation is successful, false if not

    :param int status_code: HTTP status code

    :return: A boolean indicating if the operation was a success
    :rtype: bool
    """
    if status_code in [200, 204]:
        result = True
    else:
        result = False
    return result


def _copy_and_unwrap_bulkop(bulk_op):
    """
    Make a new copy of a BulkEnrollmentOperation that replaces the listed enrollments with their
    internal values

    :param bulk_op: An instance of :class:`BulkEnrollmentOperation
     <provisioningserviceclient.BulkEnrollmentOperation>`
    :type bulk_op: :class:`BulkEnrollmentOperation
     <provisioningserviceclient.BulkEnrollmentOperation>`

    :return: A new instance of :class:`BulkEnrollmentOperation
     <provisioningserviceclient.BulkEnrollmentOperation>`
    :rtype: :class:`BulkEnrollmentOperation<provisioningserviceclient.BulkEnrollmentOperation>`
    """
    new_enrollments = []
    for i in range(len(bulk_op.enrollments)):
        new_enrollments.append(bulk_op.enrollments[i]._internal)
    return BulkEnrollmentOperation(bulk_op.mode, new_enrollments)


class BulkEnrollmentOperation(genmodels.BulkEnrollmentOperation):
    """
    Structure for the details of a Bulk Enrollment Operation

    :param str mode: Operation mode. Possible values include: 'create', 'update',
     'updateIfMatchETag', 'delete'
    :param enrollments: List of enrollments
    :type enrollments: list[:class:`IndividualEnrollment
     <provisioningserviceclient.models.IndividualEnrollment>`]
    """
    pass


class BulkEnrollmentOperationResult(genmodels.BulkEnrollmentOperationResult):
    """
    Contains the results of a Bulk Enrollment Operation

    :param is_successful: Indicates if the operation was successful in its
     entirety
    :type is_successful: bool
    :param errors: Registration errors
    :type errors: list[:class:`BulkEnrollmentOperationError
     <provisioningserviceclient.BulkEnrollmentOperationError>`]
    """
    pass


class BulkEnrollmentOperationError(genmodels.BulkEnrollmentOperationError):
    """
    Contains the details of a single error in conducting a Bulk Enrollment Operation

    :param registration_id: Device registration id.
    :type registration_id: str
    :param error_code: Error code
    :type error_code: int
    :param error_status: Error status
    :type error_status: str
    """
    pass


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
    err_msg_unexpected = "Unexpected response {} from the Provisioning Service"

    def __init__(self, host_name, shared_access_key_name, shared_access_key):
        https_prefix = "https://"

        self.host_name = host_name
        self.shared_access_key_name = shared_access_key_name
        self.shared_access_key = shared_access_key
        self._runtime_client = DeviceProvisioningServiceServiceRuntimeClient(
            https_prefix + self.host_name)
        self._sastoken_factory = sastoken.SasTokenFactory(
            self.host_name, self.shared_access_key_name, self.shared_access_key)

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
        cs_delimiter = ";"
        cs_val_separator = "="
        host_name_label = "HostName"
        shared_access_key_name_label = "SharedAccessKeyName"
        shared_access_key_label = "SharedAccessKey"

        cs_args = connection_string.split(cs_delimiter)

        if len(cs_args) != 3:
            raise ValueError("Too many or too few values in the connection string")
        if len(cs_args) > len(set(cs_args)):
            raise ValueError("Duplicate label in connection string")

        #host_name = None
        #shared_access_key = None
        #shared_access_key_name = None
        for arg in cs_args:
            tokens = arg.split(cs_val_separator, 1)

            if tokens[0] == host_name_label:
                host_name = tokens[1]
            elif tokens[0] == shared_access_key_name_label:
                shared_access_key_name = tokens[1]
            elif tokens[0] == shared_access_key_label:
                shared_access_key = tokens[1]
            else:
                raise ValueError("Connection string contains incorrect values")

        return cls(host_name, shared_access_key_name, shared_access_key)

    def _gen_sastoken_str(self):
        """
        Generate a Sas Token from the internal factory

        :return: A string representation of a new Sas Token
        :rtype: str
        """
        return str(self._sastoken_factory.generate_sastoken())

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
            operation = self._runtime_client.device_enrollment.create_or_update
            id = provisioning_model.registration_id
        elif isinstance(provisioning_model, EnrollmentGroup):
            operation = self._runtime_client.device_enrollment_group.create_or_update
            id = provisioning_model.enrollment_group_id
        else:
            raise TypeError("given object must be IndividualEnrollment or EnrollmentGroup")

        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()

        try:
            raw_resp = operation(id, provisioning_model._internal, provisioning_model.etag, \
                custom_headers, True)
        except genmodels.ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(
                self.err_msg_unexpected.format(e.response.status_code), e)

        if not _is_successful(raw_resp.response.status_code):
            raise ProvisioningServiceError(raw_resp.response.reason)

        result = raw_resp.output
        return models._wrap_internal_model(result)

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
        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()

        try:
            raw_resp = self._runtime_client.device_enrollment.get(
                registration_id, custom_headers, True)
        except genmodels.ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(
                self.err_msg_unexpected.format(e.response.status_code), e)

        if not _is_successful(raw_resp.response.status_code):
            raise ProvisioningServiceError(raw_resp.response.reason)

        result = raw_resp.output
        return IndividualEnrollment(result)

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
        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()

        try:
            raw_resp = self._runtime_client.device_enrollment_group.get(
                group_id, custom_headers, True)
        except genmodels.ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(
                self.err_msg_unexpected.format(e.response.status_code), e)

        if not _is_successful(raw_resp.response.status_code):
            raise ProvisioningServiceError(raw_resp.response.reason)

        result = raw_resp.output
        return EnrollmentGroup(result)

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
        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()

        try:
            raw_resp = self._runtime_client.registration_state.get_registration_state(\
                registration_id, custom_headers, True)
        except genmodels.ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(
                self.err_msg_unexpected.format(e.response.status_code), e)

        if not _is_successful(raw_resp.response.status_code):
            raise ProvisioningServiceError(raw_resp.response.reason)

        result = raw_resp.output
        return DeviceRegistrationState(result)

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
        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()

        try:
            raw_resp = self._runtime_client.device_enrollment.delete(registration_id, etag, \
                custom_headers, True)
        except genmodels.ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(
                self.err_msg_unexpected.format(e.response.status_code), e)

        if not _is_successful(raw_resp.response.status_code):
            raise ProvisioningServiceError(raw_resp.response.reason)

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
        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()

        try:
            raw_resp = self._runtime_client.device_enrollment_group.delete(
                group_id, etag, custom_headers, True)
        except genmodels.ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(
                self.err_msg_unexpected.format(e.response.status_code), e)

        if not _is_successful(raw_resp.response.status_code):
            raise ProvisioningServiceError(raw_resp.response.reason)

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
        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()

        try:
            raw_resp = self._runtime_client.registration_state.delete_registration_state(
                registration_id, etag, custom_headers, True)
        except genmodels.ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(self.err_msg_unexpected.format(e.response.status_code), e)

        if not _is_successful(raw_resp.response.status_code):
            raise ProvisioningServiceError(raw_resp.response.reason)

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
        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()

        internal_bulkop = _copy_and_unwrap_bulkop(bulk_op)

        try:
            raw_resp = self._runtime_client.device_enrollment.bulk_operation(internal_bulkop, custom_headers, True)
        except genmodels.ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(self.err_msg_unexpected.format(e.response.status_code), e)

        if not _is_successful(raw_resp.response.status_code):
            raise ProvisioningServiceError(raw_resp.response.reason)

        result = raw_resp.output
        result.__class__ = BulkEnrollmentOperationResult
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
        query_fn = self._runtime_client.device_enrollment.query
        return Query(query_spec, query_fn, self._sastoken_factory, page_size)

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
        query_fn = self._runtime_client.device_enrollment_group.query
        return Query(query_spec, query_fn, self._sastoken_factory, page_size)

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
        query_fn = self._runtime_client.registration_state.query_registration_state
        return Query(reg_id, query_fn, self._sastoken_factory, page_size)


class QuerySpecification(genmodels.QuerySpecification):
    """
    Contains details of a query to be made to the Provisioning Service
    :param str query: The query details
    """
    pass

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
    authorization_header = "Authorization"
    err_msg_unexpected = "Unexpected response {} from the Provisioning Service"

    def __init__(self, query_spec_or_id, query_fn, sastoken_factory, page_size=None):
        self._query_spec_or_id = query_spec_or_id
        self._query_fn = query_fn
        self.page_size = page_size
        self._sastoken_factory = sastoken_factory
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

        custom_headers = {}
        custom_headers[Query.authorization_header] = str(self._sastoken_factory.generate_sastoken())
        custom_headers[Query.continuation_token_header] = continuation_token
        custom_headers[Query.page_size_header] = page_size

        raw_resp = self._query_fn(self._query_spec_or_id, custom_headers, True)

        if not raw_resp.output:
            raise StopIteration("No more results")

        self.continuation_token = raw_resp.headers[Query.continuation_token_header]
        self.has_next = self.continuation_token != None

        #convert results to wrapper class
        output = []
        for item in raw_resp.output:
            output.append(models._wrap_internal_model(item))

        return output
