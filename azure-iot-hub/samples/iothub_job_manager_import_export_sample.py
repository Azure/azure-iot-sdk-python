# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
import msrest
from azure.iot.hub import IoTHubJobManager
from azure.iot.hub.models import JobProperties, ManagedIdentity


iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
output_container_uri = os.getenv("JOB_EXPORT_IMPORT_OUTPUT_URI")


def create_export_import_job_properties():
    job_properties = JobProperties()
    job_properties.type = "export"
    job_properties.output_blob_container_uri = output_container_uri

    # To use a managed identity (either system assigned or user assigned), change storage_authentication_type from "keyBased" to "identityBased"
    job_properties.storage_authentication_type = "keyBased"

    # For user assigned managed identities, uncomment the two lines below and add the resource id of the managed identity. storage_authentication_type must be identityBased.
    # job_properties.identity = ManagedIdentity()
    # job_properties.identity.user_assigned_identity = "<resource id of user assigned identity>"

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
    print("    storage_authentication_type: {}".format(job.storage_authentication_type))
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


try:
    # Create IoTHubJobManager
    iothub_job_manager = IoTHubJobManager.from_connection_string(iothub_connection_str)

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

except msrest.exceptions.HttpOperationError as ex:
    print("HttpOperationError error {0}".format(ex.response.text))
except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("{} stopped".format(__file__))
finally:
    print("{} finished".format(__file__))
