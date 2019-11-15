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
from . import pipeline_ops_edgehub, pipeline_events_edgehub, http_path_edgehub
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

        if isinstance(op, pipeline_ops_edgehub.SetEdgeHubConnectionArgsOperation):
            self.device_id = op.device_id
            self.module_id = op.module_id

            self._set_topic_names(device_id=op.device_id, module_id=op.module_id)

            if op.module_id:
                client_id = "{}/{}".format(op.device_id, op.module_id)
            else:
                client_id = op.device_id
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

        elif (
            isinstance(op, pipeline_ops_edgehub.MethodInvokeOperation)
            # and self.pipeline_root.connected # TODO: See if this is necessary or not.
        ):
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

        elif isinstance(op, pipeline_ops_edgehub.SendD2CMessageOperation) or isinstance(
            op, pipeline_ops_edgehub.SendOutputEventOperation
        ):
            # Convert Get Storage Info operation into HTTP Publish operations
            path = http_path_edgehub.encode_properties(op.message, self.telemetry_topic)
            self.send_worker_op_down(
                worker_op=pipeline_ops_http.HTTPPublishOperation(
                    path=path, payload=op.message.data, callback=op.callback
                ),
                op=op,
            )

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


# FOR NOW, I DON'T THINK THIS IS NECESSARY
# @pipeline_thread.runs_on_pipeline_thread
# def _handle_pipeline_event(self, event):
#     """
#     Pipeline Event handler function to convert incoming HTTP messages into the appropriate EdgeHub
#     events, based on the topic of the message
#     """
#     if isinstance(event, pipeline_events_http.IncomingHTTPMessageEvent):
#         topic = event.topic

#         if http_path_edgehub.is_c2d_topic(topic, self.device_id):
#             message = Message(event.payload)
#             http_path_edgehub.extract_properties_from_topic(topic, message)
#             self.send_event_up(pipeline_events_edgehub.C2DMessageEvent(message))

#         elif http_path_edgehub.is_input_topic(topic, self.device_id, self.module_id):
#             message = Message(event.payload)
#             http_path_edgehub.extract_properties_from_topic(topic, message)
#             input_name = http_path_edgehub.get_input_name_from_topic(topic)
#             self.send_event_up(pipeline_events_edgehub.InputMessageEvent(input_name, message))

#         elif http_path_edgehub.is_method_topic(topic):
#             request_id = http_path_edgehub.get_method_request_id_from_topic(topic)
#             method_name = http_path_edgehub.get_method_name_from_topic(topic)
#             method_received = MethodRequest(
#                 request_id=request_id,
#                 name=method_name,
#                 payload=json.loads(event.payload.decode("utf-8")),
#             )
#             self.send_event_up(pipeline_events_edgehub.MethodRequestEvent(method_received))

#         elif http_path_edgehub.is_twin_response_topic(topic):
#             request_id = http_path_edgehub.get_twin_request_id_from_topic(topic)
#             status_code = int(http_path_edgehub.get_twin_status_code_from_topic(topic))
#             self.send_event_up(
#                 pipeline_events_base.ResponseEvent(
#                     request_id=request_id, status_code=status_code, response_body=event.payload
#                 )
#             )

#         elif http_path_edgehub.is_twin_desired_property_patch_topic(topic):
#             self.send_event_up(
#                 pipeline_events_edgehub.TwinDesiredPropertiesPatchEvent(
#                     patch=json.loads(event.payload.decode("utf-8"))
#                 )
#             )

#         else:
#             logger.debug("Uunknown topic: {} passing up to next handler".format(topic))
#             self.send_event_up(event)

#     else:
#         # all other messages get passed up
#         self.send_event_up(event)
