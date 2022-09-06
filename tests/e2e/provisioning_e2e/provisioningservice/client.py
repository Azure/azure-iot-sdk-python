# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

from .utils import auth

# from .protocol import GeneratedProvisioningServiceClient
from .protocol.models import (
    # IndividualEnrollment,
    # EnrollmentGroup,
    # DeviceRegistrationState,
    ProvisioningServiceErrorDetailsException,
)
from msrest.service_client import SDKClient
from msrest import Configuration, Serializer, Deserializer
from .protocol.version import VERSION

from msrest.pipeline import ClientRawResponse
from .protocol import models
import logging

BULKOP_CREATE = "create"
BULKOP_DELETE = "delete"
BULKOP_UPDATE = "update"
BULKOP_UPDATE_IF_MATCH_ETAG = "updateIfMatchETag"

ENROLLMENTS_URL = "/enrollments/{id}/"
ENROLLMENT_GROUPS_URL = "/enrollmentGroups/{id}"
REGISTRATIONS_URL = "/registrations/{id}"

logging.basicConfig(level=logging.DEBUG, filename="sync_enroll.log")


def _unwrap_model(model):
    if model.initial_twin:  # LBYL for efficiency - nothing exceptional about this situation
        model.initial_twin = model.initial_twin._unwrap()


def _wrap_model(model):
    if model.initial_twin:
        model.initial_twin = model.initial_twin._wrap()


class GeneratedProvisioningServiceClientConfiguration(Configuration):
    """Configuration for ProvisioningServiceClient
    Note that all parameters used to create this instance are saved as instance
    attributes.

    :param credentials: Subscription credentials which uniquely identify
     client subscription.
    :type credentials: None
    :param str base_url: Service URL
    """

    def __init__(self, credentials, base_url=None):

        if credentials is None:
            raise ValueError("Parameter 'credentials' must not be None.")
        if not base_url:
            base_url = "https://localhost"

        super(GeneratedProvisioningServiceClientConfiguration, self).__init__(base_url)

        self.add_user_agent("provisioningserviceclient/{}".format(VERSION))

        self.credentials = credentials


class ProvisioningServiceError(Exception):
    """
    An error from the Device Provisioning Service

    :param str message: Error message
    :param Exception cause: Error that causes this error (optional)
    """

    def __init__(self, message, cause=None):
        super(ProvisioningServiceError, self).__init__(message)
        self.cause = cause


