# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.protocol.models import AuthenticationMechanism
from azure.iot.hub.iothub_job_manager import IoTHubJobManager

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


@pytest.mark.describe("IoTHubJobManager - .create_import_export_job()")
class TestCreateImportExportJob(object):
    @pytest.mark.it("Creates export/import job")
    def test_create_export_import_job(self, mocker, mock_job_client_operations, iothub_job_manager):
        iothub_job_manager.create_import_export_job(fake_job_properties)
        assert mock_job_client_operations.create_import_export_job.call_count == 1
        assert mock_job_client_operations.create_import_export_job.call_args == mocker.call(
            fake_job_properties
        )


@pytest.mark.describe("IoTHubJobManager - .get_import_export_jobs()")
class TestGetImportExportJobs(object):
    @pytest.mark.it("Get export/import jobs")
    def test_get_export_import_jobs(self, mocker, mock_job_client_operations, iothub_job_manager):
        iothub_job_manager.get_import_export_jobs()
        assert mock_job_client_operations.get_import_export_jobs.call_count == 1
        assert mock_job_client_operations.get_import_export_jobs.call_args == mocker.call()


@pytest.mark.describe("IoTHubJobManager - .get_import_export_job()")
class TestGetImportExportJob(object):
    @pytest.mark.it("Get export/import job")
    def test_get_export_import_job(self, mocker, mock_job_client_operations, iothub_job_manager):
        iothub_job_manager.get_import_export_job(fake_job_id)
        assert mock_job_client_operations.get_import_export_job.call_count == 1
        assert mock_job_client_operations.get_import_export_job.call_args == mocker.call(
            fake_job_id
        )


@pytest.mark.describe("IoTHubJobManager - .cancel_import_export_job()")
class TestCancelImportExportJob(object):
    @pytest.mark.it("Cancel export/import job")
    def test_cancel_import_export_job(self, mocker, mock_job_client_operations, iothub_job_manager):
        iothub_job_manager.cancel_import_export_job(fake_job_id)
        assert mock_job_client_operations.cancel_import_export_job.call_count == 1
        assert mock_job_client_operations.cancel_import_export_job.call_args == mocker.call(
            fake_job_id
        )


@pytest.mark.describe("IoTHubJobManager - .create_job()")
class TestCreateJob(object):
    @pytest.mark.it("Create job")
    def test_create_job(self, mocker, mock_job_client_operations, iothub_job_manager):
        iothub_job_manager.create_job(fake_job_id, fake_job_request)
        assert mock_job_client_operations.create_job.call_count == 1
        assert mock_job_client_operations.create_job.call_args == mocker.call(
            fake_job_id, fake_job_request
        )


@pytest.mark.describe("IoTHubJobManager - .get_job()")
class TestGetJob(object):
    @pytest.mark.it("Get job")
    def test_get_job(self, mocker, mock_job_client_operations, iothub_job_manager):
        iothub_job_manager.get_job(fake_job_id)
        assert mock_job_client_operations.get_job.call_count == 1
        assert mock_job_client_operations.get_job.call_args == mocker.call(fake_job_id)


@pytest.mark.describe("IoTHubJobManager - .cancel_job()")
class TestCancelJob(object):
    @pytest.mark.it("Cancel job")
    def test_get_job(self, mocker, mock_job_client_operations, iothub_job_manager):
        iothub_job_manager.cancel_job(fake_job_id)
        assert mock_job_client_operations.cancel_job.call_count == 1
        assert mock_job_client_operations.cancel_job.call_args == mocker.call(fake_job_id)


@pytest.mark.describe("IoTHubJobManager - .query_jobs()")
class TestQueryJob(object):
    @pytest.mark.it("Query job")
    def test_get_job(self, mocker, mock_job_client_operations, iothub_job_manager):
        iothub_job_manager.query_jobs(fake_job_type, fake_job_status)
        assert mock_job_client_operations.query_jobs.call_count == 1
        assert mock_job_client_operations.query_jobs.call_args == mocker.call(
            fake_job_type, fake_job_status
        )
