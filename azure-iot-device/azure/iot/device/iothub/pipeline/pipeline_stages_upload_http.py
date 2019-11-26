# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import json
import six.moves.urllib as urllib
from azure.iot.device.common.pipeline import (
    pipeline_events_base,
    pipeline_ops_base,
    pipeline_ops_http,
    PipelineStage,
    pipeline_thread,
)
from . import pipeline_ops_iothub, pipeline_ops_upload, http_path_edgehub
from . import constant as pipeline_constant
from . import exceptions as pipeline_exceptions
from azure.iot.device import constant as pkg_constant

logger = logging.getLogger(__name__)


class UploadHTTPTranslationStage(PipelineStage):
    """
    PipelineStage which converts other Iot and EdgeHub operations into HTTP operations.  This stage also
    converts http pipeline events into Iot and EdgeHub pipeline events.
    """

    def __init__(self):
        super(UploadHTTPTranslationStage, self).__init__()
        self.feature_to_topic = {}
        self.device_id = None
        self.module_id = None
        self.client_id = None
        self.hostname = None

    @pipeline_thread.runs_on_pipeline_thread
    def _execute_op(self, op):
        def map_http_error(error, http_op):
            if error:
                return error
            elif http_op.status_code >= 300:
                # TODO map error codes to correct exceptions
                logger.error("Error {} received from request operation".format(http_op.status_code))
                logger.error("response body: {}".format(http_op.response_body))
                return pipeline_exceptions.PipelineError(
                    "http operation returned status {}".format(http_op.status_code)
                )

        if isinstance(op, pipeline_ops_iothub.SetIoTHubConnectionArgsOperation):
            self.device_id = op.device_id
            self.module_id = op.module_id

            # self._set_topic_names(device_id=op.device_id, module_id=op.module_id)

            if op.module_id:
                self.client_id = "{}/{}".format(op.device_id, op.module_id)
            else:
                self.client_id = op.device_id
            # When you are connecting through Edge Hub to another Hub, Gateway Hostname is the gateway you are connecting to, hostname is the IoT Hub you are connecting to.
            # TODO: Read the node code to figure out how to format the HTTP url with the gateway hostname and the hostname
            if op.gateway_hostname:
                self.hostname = op.gateway_hostname
            else:
                self.hostname = op.hostname

            worker_op = op.spawn_worker_op(
                worker_op_type=pipeline_ops_http.SetHTTPConnectionArgsOperation,
                client_id=self.client_id,
                hostname=self.hostname,
                ca_cert=op.ca_cert,
                client_cert=op.client_cert,
                sas_token=op.sas_token,
            )

            self.send_op_down(worker_op)

        elif isinstance(op, pipeline_ops_upload.GetStorageInfoOperation):
            # TODO: translate the method params into the HTTP specific operations. It sets the path, the header values, picks the verb (METHOD INVOKE is a POST)
            logger.debug("{}({}): BLAH BLAH BLAH".format(self.name, op.name))
            query_params = "api-version={apiVersion}".format(
                apiVersion=pkg_constant.IOTHUB_API_VERSION
            )
            path = "/devices/{deviceId}/files".format(deviceId=self.device_id)
            body = {"blobName": op.blob_name}
            headers = {
                "Host": self.hostname,  # TODO: Does this need to be encoded?
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Content-Length": len(str(body)),
                "User-Agent": pkg_constant.USER_AGENT,  # TODO: Does this need to be encoded?
            }

            op_waiting_for_response = op

            def on_request_response(op, error):
                logger.debug(
                    "{}({}): Got response for GetStorageInfoOperation".format(self.name, op.name)
                )
                error = map_http_error(error=error, http_op=op)
                if not error:
                    op_waiting_for_response.storage_info = json.loads(
                        op.response_body.decode("utf-8")
                    )
                op_waiting_for_response.complete(error=error)

            self.send_op_down(
                pipeline_ops_http.HTTPRequestAndResponseOperation(
                    hostname=self.hostname,
                    path=path,
                    headers=headers,
                    body=body,
                    query_params=query_params,
                    callback=on_request_response,
                )
            )

        elif isinstance(op, pipeline_ops_upload.NotifyBlobUploadStatusOperation):
            # TODO: translate the method params into the HTTP specific operations. It sets the path, the header values, picks the verb (METHOD INVOKE is a POST)
            logger.debug("{}({}): BLAH BLAH BLAH.".format(self.name, op.name))
            query_params = "api-version={apiVersion}".format(
                apiVersion=pkg_constant.IOTHUB_API_VERSION
            )
            path = "/devices/{deviceId}/files/notifications".format(deviceId=self.device_id)
            body = {
                "correlationId": op.correlation_id,
                "isSuccess": op.upload_response,
                "statusCode": op.request_status_code,
                "statusDescription": op.status_description,
            }

            # Note we do not add the sas Authorization header here. Instead we add it later on in the stage above
            # the transport layer, since that stage stores the updated SAS and also X509 certs if that is what is
            # being used.
            headers = {
                "Host": self.hostname,  # TODO: Does this need to be encoded?
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": len(str(body)),
                "User-Agent": pkg_constant.USER_AGENT,  # TODO: Does this need to be encoded?
            }
            op_waiting_for_response = op

            def on_request_response(op, error):
                logger.debug(
                    "{}({}): Got response for GetStorageInfoOperation".format(self.name, op.name)
                )
                error = map_http_error(error=error, http_op=op)
                if not error:
                    op_waiting_for_response.response_status_code = op.status_code
                op_waiting_for_response.complete(error=error)

            self.send_op_down(
                pipeline_ops_http.HTTPRequestAndResponseOperation(
                    hostname=self.hostname,
                    path=path,
                    headers=headers,
                    body=body,
                    query_params=query_params,
                    callback=on_request_response,
                )
            )

        else:
            # All other operations get passed down
            self.send_op_down(op)
