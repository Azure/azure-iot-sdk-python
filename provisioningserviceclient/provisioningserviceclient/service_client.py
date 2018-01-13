# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

from utils.sastoken import SasTokenFactory
from serviceswagger import DeviceProvisioningServiceServiceRuntimeClient
import serviceswagger.models as genmodels
import provisioningserviceclient.models as models
from provisioningserviceclient.models import IndividualEnrollment, EnrollmentGroup, \
    DeviceRegistrationState
from provisioningserviceclient.query import Query
import provisioningserviceclient


def _is_successful(status_code):
    """
    Return true if successful, false if not
    """
    if status_code in [200, 204]:
        result = True
    else:
        result = False
    return result


class BulkEnrollmentOperation(genmodels.BulkEnrollmentOperation):
    pass

class BulkEnrollmentOperationResult(genmodels.BulkEnrollmentOperationResult):
    pass

class BulkEnrollmentOperationError(genmodels.BulkEnrollmentOperationError):
    pass

class ProvisioningServiceError(Exception):
    def __init__(self, message, cause=None):
        super(ProvisioningServiceError, self).__init__(message)
        self.cause = cause

class ProvisioningServiceClient(object):
    """
    API for conducting operations on the Provisioning Service

    Parameters:
    conn_str (str): Connection String for your Device Provisioning Service
    """

    authorization_header = "Authorization"
    err_msg_unexpected = "Unexpected response {} from the Provisioning Service"

    def __init__(self, conn_str):
        conn_str_delimiter = ";"
        conn_str_val_separator = "="
        host_name_label = "HostName"
        shared_access_key_name_label = "SharedAccessKeyName"
        shared_access_key_label = "SharedAccessKey"
        https_prefix = "https://"

        cs_args = conn_str.split(conn_str_delimiter)

        if len(cs_args) != 3:
            raise ValueError("Too many or too few values in the connection string")
        if len(cs_args) > len(set(cs_args)):
            raise ValueError("Duplicate label in connection string")

        for arg in cs_args:
            tokens = arg.split(conn_str_val_separator, 1)

            if tokens[0] == host_name_label:
                self.host_name = tokens[1]
            elif tokens[0] == shared_access_key_name_label:
                self.shared_access_key_name = tokens[1]
            elif tokens[0] == shared_access_key_label:
                self.shared_access_key = tokens[1]
            else:
                raise ValueError("Connection string contains incorrect values")

        self._runtime_client = DeviceProvisioningServiceServiceRuntimeClient(https_prefix + self.host_name)
        self._sastoken_factory = SasTokenFactory(self.host_name, self.shared_access_key_name, self.shared_access_key)

    def _gen_sastoken_str(self):
        return str(self._sastoken_factory.generate_sastoken())

    def create_or_update(self, model):
        """
        Create or update an object on the Provisioning Service

        Parameters:
        model: IndividualEnrollment, EnrollmentGroup or DeviceRegistrationState to be created/updated

        Returns:
        Resulting object from the create or update operation
        """
        if isinstance(model, IndividualEnrollment):
            operation = self._runtime_client.device_enrollment.create_or_update
            id = model.registration_id
        elif isinstance(model, EnrollmentGroup):
            operation = self._runtime_client.device_enrollment_group.create_or_update
            id = model.enrollment_group_id
        else:
            raise TypeError("given object must be IndividualEnrollment or EnrollmentGroup")

        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()

        try:
            raw_resp = operation(id, model._internal, model.etag, custom_headers, True)
        except genmodels.ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(self.err_msg_unexpected.format(e.response.status_code), e)

        if not _is_successful(raw_resp.response.status_code):
            raise ProvisioningServiceError(raw_resp.response.reason)

        result = raw_resp.output
        return models._wrap_internal_model(result)

    def get_individual_enrollment(self, reg_id):
        """
        Retrieve an IndividualEnrollment from the Provisioning Service

        Parameters:
        reg_id (str): Registration ID of the IndividualEnrollment to be retrieved
        
        Returns:
        IndvidualEnrollment from the Provisioning Service corresponding to reg_id
        """
        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()

        try:
            raw_resp = self._runtime_client.device_enrollment.get(reg_id, custom_headers, True)
        except genmodels.ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(self.err_msg_unexpected.format(e.response.status_code), e)

        if not _is_successful(raw_resp.response.status_code):
            raise ProvisioningServiceError(raw_resp.response.reason)

        result = raw_resp.output
        return IndividualEnrollment(result)

    def get_enrollment_group(self, grp_id):
        """
        Retrieve an EnrollmentGroup from the Provisioning Service

        Parameters:
        grp_id (str): Group ID of the EnrollmentGroup to be retrieved
        
        Returns:
        EnrollmentGroup from the Provisioning Service corresponding to grp_id
        """
        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()

        try:
            raw_resp = self._runtime_client.device_enrollment_group.get(grp_id, custom_headers, True)
        except genmodels.ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(self.err_msg_unexpected.format(e.response.status_code), e)

        
        if not _is_successful(raw_resp.response.status_code):
            raise ProvisioningServiceError(raw_resp.response.reason)

        result = raw_resp.output
        return EnrollmentGroup(result)

    def get_registration_state(self, reg_id):
        """
        Retrieve a DeviceRegistrationState from the Provisioning Service

        Parameters:
        reg_id (str): Registration ID of the DeviceRegistrationState to be retrieved

        Returns:
        DeviceRegistrationState from the Provisioning Service corresponding to reg_id
        """
        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()

        try:
            raw_resp = self._runtime_client.registration_state.get_registration_state(reg_id, custom_headers, True)
        except genmodels.ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(self.err_msg_unexpected.format(e.response.status_code), e)

        if not _is_successful(raw_resp.response.status_code):
            raise ProvisioningServiceError(raw_resp.response.reason)

        result = raw_resp.output
        return DeviceRegistrationState(result)

    def delete(self, model):
        """
        Delete an object on the Provisioning Service

        Parameters:
        model: IndividualEnrollment, EnrollmentGroup or DeviceRegistrationState to be created/updated
        """
        if isinstance(model, IndividualEnrollment):
            self.delete_individual_enrollment_by_param(model.registration_id, model.etag)
        elif isinstance(model, EnrollmentGroup):
            self.delete_enrollment_group_by_param(model.enrollment_group_id, model.etag)
        elif isinstance(model, DeviceRegistrationState):
            self.delete_registration_state_by_param(model.registration_id, model.etag)
        else:
            raise TypeError("Given model must be IndividualEnrollment, EnrollmentGroup or DeviceRegistrationState")
        return

    def delete_individual_enrollment_by_param(self, reg_id, etag=None):
        """
        Delete an IndividualEnrollment on the Provisioning Service

        Parameters:
        reg_id (str): Registration ID of the target IndividualEnrollment
        etag (str)[optional]: Etag of the target IndividualEnrollment
        """
        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()

        try:
            raw_resp = self._runtime_client.device_enrollment.delete(reg_id, etag, custom_headers, True)
        except genmodels.ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(self.err_msg_unexpected.format(e.response.status_code), e)

        if not _is_successful(raw_resp.response.status_code):
            raise ProvisioningServiceError(raw_resp.response.reason)

        return

    def delete_enrollment_group_by_param(self, grp_id, etag=None):
        """
        Delete an EnrollmentGroup on the Provisioning Service

        Parameters:
        grp_id (str): Group ID of the target EnrollmentGroup
        etag (str)[optional]: Etag of the target EnrollmentGroup
        """
        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()
        
        try:
            raw_resp = self._runtime_client.device_enrollment_group.delete(grp_id, etag, custom_headers, True)
        except genmodels.ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(self.err_msg_unexpected.format(e.response.status_code), e)

        if not _is_successful(raw_resp.response.status_code):
            raise ProvisioningServiceError(raw_resp.response.reason)

        return

    def delete_registration_state_by_param(self, reg_id, etag=None):
        """
        Delete a DeviceRegistrationState on the Provisioning Service
        
        Parameters:
        reg_id (str): Registration ID of the target DeviceRegistrationState
        etag (str)[optional]: Etag of the target DeviceRegistrationState
        """
        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()

        try:
            raw_resp = self._runtime_client.registration_state.delete_registration_state(reg_id, etag, custom_headers, True)
        except genmodels.ProvisioningServiceErrorDetailsException as e:
            raise ProvisioningServiceError(self.err_msg_unexpected.format(e.response.status_code), e)

        if not _is_successful(raw_resp.response.status_code):
            raise ProvisioningServiceError(raw_resp.response.reason)

        return

    def run_bulk_operation(self, bulk_op):
        """
        Run a series of operations on the Provisioning Service
        
        Parameters:
        bulk_op (BulkEnrollmentOperation): Details of the operations to be run

        Returns:
        BulkEnrollmentOperationResult describing results of each operation
        """
        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()

        for i in range(len(bulk_op.enrollments)):
            bulk_op[i] = bulk_op[i]._internal

        try:
            raw_resp = self._runtime_client.device_enrollment.bulk_operation(bulk_op, custom_headers, True)
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
        for IndividualEnrollments

        Parameters:
        query_spec (QuerySpecification): The specification for the query
        page_size (int)[optional]: Max results per page

        Returns:
        Query object that can iterate through results of the query
        """
        query_fn = self._runtime_client.device_enrollment.query
        return provisioningserviceclient.Query(query_spec, query_fn, self._sastoken_factory, page_size)

    def create_enrollment_group_query(self, query_spec, page_size=None):
        """
        Create a Query object to access results of a Provisioning Service query
        for EnrollmentGroups

        Parameters:
        query_spec (QuerySpecification): The specification for the query
        page_size (int)[optional]: Max results per page

        Returns:
        Query object that can iterate through results of the query
        """
        query_fn = self._runtime_client.device_enrollment_group.query
        return Query(query_spec, query_fn, self._sastoken_factory, page_size)

    def create_registration_state_query(self, query_spec, page_size=None):
        """
        Create a Query object to access results of a Provisioning Service query
        for DeviceRegistrationStates

        Parameters:
        query_spec (QuerySpecification): The specification for the query
        page_size (int)[optional]: Max results per page

        Returns:
        Query object that can iterate through results of the query
        """
        raise NotImplementedError("Query Registration State currently unsupported")
        #query_fn = self._runtime_client.registration_state.query_registration_state
        #return Query(query_spec, query_fn, self._sastoken_factory, VERSION, page_size)

