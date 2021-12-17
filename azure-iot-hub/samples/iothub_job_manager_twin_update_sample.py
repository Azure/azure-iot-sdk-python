# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import datetime
import time
import uuid
from azure.iot.hub import IoTHubJobManager
from azure.iot.hub.models import JobRequest, Twin, TwinProperties


iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")


def create_twin_update_job_request():
    job = JobRequest()
    job.job_id = "twinjob" + str(uuid.uuid4())[:7]
    job.type = "scheduleUpdateTwin"
    job.start_time = datetime.datetime.utcnow().isoformat()
    job.update_twin = Twin(etag="*", properties=TwinProperties(desired={"temperature": 98.6}))
    job.query_condition = "*"
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
    print("    status: {}".format(job.status))
    if job.device_job_statistics:
        print("    statistics: {}".format(job.device_job_statistics.as_dict()))


try:
    # Create IoTHubJobManager
    iothub_job_manager = IoTHubJobManager.from_connection_string(iothub_connection_str)

    # Create  job
    job_request = create_twin_update_job_request()
    new_job_response = iothub_job_manager.create_scheduled_job(job_request.job_id, job_request)
    print_job_response("Create job response: ", new_job_response)

    # Get job
    while True:
        get_job_response = iothub_job_manager.get_scheduled_job(job_request.job_id)
        print_job_response("Get job response: ", get_job_response)
        if get_job_response.status == "completed":
            break
        time.sleep(5)

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iothub_registry_manager_sample stopped")
