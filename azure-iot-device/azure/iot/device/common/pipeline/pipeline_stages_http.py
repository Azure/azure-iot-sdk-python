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
    def _cancel_pending_connection_op(self):
        """
        Cancel any running connect, disconnect or reconnect op. Since our ability to "cancel" is fairly limited,
        all this does (for now) is to fail the operation
        """

        op = self._pending_connection_op
        if op:
            # NOTE: This code path should NOT execute in normal flow. There should never already be a pending
            # connection op when another is added, due to the SerializeConnectOps stage.
            # If this block does execute, there is a bug in the codebase.
            error = pipeline_exceptions.OperationCancelled(
                "Cancelling because new ConnectOperation, DisconnectOperation, or ReconnectOperation was issued"
            )  # TODO: should this actually somehow cancel the operation?
            self.complete_op(op, error=error)
            self._pending_connection_op = None

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

            self.complete_op(op)

        elif isinstance(op, pipeline_ops_base.UpdateSasTokenOperation):
            logger.debug("{}({}): saving sas token and completing".format(self.name, op.name))
            self.sas_token = op.sas_token
            self.complete_op(op)

        elif isinstance(op, pipeline_ops_http.HTTPRequestOperation):
            logger.info("{}({}): Handling HTTP Request Operation".format(self.name, op.name))
            path = op.path
            headers = op.headers

            # TODO: IMPLEMENT THIS!!!

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_request_complete():
                logger.debug("{}({}): PUBACK received. completing op.".format(self.name, op.name))
                op.complete()

            HTTPTransport.request(
                method="POST",
                hostname=op.hostname,
                path=path,
                headers=headers,
                body=op.body,
                callback=on_request_complete,
            )
            self.complete_op(op)

        else:
            self.send_op_down(op)
