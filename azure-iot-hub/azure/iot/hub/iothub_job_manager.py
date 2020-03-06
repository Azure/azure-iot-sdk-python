# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from .auth import ConnectionStringAuthentication
from .protocol.iot_hub_gateway_service_ap_is import IotHubGatewayServiceAPIs as protocol_client
from .protocol.models import Configuration, ConfigurationContent, ConfigurationQueriesTestInput


class IoTHubJobManager(object):
    """A class to provide convenience APIs for IoTHub Job Manager operations,
    based on top of the auto generated IotHub REST APIs
    """

    def __init__(self, connection_string):
        """Initializer for a Job Manager Service client.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param str connection_string: The IoTHub connection string used to authenticate connection
            with IoTHub.

        :returns: Instance of the IoTHubJobManager object.
        :rtype: :class:`azure.iot.hub.IoTHubJobManager`
        """

        self.auth = ConnectionStringAuthentication(connection_string)
        self.protocol = protocol_client(self.auth, "https://" + self.auth["HostName"])

    def create_import_export_job(self, job_properties):
        """Creates a new import/export job on an IoT hub.

        :param job_properties job_properties: Specifies the job specification.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: JobProperties object containing the created job.
        """
        return self.protocol.job_client.create_import_export_job(job_properties)

    def get_import_export_jobs(self):
        """Retrieves the status of all import/export jobs on an IoTHub.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The list[JobProperties] object.
        """
        return self.protocol.job_client.get_import_export_jobs()

    def get_import_export_job(self, job_id):
        """Retrieves the status of an import/export job on an IoTHub.

        :param str job_id: The ID of the job.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The JobProperties object containing the requested job.
        """
        return self.protocol.job_client.get_import_export_job(job_id)

    def cancel_import_export_job(self, job_id):
        """Cancels an import/export job on an IoT hub.

        :param str job_id: The ID of the job.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: Object.
        """
        return self.protocol.job_client.cancel_import_export_job(job_id)

    def create_job(self, job_id, job_request):
        """Creates a new job to schedule update twins or device direct methods on an IoT hub.

        :param str job_id: The ID of the job.
        :param job_request job_request: Specifies the job.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: JobResponse object containing the created job.
        """
        return self.protocol.job_client.create_job(job_id, job_request)

    def get_job(self, job_id):
        """Retrieves the details of a scheduled job on an IoTHub.

        :param str job_id: The ID of the job.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The JobResponse object containing the requested details.
        """
        return self.protocol.job_client.get_job(job_id)

    def cancel_job(self, job_id):
        """Cancels a scheduled job on an IoT hub.

        :param str job_id: The ID of the job.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: JobResponse object containing the cancelled job.
        """
        return self.protocol.job_client.cancel_job(job_id)

    def query_jobs(self, job_type, job_status):
        """Query an IoT hub to retrieve information regarding jobs using the IoT Hub query language.

        :param str job_type: The type of the jobs.
        :param str job_status: The status of the jobs.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: QueryResult object containing the jobs.
        """
        return self.protocol.job_client.query_jobs(job_type, job_status)
