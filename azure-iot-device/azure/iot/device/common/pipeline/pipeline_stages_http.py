# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import six
import traceback
from . import (
    pipeline_ops_base,
    PipelineStage,
    pipeline_ops_http,
    pipeline_thread,
    pipeline_exceptions,
)
from azure.iot.device.common.http_transport import HTTPTransport
from azure.iot.device.common import handle_exceptions, transport_exceptions
from azure.iot.device.common.callable_weak_method import CallableWeakMethod

logger = logging.getLogger(__name__)


class HTTPTransportStage(PipelineStage):
    """
    PipelineStage object which is responsible for interfacing with the HTTP protocol wrapper object.
    This stage handles all HTTP operations and any other operations (such as ConnectOperation) which
    is not in the HTTP group of operations, but can only be run at the protocol level.
    """

    @pipeline_thread.runs_on_pipeline_thread
    def _execute_op(self, op):
        if isinstance(op, pipeline_ops_http.SetHTTPConnectionArgsOperation):
            # pipeline_ops_http.SetMQTTConnectionArgsOperation is where we create our HTTPTransport object and set
            # all of its properties.
            logger.debug("{}({}): got connection args".format(self.name, op.name))
            self.hostname = op.hostname
            self.ca_cert = op.ca_cert
            self.sas_token = op.sas_token
            self.client_cert = op.client_cert
            self.transport = HTTPTransport(
                hostname=self.hostname, ca_cert=self.ca_cert, x509_cert=self.client_cert
            )

            self.pipeline_root.transport = self.transport
            op.complete()

        elif isinstance(op, pipeline_ops_base.UpdateSasTokenOperation):
            logger.debug("{}({}): saving sas token and completing".format(self.name, op.name))
            self.sas_token = op.sas_token
            op.complete()

        elif isinstance(op, pipeline_ops_http.HTTPRequestAndResponseOperation):

            http_headers = op.headers
            if self.sas_token:
                http_headers["Authorization"] = self.sas_token

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_request_completed(status_code, response):
                logger.debug("{}({}): Request completed. Completing op.".format(self.name, op.name))

                logger.debug("HTTP Response Status: {}".format(status_code))
                logger.debug(response)

                op.status_code = status_code
                op.response_body = response
                op.complete()  # TODO: Do we need to put an error in here?

            self.transport.request(
                method="POST",
                hostname=op.hostname,
                path=op.path,
                headers=http_headers,
                query_params=op.query_params,
                body=op.body,
                callback=on_request_completed,
            )

        else:
            self.send_op_down(op)
