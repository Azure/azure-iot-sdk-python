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
    pipeline_events_http,
    PipelineStage,
    pipeline_thread,
)
from azure.iot.device.edgehub.models import Message, MethodRequest
from . import pipeline_ops_iothub, pipeline_ops_edgehub, http_path_edgehub
from . import constant as pipeline_constant
from . import exceptions as pipeline_exceptions
from azure.iot.device import constant as pkg_constant

logger = logging.getLogger(__name__)


class EdgeHubHTTPTranslationStage(PipelineStage):
    """
    PipelineStage which converts other Iot and EdgeHub operations into HTTP operations.  This stage also
    converts http pipeline events into Iot and EdgeHub pipeline events.
    """

    def __init__(self):
        super(EdgeHubHTTPTranslationStage, self).__init__()
        self.feature_to_topic = {}

    @pipeline_thread.runs_on_pipeline_thread
    def _execute_op(self, op):

        if isinstance(op, pipeline_ops_iothub.SetIoTHubConnectionArgsOperation):
            self.device_id = op.device_id
            self.module_id = op.module_id

            self._set_topic_names(device_id=op.device_id, module_id=op.module_id)

            if op.module_id:
                client_id = "{}/{}".format(op.device_id, op.module_id)
            else:
                client_id = op.device_id
            # When you are connecting through Edge Hub to another Hub, Gateway Hostname is the gateway you are connecting to, hostname is the IoT Hub you are connecting to.
            # TODO: Read the node code to figure out how to format the HTTP url with the gateway hostname and the hostname
            if op.gateway_hostname:
                hostname = op.gateway_hostname
            else:
                hostname = op.hostname

            # TODO: test to make sure client_cert and sas_token travel down correctly
            self.send_worker_op_down(
                # self, hostname, callback, ca_cert=None, client_cert=None, sas_token=None
                worker_op=pipeline_ops_http.SetHTTPConnectionArgsOperation(
                    client_id=client_id,
                    hostname=hostname,
                    ca_cert=op.ca_cert,
                    client_cert=op.client_cert,
                    sas_token=op.sas_token,
                    callback=op.callback,
                ),
                op=op,
            )

        elif isinstance(op, pipeline_ops_edgehub.MethodInvokeOperation):
            # TODO: translate the method params into the HTTP specific operations. It sets the path, the header values, picks the verb (METHOD INVOKE is a POST)
            logger.debug(
                "{}({}): Connected.  Passing op down and reconnecting after token is updated.".format(
                    self.name, op.name
                )
            )
            path = "fakePath"
            headers = "fakeHeaders"
            self.send_worker_op_down(
                worker_op=pipeline_ops_http.HTTPRequestOperation(
                    path=path, headers=headers, callback=op.callback
                ),
                op=op,
            )
            self.send_op_down(op)

        else:
            # All other operations get passed down
            self.send_op_down(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _set_topic_names(self, device_id, module_id):
        """
        Build topic names based on the device_id and module_id passed.
        """
        self.telemetry_topic = http_path_edgehub.get_telemetry_topic_for_publish(
            device_id, module_id
        )
