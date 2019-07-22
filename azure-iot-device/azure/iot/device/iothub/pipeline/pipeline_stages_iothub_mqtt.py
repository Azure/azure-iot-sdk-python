# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import json
from azure.iot.device.common.pipeline import (
    pipeline_events_base,
    pipeline_ops_base,
    pipeline_ops_mqtt,
    pipeline_events_mqtt,
    PipelineStage,
    operation_flow,
    pipeline_thread,
)
from azure.iot.device.iothub.models import Message, MethodRequest
from . import constant, pipeline_ops_iothub, pipeline_events_iothub, mqtt_topic_iothub

logger = logging.getLogger(__name__)


class IoTHubMQTTConverterStage(PipelineStage):
    """
    PipelineStage which converts other Iot and IoTHub operations into MQTT operations.  This stage also
    converts mqtt pipeline events into Iot and IoTHub pipeline events.
    """

    def __init__(self):
        super(IoTHubMQTTConverterStage, self).__init__()
        self.feature_to_topic = {}

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):

        if isinstance(op, pipeline_ops_iothub.SetAuthProviderArgsOperation):
            self.device_id = op.device_id
            self.module_id = op.module_id

            # if we get auth provider args from above, we save some, use some to build topic names,
            # and always pass it down because we know that the MQTT protocol stage will also want
            # to receive these args.
            self._set_topic_names(device_id=op.device_id, module_id=op.module_id)

            if op.module_id:
                client_id = "{}/{}".format(op.device_id, op.module_id)
            else:
                client_id = op.device_id

            username = "{hostname}/{client_id}/?api-version=2018-06-30".format(
                hostname=op.hostname, client_id=client_id
            )

            if op.gateway_hostname:
                hostname = op.gateway_hostname
            else:
                hostname = op.hostname

            operation_flow.delegate_to_different_op(
                stage=self,
                original_op=op,
                new_op=pipeline_ops_mqtt.SetMQTTConnectionArgsOperation(
                    client_id=client_id, hostname=hostname, username=username, ca_cert=op.ca_cert
                ),
            )

        elif isinstance(op, pipeline_ops_iothub.SendD2CMessageOperation) or isinstance(
            op, pipeline_ops_iothub.SendOutputEventOperation
        ):
            # Convert SendTelementry and SendOutputEventOperation operations into MQTT Publish operations
            topic = mqtt_topic_iothub.encode_properties(op.message, self.telemetry_topic)
            operation_flow.delegate_to_different_op(
                stage=self,
                original_op=op,
                new_op=pipeline_ops_mqtt.MQTTPublishOperation(topic=topic, payload=op.message.data),
            )

        elif isinstance(op, pipeline_ops_iothub.SendMethodResponseOperation):
            # Sending a Method Response gets translated into an MQTT Publish operation
            topic = mqtt_topic_iothub.get_method_topic_for_publish(
                op.method_response.request_id, str(op.method_response.status)
            )
            payload = json.dumps(op.method_response.payload)
            operation_flow.delegate_to_different_op(
                stage=self,
                original_op=op,
                new_op=pipeline_ops_mqtt.MQTTPublishOperation(topic=topic, payload=payload),
            )

        elif isinstance(op, pipeline_ops_base.EnableFeatureOperation):
            # Enabling a feature gets translated into an MQTT subscribe operation
            topic = self.feature_to_topic[op.feature_name]
            operation_flow.delegate_to_different_op(
                stage=self,
                original_op=op,
                new_op=pipeline_ops_mqtt.MQTTSubscribeOperation(topic=topic),
            )

        elif isinstance(op, pipeline_ops_base.DisableFeatureOperation):
            # Disabling a feature gets turned into an MQTT unsubscribe operation
            topic = self.feature_to_topic[op.feature_name]
            operation_flow.delegate_to_different_op(
                stage=self,
                original_op=op,
                new_op=pipeline_ops_mqtt.MQTTUnsubscribeOperation(topic=topic),
            )

        elif isinstance(op, pipeline_ops_base.SendIotRequestOperation):
            if op.request_type == constant.TWIN:
                topic = mqtt_topic_iothub.get_twin_topic_for_publish(
                    method=op.method,
                    resource_location=op.resource_location,
                    request_id=op.request_id,
                )
                operation_flow.delegate_to_different_op(
                    stage=self,
                    original_op=op,
                    new_op=pipeline_ops_mqtt.MQTTPublishOperation(
                        topic=topic, payload=op.request_body
                    ),
                )
            else:
                raise NotImplementedError(
                    "SendIotRequestOperation request_type {} not supported".format(op.request_type)
                )

        else:
            # All other operations get passed down
            operation_flow.pass_op_to_next_stage(self, op)

    @pipeline_thread.runs_on_pipeline_thread
    def _set_topic_names(self, device_id, module_id):
        """
        Build topic names based on the device_id and module_id passed.
        """
        self.telemetry_topic = mqtt_topic_iothub.get_telemetry_topic_for_publish(
            device_id, module_id
        )
        self.feature_to_topic = {
            constant.C2D_MSG: (mqtt_topic_iothub.get_c2d_topic_for_subscribe(device_id, module_id)),
            constant.INPUT_MSG: (
                mqtt_topic_iothub.get_input_topic_for_subscribe(device_id, module_id)
            ),
            constant.METHODS: (mqtt_topic_iothub.get_method_topic_for_subscribe()),
            constant.TWIN: (mqtt_topic_iothub.get_twin_response_topic_for_subscribe()),
            constant.TWIN_PATCHES: (mqtt_topic_iothub.get_twin_patch_topic_for_subscribe()),
        }

    @pipeline_thread.runs_on_pipeline_thread
    def _handle_pipeline_event(self, event):
        """
        Pipeline Event handler function to convert incoming MQTT messages into the appropriate IoTHub
        events, based on the topic of the message
        """
        if isinstance(event, pipeline_events_mqtt.IncomingMQTTMessageEvent):
            topic = event.topic

            if mqtt_topic_iothub.is_c2d_topic(topic, self.device_id):
                message = Message(event.payload)
                mqtt_topic_iothub.extract_properties_from_topic(topic, message)
                operation_flow.pass_event_to_previous_stage(
                    self, pipeline_events_iothub.C2DMessageEvent(message)
                )

            elif mqtt_topic_iothub.is_input_topic(topic, self.device_id, self.module_id):
                message = Message(event.payload)
                mqtt_topic_iothub.extract_properties_from_topic(topic, message)
                input_name = mqtt_topic_iothub.get_input_name_from_topic(topic)
                operation_flow.pass_event_to_previous_stage(
                    self, pipeline_events_iothub.InputMessageEvent(input_name, message)
                )

            elif mqtt_topic_iothub.is_method_topic(topic):
                request_id = mqtt_topic_iothub.get_method_request_id_from_topic(topic)
                method_name = mqtt_topic_iothub.get_method_name_from_topic(topic)
                method_received = MethodRequest(
                    request_id=request_id,
                    name=method_name,
                    payload=json.loads(event.payload.decode("utf-8")),
                )
                operation_flow.pass_event_to_previous_stage(
                    self, pipeline_events_iothub.MethodRequestEvent(method_received)
                )

            elif mqtt_topic_iothub.is_twin_response_topic(topic):
                request_id = mqtt_topic_iothub.get_twin_request_id_from_topic(topic)
                status_code = int(mqtt_topic_iothub.get_twin_status_code_from_topic(topic))
                operation_flow.pass_event_to_previous_stage(
                    self,
                    pipeline_events_base.IotResponseEvent(
                        request_id=request_id, status_code=status_code, response_body=event.payload
                    ),
                )

            elif mqtt_topic_iothub.is_twin_desired_property_patch_topic(topic):
                operation_flow.pass_event_to_previous_stage(
                    self,
                    pipeline_events_iothub.TwinDesiredPropertiesPatchEvent(
                        patch=json.loads(event.payload.decode("utf-8"))
                    ),
                )

            else:
                logger.info("Uunknown topic: {} passing up to next handler".format(topic))
                operation_flow.pass_event_to_previous_stage(self, event)

        else:
            # all other messages get passed up
            operation_flow.pass_event_to_previous_stage(self, event)
