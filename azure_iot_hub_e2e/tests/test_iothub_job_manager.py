# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import pytest
import logging
import uuid
from azure.iot.hub.iothub_job_manager import IoTHubJobManager
from azure.iot.hub.models import JobProperties, JobRequest

logging.basicConfig(level=logging.DEBUG)

iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
output_container_uri = os.getenv("JOB_EXPORT_IMPORT_OUTPUT_URI")


@pytest.mark.describe("Create and test IoTHubJobManager")
class TestJobManager(object):
    @pytest.mark.it("Create IoTHubJobManager client and create, get and cancel export/import job")
    def test_iot_hub_job_manager_export_import_jobs(self):
        try:
            iothub_job_manager = IoTHubJobManager(iothub_connection_str)

            # Create export/import job
            authentication_type = "keyBased"
            properties_type = "export"
            job_properties = JobProperties()
            job_properties.authentication_type = authentication_type
            job_properties.type = properties_type
            job_properties.output_blob_container_uri = output_container_uri

            new_export_import_job = iothub_job_manager.create_import_export_job(job_properties)

            # Verify result
            assert new_export_import_job.authentication_type == authentication_type
            assert new_export_import_job.type == properties_type
            assert new_export_import_job.output_blob_container_uri == output_container_uri

            # Get export/import job
            get_export_import_job = iothub_job_manager.get_import_export_job(
                new_export_import_job.job_id
            )

            # Verify result
            assert get_export_import_job.job_id == new_export_import_job.job_id
            assert (
                get_export_import_job.authentication_type
                == new_export_import_job.authentication_type
            )
            assert get_export_import_job.type == new_export_import_job.type
            assert (
                get_export_import_job.output_blob_container_uri
                == new_export_import_job.output_blob_container_uri
            )

            # Get all export/import jobs
            export_import_jobs = iothub_job_manager.get_import_export_jobs()

            assert new_export_import_job in export_import_jobs

            # Cancel export_import job
            iothub_job_manager.cancel_import_export_job(new_export_import_job.job_id)

            # Get all export/import jobs
            export_import_jobs = iothub_job_manager.get_import_export_jobs()

            assert new_export_import_job not in export_import_jobs

        except Exception as e:
            logging.exception(e)

    @pytest.mark.it("Create IoTHubJobManager client and create, get and cancel job")
    def test_iot_hub_job_manager_jobs(self):
        try:
            iothub_job_manager = IoTHubJobManager(iothub_connection_str)

            # Create job request
            job_id = "sample_cloud_to_device_method"
            job_type = "cloudToDeviceMethod"
            job_execution_time_max = 60
            job_request = JobRequest()
            job_request.job_id = job_id
            job_request.type = job_type
            job_request.start_time = ""
            job_request.max_execution_time_in_seconds = job_execution_time_max
            job_request.update_twin = ""
            job_request.query_condition = ""

            new_job_response = iothub_job_manager.create_job(job_request.job_id, job_request)

            # Verify result
            assert new_job_response.job_id == job_type
            assert new_job_response.type == job_type
            assert new_job_response.max_execution_time_in_seconds == job_execution_time_max

            # Get job
            get_job = iothub_job_manager.get_job(new_job_response.job_id)

            # Verify result
            assert get_job.job_id == job_id
            assert get_job.type == job_type
            assert get_job.max_execution_time_in_seconds == job_execution_time_max

            # Cancel job
            iothub_job_manager.cancel_job(get_job.job_id)

        except Exception as e:
            logging.exception(e)
