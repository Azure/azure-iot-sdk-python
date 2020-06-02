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
from . import pipeline_ops_iothub, pipeline_ops_iothub_http, http_path_iothub, http_map_error
from azure.iot.device import exceptions
from azure.iot.device import constant as pkg_constant
from azure.iot.device import user_agent


logger = logging.getLogger(__name__)


@pipeline_thread.runs_on_pipeline_thread
def map_http_error(error, http_op):
    if error:
        return error
    elif http_op.status_code >= 300:
        translated_error = http_map_error.translate_error(http_op.status_code, http_op.reason)
        return exceptions.ServiceError(
            "HTTP operation returned: {} {}".format(http_op.status_code, translated_error)
        )


class IoTHubHTTPTranslationStage(PipelineStage):
    """
    PipelineStage which converts other Iot and EdgeHub operations into HTTP operations.  This stage also
    converts http pipeline events into Iot and EdgeHub pipeline events.
    """

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        if isinstance(op, pipeline_ops_iothub_http.MethodInvokeOperation):
            logger.debug(
                "{}({}): Translating Method Invoke Operation for HTTP.".format(self.name, op.name)
            )
            query_params = "api-version={apiVersion}".format(
                apiVersion=pkg_constant.IOTHUB_API_VERSION
            )
            #  if the target is a module.

            body = json.dumps(op.method_params)
            path = http_path_iothub.get_method_invoke_path(op.target_device_id, op.target_module_id)
            # NOTE: we do not add the sas Authorization header here. Instead we add it later on in
            # the HTTPTransportStage
            x_ms_edge_string = "{deviceId}/{moduleId}".format(
                deviceId=self.pipeline_root.pipeline_configuration.device_id,
                moduleId=self.pipeline_root.pipeline_configuration.module_id,
            )  # these are the identifiers of the current module
            user_agent_string = urllib.parse.quote_plus(
                user_agent.get_iothub_user_agent()
                + str(self.pipeline_root.pipeline_configuration.product_info)
            )
            # Method Invoke must be addressed to the gateway hostname because it is an Edge op
            headers = {
                "Host": self.pipeline_root.pipeline_configuration.gateway_hostname,
                "Content-Type": "application/json",
                "Content-Length": len(str(body)),
                "x-ms-edge-moduleId": x_ms_edge_string,
                "User-Agent": user_agent_string,
            }
            op_waiting_for_response = op

            def on_request_response(op, error):
                logger.debug(
                    "{}({}): Got response for MethodInvokeOperation".format(self.name, op.name)
                )
                error = map_http_error(error=error, http_op=op)
                if not error:
                    op_waiting_for_response.method_response = json.loads(
                        op.response_body.decode("utf-8")
                    )
                op_waiting_for_response.complete(error=error)

            self.send_op_down(
                pipeline_ops_http.HTTPRequestAndResponseOperation(
                    method="POST",
                    path=path,
                    headers=headers,
                    body=body,
                    query_params=query_params,
                    callback=on_request_response,
                )
            )

        elif isinstance(op, pipeline_ops_iothub_http.GetStorageInfoOperation):
            logger.debug(
                "{}({}): Translating Get Storage Info Operation to HTTP.".format(self.name, op.name)
            )
            query_params = "api-version={apiVersion}".format(
                apiVersion=pkg_constant.IOTHUB_API_VERSION
            )
            path = http_path_iothub.get_storage_info_for_blob_path(
                self.pipeline_root.pipeline_configuration.device_id
            )
            body = json.dumps({"blobName": op.blob_name})
            user_agent_string = urllib.parse.quote_plus(
                user_agent.get_iothub_user_agent()
                + str(self.pipeline_root.pipeline_configuration.product_info)
            )
            headers = {
                "Host": self.pipeline_root.pipeline_configuration.hostname,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Content-Length": len(str(body)),
                "User-Agent": user_agent_string,
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
                    method="POST",
                    path=path,
                    headers=headers,
                    body=body,
                    query_params=query_params,
                    callback=on_request_response,
                )
            )

        elif isinstance(op, pipeline_ops_iothub_http.NotifyBlobUploadStatusOperation):
            logger.debug(
                "{}({}): Translating Get Storage Info Operation to HTTP.".format(self.name, op.name)
            )
            query_params = "api-version={apiVersion}".format(
                apiVersion=pkg_constant.IOTHUB_API_VERSION
            )
            path = http_path_iothub.get_notify_blob_upload_status_path(
                self.pipeline_root.pipeline_configuration.device_id
            )
            body = json.dumps(
                {
                    "correlationId": op.correlation_id,
                    "isSuccess": op.is_success,
                    "statusCode": op.request_status_code,
                    "statusDescription": op.status_description,
                }
            )
            user_agent_string = urllib.parse.quote_plus(
                user_agent.get_iothub_user_agent()
                + str(self.pipeline_root.pipeline_configuration.product_info)
            )

            # NOTE we do not add the sas Authorization header here. Instead we add it later on in
            # the HTTPTransportStage
            headers = {
                "Host": self.pipeline_root.pipeline_configuration.hostname,
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": len(str(body)),
                "User-Agent": user_agent_string,
            }
            op_waiting_for_response = op

            def on_request_response(op, error):
                logger.debug(
                    "{}({}): Got response for GetStorageInfoOperation".format(self.name, op.name)
                )
                error = map_http_error(error=error, http_op=op)
                op_waiting_for_response.complete(error=error)

            self.send_op_down(
                pipeline_ops_http.HTTPRequestAndResponseOperation(
                    method="POST",
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
