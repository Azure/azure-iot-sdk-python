# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.hub import IoTHubJobManager
from azure.iot.hub.models import JobProperties, JobRequest


iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
output_container_uri = os.getenv("JOB_EXPORT_IMPORT_OUTPUT_URI")


def create_export_import_job_properties():
    job_properties = JobProperties()
    job_properties.authentication_type = "keyBased"
    job_properties.type = "export"
    job_properties.output_blob_container_uri = output_container_uri
    return job_properties


def print_export_import_job(title, job):
    print()
    print(title)
    print("    job_id: {}".format(job.job_id))
    print("    type: {}".format(job.type))
    print("    status: {}".format(job.status))
    print("    start_time_utc: {}".format(job.start_time_utc))
    print("    end_time_utc: {}".format(job.end_time_utc))
    print("    progress: {}".format(job.progress))
    print("    input_blob_container_uri: {}".format(job.input_blob_container_uri))
    print("    input_blob_name: {}".format(job.input_blob_name))
    print("    output_blob_container_uri: {}".format(job.output_blob_container_uri))
    print("    output_blob_name: {}".format(job.output_blob_name))
    print("    exclude_keys_in_export: {}".format(job.exclude_keys_in_export))
    print("    authentication_type: {}".format(job.authentication_type))
    print("    failure_reason: {}".format(job.failure_reason))


def print_export_import_jobs(title, export_import_jobs):
    print("")
    x = 1
    if len([export_import_jobs]) > 0:
        for j in range(len(export_import_jobs)):
            print_export_import_job("{0}: {1}".format(title, x), export_import_jobs[j])
            x += 1
    else:
        print("No item found")


def create_job_request():
    job = JobRequest()
    job.job_id = "sample_cloud_to_device_method"
    job.type = "cloudToDeviceMethod"
    job.start_time = ""
    job.max_execution_time_in_seconds = 60
    job.update_twin = ""
    job.query_condition = ""
    return job


def print_job_response(title, job):
    print()
    print(title)
    print("    job_id: {}".format(job.job_id))
    print("    type: {}".format(job.type))
    print("    start_time: {}".format(job.start_time))
    print("    max_execution_time_in_seconds: {}".format(job.max_execution_time_in_seconds))
    print("    update_twin: {}".format(job.update_twin))
    print("    query_condition: {}".format(job.query_condition))


try:
    # Create IoTHubJobManager
    iothub_job_manager = IoTHubJobManager(iothub_connection_str)

    # Get all export/import jobs
    export_import_jobs = iothub_job_manager.get_import_export_jobs()
    if export_import_jobs:
        print_export_import_jobs("Get all export/import jobs", export_import_jobs)
    else:
        print("No export/import job found")

    # Create export/import job
    new_export_import_job = iothub_job_manager.create_import_export_job(
        create_export_import_job_properties()
    )
    print_export_import_job("Create export/import job result: ", new_export_import_job)

    # Get export/import job
    get_export_import_job = iothub_job_manager.get_import_export_job(new_export_import_job.job_id)
    print_export_import_job("Get export/import job result: ", get_export_import_job)

    # Cancel export/import job
    cancel_export_import_job = iothub_job_manager.cancel_import_export_job(
        get_export_import_job.job_id
    )
    print(cancel_export_import_job)

    # Create  job
    job_request = create_job_request()
    new_job_response = iothub_job_manager.create_job(job_request.job_id, job_request)
    print_job_response("Create job response: ", new_job_response)

    # Get job
    get_job_response = iothub_job_manager.get_job(new_job_response.job_id)
    print_job_response("Get job response: ", get_job_response)

    # Cancel job
    cancel_job_response = iothub_job_manager.cancel_job(get_job_response.job_id)
    print_job_response("Cancel job response: ", cancel_job_response)

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iothub_registry_manager_sample stopped")
