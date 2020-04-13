# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.protocol.models import AuthenticationMechanism
from azure.iot.hub.iothub_job_manager import IoTHubJobManager
from azure.iot.hub.auth import ConnectionStringAuthentication
from azure.iot.hub.protocol.iot_hub_gateway_service_ap_is import IotHubGatewayServiceAPIs

"""---Constants---"""

fake_hostname = "beauxbatons.academy-net"
fake_device_id = "MyPensieve"
fake_shared_access_key_name = "alohomora"
fake_shared_access_key = "Zm9vYmFy"
fake_job_properties = "fake_job_properties"
fake_job_id = "fake_job_id"
fake_job_request = "fake_job_request"
fake_job_type = "fake_job_type"
fake_job_status = "fake_job_status"


"""----Shared fixtures----"""


@pytest.fixture(scope="function", autouse=True)
def mock_job_client_operations(mocker):
    mock_job_client_operations_init = mocker.patch(
        "azure.iot.hub.protocol.iot_hub_gateway_service_ap_is.JobClientOperations"
    )
    return mock_job_client_operations_init.return_value


@pytest.fixture(scope="function")
def iothub_job_manager():
    connection_string = "HostName={hostname};DeviceId={device_id};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
        hostname=fake_hostname,
        device_id=fake_device_id,
        skn=fake_shared_access_key_name,
        sk=fake_shared_access_key,
    )
    iothub_job_manager = IoTHubJobManager(connection_string)
    return iothub_job_manager


@pytest.mark.describe("IoTHubJobManager - Instantiation")
class TestJobManager(object):
    @pytest.mark.it("Instantiation sets the auth and protocol attributes")
    def test_instantiates_auth_and_protocol_attributes(self, iothub_job_manager):
        assert isinstance(iothub_job_manager.auth, ConnectionStringAuthentication)
        assert isinstance(iothub_job_manager.protocol, IotHubGatewayServiceAPIs)

    @pytest.mark.it(
        "Raises a ValueError exception when instantiated with an empty connection string"
    )
    def test_instantiates_with_empty_connection_string(self):
        with pytest.raises(ValueError):
            IoTHubJobManager("")

    @pytest.mark.it(
        "Raises a ValueError exception when instantiated with a connection string without HostName"
    )
    def test_instantiates_with_connection_string_no_host_name(self):
        connection_string = "DeviceId={device_id};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
            device_id=fake_device_id, skn=fake_shared_access_key_name, sk=fake_shared_access_key
        )
        with pytest.raises(ValueError):
            IoTHubJobManager(connection_string)

    @pytest.mark.it("Instantiates with an connection string without DeviceId")
    def test_instantiates_with_connection_string_no_device_id(self):
        connection_string = "HostName={hostname};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
            hostname=fake_hostname, skn=fake_shared_access_key_name, sk=fake_shared_access_key
        )
        obj = IoTHubJobManager(connection_string)
        assert isinstance(obj, IoTHubJobManager)

    @pytest.mark.it("Instantiates with an connection string without SharedAccessKeyName")
    def test_instantiates_with_connection_string_no_shared_access_key_name(self):
        connection_string = "HostName={hostname};DeviceId={device_id};SharedAccessKey={sk}".format(
            hostname=fake_hostname, device_id=fake_device_id, sk=fake_shared_access_key
        )
        obj = IoTHubJobManager(connection_string)
        assert isinstance(obj, IoTHubJobManager)

    @pytest.mark.it(
        "Raises a ValueError exception when instantiated with a connection string without SharedAccessKey"
    )
    def test_instantiates_with_connection_string_no_shared_access_key(self):
        connection_string = "HostName={hostname};DeviceId={device_id};SharedAccessKeyName={skn}".format(
            hostname=fake_hostname, device_id=fake_device_id, skn=fake_shared_access_key_name
        )
        with pytest.raises(ValueError):
            IoTHubJobManager(connection_string)


@pytest.mark.describe("IoTHubJobManager - .create_import_export_job()")
class TestCreateImportExportJob(object):
    @pytest.mark.it("Uses protocol layer Job Client runtime to create an export/import job")
    def test_create_export_import_job(self, mocker, mock_job_client_operations, iothub_job_manager):
        ret_val = iothub_job_manager.create_import_export_job(fake_job_properties)
        assert mock_job_client_operations.create_import_export_job.call_count == 1
        assert mock_job_client_operations.create_import_export_job.call_args == mocker.call(
            fake_job_properties
        )
        assert ret_val == mock_job_client_operations.create_import_export_job()


