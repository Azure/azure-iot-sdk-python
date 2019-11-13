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
from azure.iot.device.iothub.models import Message, MethodRequest
from . import pipeline_ops_iothub, pipeline_events_iothub, http_path_iothub
from . import constant as pipeline_constant
from . import exceptions as pipeline_exceptions
from azure.iot.device import constant as pkg_constant

logger = logging.getLogger(__name__)


class IoTHubHTTPTranslationStage(PipelineStage):
    """
    PipelineStage which converts other Iot and IoTHub operations into HTTP operations.  This stage also
    converts http pipeline events into Iot and IoTHub pipeline events.
    """

    def __init__(self):
        super(IoTHubHTTPTranslationStage, self).__init__()
        self.feature_to_topic = {}

    @pipeline_thread.runs_on_pipeline_thread
    def _execute_op(self, op):

        if isinstance(op, pipeline_ops_iothub.SetIoTHubConnectionArgsOperation):
            self.device_id = op.device_id
            self.module_id = op.module_id

            # if we get auth provider args from above, we save some, use some to build topic names,
            # and always pass it down because we know that the HTTP protocol stage will also want
            # to receive these args.
            self._set_topic_names(device_id=op.device_id, module_id=op.module_id)

            if op.module_id:
                client_id = "{}/{}".format(op.device_id, op.module_id)
            else:
                client_id = op.device_id

            # For HTTP, the entire user agent string should be appended to the username field in the connect packet
            # For example, the username may look like this without custom parameters:
            # yosephsandboxhub.azure-devices.net/alpha/?api-version=2018-06-30&DeviceClientType=py-azure-iot-device%2F2.0.0-preview.12
            # The customer user agent string would simply be appended to the end of this username, in URL Encoded format.
            # query_param_seq = [
            #     ("api-version", pkg_constant.IOTHUB_API_VERSION),
            #     ("DeviceClientType", pkg_constant.USER_AGENT),
            # ]
            # username = "{hostname}/{client_id}/?{query_params}{optional_product_info}".format(
            #     hostname=op.hostname,
            #     client_id=client_id,
            #     query_params=urllib.parse.urlencode(query_param_seq),
            #     optional_product_info=urllib.parse.quote(
            #         str(self.pipeline_root.pipeline_configuration.product_info)
            #     ),
            # )

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
            isinstance(op, pipeline_ops_base.UpdateSasTokenOperation)
            and self.pipeline_root.connected
        ):
            logger.debug(
                "{}({}): Connected.  Passing op down and reconnecting after token is updated.".format(
                    self.name, op.name
                )
            )
            self.send_op_down(op)

        elif isinstance(op, pipeline_ops_iothub.SendD2CMessageOperation) or isinstance(
            op, pipeline_ops_iothub.SendOutputEventOperation
        ):
            # Convert Get Storage Info operation into HTTP Publish operations
            path = http_path_iothub.encode_properties(op.message, self.telemetry_topic)
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
        self.telemetry_topic = http_path_iothub.get_telemetry_topic_for_publish(
            device_id, module_id
        )
        self.feature_to_topic = {
            pipeline_constant.C2D_MSG: (
                http_path_iothub.get_c2d_topic_for_subscribe(device_id, module_id)
            ),
            pipeline_constant.INPUT_MSG: (
                http_path_iothub.get_input_topic_for_subscribe(device_id, module_id)
            ),
            pipeline_constant.METHODS: (http_path_iothub.get_method_topic_for_subscribe()),
            pipeline_constant.TWIN: (http_path_iothub.get_twin_response_topic_for_subscribe()),
            pipeline_constant.TWIN_PATCHES: (http_path_iothub.get_twin_patch_topic_for_subscribe()),
        }

    @pipeline_thread.runs_on_pipeline_thread
    def _handle_pipeline_event(self, event):
        """
        Pipeline Event handler function to convert incoming HTTP messages into the appropriate IoTHub
        events, based on the topic of the message
        """
        if isinstance(event, pipeline_events_http.IncomingHTTPMessageEvent):
            topic = event.topic

            if http_path_iothub.is_c2d_topic(topic, self.device_id):
                message = Message(event.payload)
                http_path_iothub.extract_properties_from_topic(topic, message)
                self.send_event_up(pipeline_events_iothub.C2DMessageEvent(message))

            elif http_path_iothub.is_input_topic(topic, self.device_id, self.module_id):
                message = Message(event.payload)
                http_path_iothub.extract_properties_from_topic(topic, message)
                input_name = http_path_iothub.get_input_name_from_topic(topic)
                self.send_event_up(pipeline_events_iothub.InputMessageEvent(input_name, message))

            elif http_path_iothub.is_method_topic(topic):
                request_id = http_path_iothub.get_method_request_id_from_topic(topic)
                method_name = http_path_iothub.get_method_name_from_topic(topic)
                method_received = MethodRequest(
                    request_id=request_id,
                    name=method_name,
                    payload=json.loads(event.payload.decode("utf-8")),
                )
                self.send_event_up(pipeline_events_iothub.MethodRequestEvent(method_received))

            elif http_path_iothub.is_twin_response_topic(topic):
                request_id = http_path_iothub.get_twin_request_id_from_topic(topic)
                status_code = int(http_path_iothub.get_twin_status_code_from_topic(topic))
                self.send_event_up(
                    pipeline_events_base.ResponseEvent(
                        request_id=request_id, status_code=status_code, response_body=event.payload
                    )
                )

            elif http_path_iothub.is_twin_desired_property_patch_topic(topic):
                self.send_event_up(
                    pipeline_events_iothub.TwinDesiredPropertiesPatchEvent(
                        patch=json.loads(event.payload.decode("utf-8"))
                    )
                )

            else:
                logger.debug("Uunknown topic: {} passing up to next handler".format(topic))
                self.send_event_up(event)

        else:
            # all other messages get passed up
            self.send_event_up(event)