class ProvisioningServiceClient(SDKClient):
    """
    API for connecting to, and conducting operations on a Device Provisioning Service

    :param str host_name: The host name of the Device Provisioning Service
    :param str shared_access_key_name: The shared access key name of the
     Device Provisioning Service
    :param str shared_access_key: The shared access key of the Device Provisioning Service
    """

    authorization_header = "Authorization"
    err_msg = "Service Error {} - {}"
    _cs_delimiter = ";"
    _cs_val_separator = "="
    _host_name_label = "HostName"
    _shared_access_key_name_label = "SharedAccessKeyName"
    _shared_access_key_label = "SharedAccessKey"

    def __init__(self, host_name, shared_access_key_name, shared_access_key):

        self.host_name = host_name
        self.shared_access_key_name = shared_access_key_name
        self.shared_access_key = shared_access_key

        # Build connection string
        credentials = auth.ConnectionStringAuthentication.create_with_parsed_values(
            self.host_name, self.shared_access_key_name, self.shared_access_key
        )
        base_url = "https://" + self.host_name
        self.config = GeneratedProvisioningServiceClientConfiguration(credentials, base_url)
        super(ProvisioningServiceClient, self).__init__(self.config.credentials, self.config)

        client_models = {k: v for k, v in models.__dict__.items() if isinstance(v, type)}
        self.api_version = VERSION  # "2018-09-01-preview"
        self._serialize = Serializer(client_models)
        self._deserialize = Deserializer(client_models)

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
        cs_args = connection_string.split(cls._cs_delimiter)

        if len(cs_args) != 3:
            raise ValueError("Too many or too few values in the connection string")
        if len(cs_args) > len(set(cs_args)):
            raise ValueError("Duplicate label in connection string")

        for arg in cs_args:
            tokens = arg.split(cls._cs_val_separator, 1)

            if tokens[0] == cls._host_name_label:
                host_name = tokens[1]
            elif tokens[0] == cls._shared_access_key_name_label:
                shared_access_key_name = tokens[1]
            elif tokens[0] == cls._shared_access_key_label:
                shared_access_key = tokens[1]
            else:
                raise ValueError("Connection string contains incorrect values")

        return cls(host_name, shared_access_key_name, shared_access_key)

    def create_or_update_individual_enrollment(
        self, enrollment, etag=None, custom_headers=None, raw=False, **operation_config
    ):
        """Create or update a device enrollment record.
        :param enrollment: The device enrollment record.
        :type enrollment: ~protocol.models.IndividualEnrollment
        :param etag: The ETag of the enrollment record.
        :type etag: str
        :param dict custom_headers: headers that will be added to the request
        :param bool raw: returns the direct response alongside the
        deserialized response
        :param operation_config: :ref:`Operation configuration
        overrides<msrest:optionsforoperations>`.
        :return: IndividualEnrollment or ClientRawResponse if raw=true
        :rtype: ~protocol.models.IndividualEnrollment or
        ~msrest.pipeline.ClientRawResponse
        :raises:
        :class:`ProvisioningServiceErrorDetailsException<protocol.models.ProvisioningServiceErrorDetailsException>`
        """
        result = None
        path_format_arguments = {"id": self._serialize.url("id", enrollment.registration_id, "str")}
        url = self._client.format_url(ENROLLMENTS_URL, **path_format_arguments)

        # Construct parameters
        query_parameters = {}
        query_parameters["api-version"] = self._serialize.query(
            "self.api_version", self.api_version, "str"
        )

        # Construct headers
        header_parameters = {}
        header_parameters["Accept"] = "application/json"
        header_parameters["Content-Type"] = "application/json; charset=utf-8"
        if custom_headers:
            header_parameters.update(custom_headers)
        if etag is not None:
            header_parameters["If-Match"] = self._serialize.header("if_match", etag, "str")

        # Construct body
        body_content = self._serialize.body(enrollment, "IndividualEnrollment")

        # Construct and send request
        request = self._client.put(url, query_parameters, header_parameters, body_content)
        response = self._client.send(request, stream=False, **operation_config)

        if response.status_code not in [200]:
            raise models.ProvisioningServiceErrorDetailsException(self._deserialize, response)

        if response.status_code == 200:
            result = self._deserialize("IndividualEnrollment", response)

        if raw:
            client_raw_response = ClientRawResponse(result, response)
            return client_raw_response

        # return result

        _wrap_model(enrollment)  # rewrap input
        _wrap_model(result)
        return result

        # create_or_update_individual_enrollment.metadata = {"url": "/enrollments/{id}"}

    def create_or_update_enrollment_group(self, provisioning_model):
        pass

    # def get_individual_enrollment(
    #     self, registration_id, custom_headers=None, raw=False, **operation_config
    # ):
    #     """
    #     Retrieve an Individual Enrollment from the Provisioning Service
    #
    #     :param str registration_id: The registration id of the target Individual Enrollment
    #     :param dict custom_headers: headers that will be added to the request
    #     :param bool raw: returns the direct response alongside the deserialized response
    #     :param operation_config: :ref:`Operation configuration overrides<msrest:optionsforoperations>`.
    #     :returns: Individual Enrollment from the Provisioning Service corresponding to the given
    #      registration id
    #     :rtype: :class:`IndividualEnrollment<provisioningserviceclient.models.IndividualEnrollment>`
    #     :raises: :class:ProvisioningServiceError <provisioningserviceclient.ProvisioningServiceError>` if an error occurs on the
    #      Provisioning Service
    #     """
    #     result = None
    #     # Construct URL
    #     url = self.get_individual_enrollment.metadata["url"]
    #     path_format_arguments = {"id": self._serialize.url("id", registration_id, "str")}
    #     url = self._client.format_url(url, **path_format_arguments)
    #
    #     # Construct parameters
    #     query_parameters = {}
    #     query_parameters["api-version"] = self._serialize.query(
    #         "self.api_version", self.api_version, "str"
    #     )
    #
    #     # Construct headers
    #     header_parameters = {}
    #     header_parameters["Accept"] = "application/json"
    #     if custom_headers:
    #         header_parameters.update(custom_headers)
    #
    #     # Construct and send request
    #     request = self._client.get(url, query_parameters, header_parameters)
    #     response = self._client.send(request, stream=False, **operation_config)
    #
    #     if response.status_code not in [200]:
    #         raise models.ProvisioningServiceErrorDetailsException(self._deserialize, response)
    #
    #     if response.status_code == 200:
    #         result = self._deserialize("IndividualEnrollment", response)
    #
    #     if raw:
    #         result = ClientRawResponse(result, response)
    #     _wrap_model(result)
    #     return result
    #
    #     get_individual_enrollment.metadata = {"url": "/enrollments/{id}"}

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
            result = self._runtime_client.get_enrollment_group(group_id)
        except ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(
                self.err_msg.format(e.response.status_code, e.response.reason), e
            )

        _wrap_model(result)
        return result

    def delete_individual_enrollment_by_param(
        self, registration_id, etag=None, custom_headers=None, raw=False, **operation_config
    ):
        """
        Delete an Individual Enrollment on the Provisioning Service

        :param str registration_id: The registration id of the Individual Enrollment to be deleted
        :param str etag: The etag of the Individual Enrollment to be deleted (optional)
        :param dict custom_headers: headers that will be added to the request
        :param bool raw: returns the direct response alongside the
         deserialized response
        :param operation_config: :ref:`Operation configuration
         overrides<msrest:optionsforoperations>`.
        :return: None or ClientRawResponse if raw=true
        :rtype: None or ~msrest.pipeline.ClientRawResponse
        :raises:
         :class:`ProvisioningServiceErrorDetailsException<protocol.models.ProvisioningServiceErrorDetailsException>`
        """
        path_format_arguments = {"id": self._serialize.url("id", registration_id, "str")}
        url = self._client.format_url(ENROLLMENTS_URL, **path_format_arguments)

        # Construct parameters
        query_parameters = {}
        query_parameters["api-version"] = self._serialize.query(
            "self.api_version", self.api_version, "str"
        )

        # Construct headers
        header_parameters = {}
        if custom_headers:
            header_parameters.update(custom_headers)
        if etag is not None:
            header_parameters["If-Match"] = self._serialize.header("if_match", etag, "str")

        # Construct and send request
        request = self._client.delete(url, query_parameters, header_parameters)
        response = self._client.send(request, stream=False, **operation_config)

        if response.status_code not in [204]:
            raise models.ProvisioningServiceErrorDetailsException(self._deserialize, response)

        if raw:
            client_raw_response = ClientRawResponse(None, response)
            return client_raw_response

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
                self.err_msg.format(e.response.status_code, e.response.reason), e
            )
        return


