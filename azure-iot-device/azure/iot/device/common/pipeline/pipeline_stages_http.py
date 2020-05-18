# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import six
import traceback
import copy
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
    This stage handles all HTTP operations that are not specific to IoT Hub.
    """

    def __init__(self):
        super(HTTPTransportStage, self).__init__()
        # The sas_token will be set when Connetion Args are received
        self.sas_token = None

        # The transport will be instantiated when Connection Args are received
        self.transport = None

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        if isinstance(op, pipeline_ops_base.InitializePipelineOperation):

            # If there is a gateway hostname, use that as the hostname for connection,
            # rather than the hostname itself
            if self.pipeline_root.pipeline_configuration.gateway_hostname:
                logger.debug(
                    "Gateway Hostname Present. Setting Hostname to: {}".format(
                        self.pipeline_root.pipeline_configuration.gateway_hostname
                    )
                )
                hostname = self.pipeline_root.pipeline_configuration.gateway_hostname
            else:
                logger.debug(
                    "Gateway Hostname not present. Setting Hostname to: {}".format(
                        self.pipeline_root.pipeline_configuration.hostname
                    )
                )
                hostname = self.pipeline_root.pipeline_configuration.hostname

            # Create HTTP Transport
            logger.debug("{}({}): got connection args".format(self.name, op.name))
            self.transport = HTTPTransport(
                hostname=hostname,
                server_verification_cert=self.pipeline_root.pipeline_configuration.server_verification_cert,
                x509_cert=self.pipeline_root.pipeline_configuration.x509,
                cipher=self.pipeline_root.pipeline_configuration.cipher,
            )

            self.pipeline_root.transport = self.transport
            op.complete()

        elif isinstance(op, pipeline_ops_http.HTTPRequestAndResponseOperation):
            # This will call down to the HTTP Transport with a request and also created a request callback. Because the HTTP Transport will run on the http transport thread, this call should be non-blocking to the pipline thread.
            logger.debug(
                "{}({}): Generating HTTP request and setting callback before completing.".format(
                    self.name, op.name
                )
            )

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_request_completed(error=None, response=None):
                if error:
                    logger.error(
                        "{}({}): Error passed to on_request_completed. Error={}".format(
                            self.name, op.name, error
                        )
                    )
                    op.complete(error=error)
                else:
                    logger.debug(
                        "{}({}): Request completed. Completing op.".format(self.name, op.name)
                    )
                    logger.debug("HTTP Response Status: {}".format(response["status_code"]))
                    logger.debug("HTTP Response: {}".format(response["resp"].decode("utf-8")))
                    op.response_body = response["resp"]
                    op.status_code = response["status_code"]
                    op.reason = response["reason"]
                    op.complete()

            # A deepcopy is necessary here since otherwise the manipulation happening to http_headers will affect the op.headers, which would be an unintended side effect and not a good practice.
            # TODO: We could probably do this somewhere else than here now that sastoken is a static value
            http_headers = copy.deepcopy(op.headers)
            if self.pipeline_root.pipeline_configuration.sastoken:
                http_headers["Authorization"] = str(
                    self.pipeline_root.pipeline_configuration.sastoken
                )

            self.transport.request(
                method=op.method,
                path=op.path,
                headers=http_headers,
                query_params=op.query_params,
                body=op.body,
                callback=on_request_completed,
            )

        else:
            self.send_op_down(op)