@pytest.mark.describe("IoTHubJobManager - .get_import_export_jobs()")
class TestGetImportExportJobs(object):
    @pytest.mark.it("Uses protocol layer Job Client runtime to get an export/import jobs")
    def test_get_export_import_jobs(self, mocker, mock_job_client_operations, iothub_job_manager):
        ret_val = iothub_job_manager.get_import_export_jobs()
        assert mock_job_client_operations.get_import_export_jobs.call_count == 1
        assert mock_job_client_operations.get_import_export_jobs.call_args == mocker.call()
        assert ret_val == mock_job_client_operations.get_import_export_jobs()


@pytest.mark.describe("IoTHubJobManager - .get_import_export_job()")
class TestGetImportExportJob(object):
    @pytest.mark.it("Uses protocol layer Job Client runtime to get an export/import job")
    def test_get_export_import_job(self, mocker, mock_job_client_operations, iothub_job_manager):
        ret_val = iothub_job_manager.get_import_export_job(fake_job_id)
        assert mock_job_client_operations.get_import_export_job.call_count == 1
        assert mock_job_client_operations.get_import_export_job.call_args == mocker.call(
            fake_job_id
        )
        assert ret_val == mock_job_client_operations.get_import_export_job()


@pytest.mark.describe("IoTHubJobManager - .cancel_import_export_job()")
class TestCancelImportExportJob(object):
    @pytest.mark.it("Uses protocol layer Job Client runtime to cancel an export/import job")
    def test_cancel_import_export_job(self, mocker, mock_job_client_operations, iothub_job_manager):
        ret_val = iothub_job_manager.cancel_import_export_job(fake_job_id)
        assert mock_job_client_operations.cancel_import_export_job.call_count == 1
        assert mock_job_client_operations.cancel_import_export_job.call_args == mocker.call(
            fake_job_id
        )
        assert ret_val == mock_job_client_operations.cancel_import_export_job()


@pytest.mark.describe("IoTHubJobManager - .create_job()")
class TestCreateJob(object):
    @pytest.mark.it("Uses protocol layer Job Client runtime to create a job")
    def test_create_job(self, mocker, mock_job_client_operations, iothub_job_manager):
        ret_val = iothub_job_manager.create_job(fake_job_id, fake_job_request)
        assert mock_job_client_operations.create_job.call_count == 1
        assert mock_job_client_operations.create_job.call_args == mocker.call(
            fake_job_id, fake_job_request
        )
        assert ret_val == mock_job_client_operations.create_job()


@pytest.mark.describe("IoTHubJobManager - .get_job()")
class TestGetJob(object):
    @pytest.mark.it("Uses protocol layer Job Client runtime to get a job")
    def test_get_job(self, mocker, mock_job_client_operations, iothub_job_manager):
        ret_val = iothub_job_manager.get_job(fake_job_id)
        assert mock_job_client_operations.get_job.call_count == 1
        assert mock_job_client_operations.get_job.call_args == mocker.call(fake_job_id)
        assert ret_val == mock_job_client_operations.get_job()


@pytest.mark.describe("IoTHubJobManager - .cancel_job()")
class TestCancelJob(object):
    @pytest.mark.it("Uses protocol layer Job Client runtime to cancel a job")
    def test_get_job(self, mocker, mock_job_client_operations, iothub_job_manager):
        ret_val = iothub_job_manager.cancel_job(fake_job_id)
        assert mock_job_client_operations.cancel_job.call_count == 1
        assert mock_job_client_operations.cancel_job.call_args == mocker.call(fake_job_id)
        assert ret_val == mock_job_client_operations.cancel_job()


@pytest.mark.describe("IoTHubJobManager - .query_jobs()")
class TestQueryJob(object):
    @pytest.mark.it("Uses protocol layer Job Client runtime to query a job")
    def test_get_job(self, mocker, mock_job_client_operations, iothub_job_manager):
        ret_val = iothub_job_manager.query_jobs(fake_job_type, fake_job_status)
        assert mock_job_client_operations.query_jobs.call_count == 1
        assert mock_job_client_operations.query_jobs.call_args == mocker.call(
            fake_job_type, fake_job_status
        )
        assert ret_val == mock_job_client_operations.query_jobs()