# class Query(object):
#     """
#     Query object that can be used to iterate over Provisioning Service data.
#     Note that for general usage, Query objects should be generated using a
#     :class:`ProvisioningServiceClient<provisioningserviceclient.ProvisioningServiceClient>`
#     instance, not directly constructed.
#
#     :param query_spec_or_id: The Query Specification or registration id
#     :type query_spec_or_id: :class:`QuerySpecification
#      <provisioningserviceclient.QuerySpecification>` or str
#     :param query_fn: Function pointer to make HTTP query request. Note well that it must take args
#      in the format query_fn(qs: QuerySpecification, cust_headers: dict, raw_resp: bool) or
#      query_fn(id: str, cust_headers: dict, raw_resp:bool) and return an instance of
#      :class:`ClientRawResponse<msrest.pipeline.ClientRawResponse>` when raw_resp == True
#     :type query_fn: Function pointer
#     :param sastoken_factory: Sas Token Factory to generate Sas Tokens
#     :type sastoken_factory: :class:`SasTokenFactory<utils.sastoken.SasTokenFactory>`
#     :param int page_size: Max number of results per page of query response
#     :ivar page_size: Max number of results per page of query response
#     :ivar has_next: Indicates if the Query has more results to return
#     :ivar continuation_token: Token indicating current position in list of results
#     :raises: TypeError if given invalid type
#     """
#
#     page_size_header = "x-ms-max-item-count"
#     continuation_token_header = "x-ms-continuation"
#     item_type_header = "x-ms-item-type"
#
#     err_msg = "Service Error {} - {}"
#
#     def __init__(self, query_spec_or_id, query_fn, page_size=None):
#         self._query_spec_or_id = query_spec_or_id
#         self._query_fn = query_fn
#         self.page_size = page_size
#         self.has_next = True
#         self.continuation_token = None
#
#     def __iter__(self):
#         self.continuation_token = None
#         return self
#
#     def __next__(self):
#         return self.next()
#
#     @property
#     def page_size(self):
#         return self._page_size
#
#     @page_size.setter
#     def page_size(self, value):
#         if value is None or value > 0:
#             self._page_size = value
#         else:
#             raise ValueError("Page size must be a positive number")
#
#     def next(self, continuation_token=None):
#         """
#         Get the next page of query results
#
#         :param str continuation_token: Token indicating a specific starting point in the set
#          of all results
#         :returns: The next page of results
#         :rtype: list[:class:`IndividualEnrollment
#          <provisioningserviceclient.models.IndividualEnrollment>`]
#         :raises: StopIteration if there are no more results or
#          :class:`ProvisioningServiceError<provisioningserviceclient.ProvisioningServiceError>` if an
#          error occurs on the Provisioning Service
#         """
#         if not self.has_next:
#             raise StopIteration("No more results")
#
#         if not continuation_token:
#             continuation_token = self.continuation_token
#
#         if self.page_size is not None:
#             page_size = str(self._page_size)
#         else:
#             page_size = self._page_size
#
#         try:
#             raw_resp = self._query_fn(
#                 self._query_spec_or_id, page_size, continuation_token, raw=True
#             )
#         except ProvisioningServiceErrorDetailsException as e:
#             raise ProvisioningServiceError(
#                 self.err_msg.format(e.response.status_code, e.response.reason), e
#             )
#
#         if not raw_resp.output:
#             raise StopIteration("No more results")
#
#         self.continuation_token = raw_resp.headers[Query.continuation_token_header]
#         self.has_next = self.continuation_token is not None
#
#         # wrap results
#         output = []
#         for item in raw_resp.output:
#             _wrap_model(item)
#             output.append(item)
#
#         return output
