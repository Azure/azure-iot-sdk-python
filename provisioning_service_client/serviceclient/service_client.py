# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

from service import DeviceProvisioningServiceServiceRuntimeClient
from service import VERSION
from models import *
from sastoken import SasTokenFactory
from query import Query


class ProvisioningServiceClient(object):
    """
    API for conducting operations on the Provisioning Service

    Parameters:
    conn_str (str): Connection String for your Device Provisioning Service

    """

    authorization_header = "Authorization"

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

    def create_or_update(self, target_obj):
        """
        Create or update an object on the Provisioning Service

        Parameters:
        target_obj: IndividualEnrollment, EnrollmentGroup or DeviceRegistrationState to be created/updated

        Returns:
        Resulting object from the create or update operation
        """
        obj_type = type(target_obj)
        if obj_type == IndividualEnrollment:
            operation = self._runtime_client.device_enrollment.create_or_update
            id = target_obj.registration_id
        elif obj_type == EnrollmentGroup:
            operation = self._runtime_client.device_enrollment_group.create_or_update
            id = target_obj.enrollment_group_id
        else:
            raise TypeError("given object must be IndividualEnrollment or EnrollmentGroup")

        custom_headers = {}
        custom_headers[ProvisioningServiceClient.authorization_header] = self._gen_sastoken_str()
        return operation(id, target_obj, VERSION, target_obj.etag, custom_headers)

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
        return self._runtime_client.device_enrollment.get(reg_id, VERSION, custom_headers)

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
        return self._runtime_client.device_enrollment_group.get(grp_id, VERSION, custom_headers)

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
        return self._runtime_client.registration_status.get_registration_state(reg_id, VERSION, custom_headers)

    def delete(self, target_obj):
        """
        Delete an object on the Provisioning Service

        Parameters:
        target_obj: IndividualEnrollment, EnrollmentGroup or DeviceRegistrationState to be created/updated
        """
        obj_type = type(target_obj)
        if obj_type == IndividualEnrollment:
            self.delete_individual_enrollment_by_param(target_obj.registration_id, target_obj.etag)
        elif obj_type == EnrollmentGroup:
            self.delete_enrollment_group_by_param(target_obj.enrollment_group_id, target_obj.etag)
        elif obj_type == DeviceRegistrationState:
            self.delete_registration_state_by_param(target_obj.registration_id, target_obj.etag)
        else:
            raise TypeError("Given object must be IndividualEnrollment, EnrollmentGroup or DeviceRegistrationState")

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
        self._runtime_client.device_enrollment.delete(reg_id, VERSION, etag, custom_headers)
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
        self._runtime_client.device_enrollment_group.delete(grp_id, VERSION, etag, custom_headers)
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
        self._runtime_client.registration_status.delete_registration_state(reg_id, VERSION, etag, custom_headers)
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
        return self._runtime_client.device_enrollment.bulk_operation(bulk_op, VERSION, custom_headers)

    def create_individual_enrollment_query(self, query_spec, page_size=10):
        """
        Create a Query object to access results of a Provisioning Service query

        Parameters:
        query_spec (QuerySpecification): The specification for the query
        page_size (int)[default 10]: Results per page

        Returns:
        Query object that can iterate through results of the query
        """
        query_fn = self._runtime_client.device_enrollment.query
        return Query(query_spec, query_fn, self._sastoken_factory, page_size, VERSION)
