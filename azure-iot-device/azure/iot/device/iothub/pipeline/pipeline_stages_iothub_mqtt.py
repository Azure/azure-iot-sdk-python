# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import json
from azure.iot.device.common.pipeline import (
    pipeline_ops_base,
    pipeline_ops_mqtt,
    pipeline_events_mqtt,
    PipelineStage,
)
from azure.iot.device.iothub.models import Message, MethodRequest
from . import constant, pipeline_ops_iothub, pipeline_events_iothub, mqtt_topic_iothub

logger = logging.getLogger(__name__)


class IotHubMQTTConverter(PipelineStage):
    """
    PipelineStage which converts other Iot and IotHub operations into Mqtt operations.  This stage also
    converts mqtt pipeline events into Iot and IotHub pipeline events.
    """

    def __init__(self):
        super(IotHubMQTTConverter, self).__init__()
        self.feature_to_topic = {}

    def _run_op(self, op):

        if isinstance(op, pipeline_ops_iothub.SetAuthProviderArgs):
            # if we get auth provider args from above, we save some, use some to build topic names,
            # and always pass it down because we know that the MQTT Provider stage will also want
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

            self.continue_with_different_op(
                original_op=op,
                new_op=pipeline_ops_mqtt.SetConnectionArgs(
                    client_id=client_id, hostname=hostname, username=username, ca_cert=op.ca_cert
                ),
            )

        elif isinstance(op, pipeline_ops_iothub.SendTelemetry) or isinstance(
            op, pipeline_ops_iothub.SendOutputEvent
        ):
            # Convert SendTelementry and SendOutputEvent operations into Mqtt Publish operations
            topic = mqtt_topic_iothub.encode_properties(op.message, self.telemetry_topic)
            self.continue_with_different_op(
                original_op=op,
                new_op=pipeline_ops_mqtt.Publish(topic=topic, payload=op.message.data),
            )

        elif isinstance(op, pipeline_ops_iothub.SendMethodResponse):
            # Sending a Method Response gets translated into an MQTT Publish operation
            topic = mqtt_topic_iothub.get_method_topic_for_publish(
                op.method_response.request_id, str(op.method_response.status)
            )
            payload = json.dumps(op.method_response.payload)
            self.continue_with_different_op(
                original_op=op, new_op=pipeline_ops_mqtt.Publish(topic=topic, payload=payload)
            )

        elif isinstance(op, pipeline_ops_base.EnableFeature):
            # Enabling a feature gets translated into an Mqtt subscribe operation
            topic = self.feature_to_topic[op.feature_name]
            self.continue_with_different_op(
                original_op=op, new_op=pipeline_ops_mqtt.Subscribe(topic=topic)
            )

        elif isinstance(op, pipeline_ops_base.DisableFeature):
            # Disabling a feature gets turned into an Mqtt unsubscribe operation
            topic = self.feature_to_topic[op.feature_name]
            self.continue_with_different_op(
                original_op=op, new_op=pipeline_ops_mqtt.Unsubscribe(topic=topic)
            )

        else:
            # All other operations get passed down
            self.continue_op(op)

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
        }

    def _handle_pipeline_event(self, event):
        """
        Pipeline Event handler function to convert incoming Mqtt messages into the appropriate IotHub
        events, based on the topic of the message
        """
        if isinstance(event, pipeline_events_mqtt.IncomingMessage):
            topic = event.topic

            if mqtt_topic_iothub.is_c2d_topic(topic):
                message = Message(event.payload)
                mqtt_topic_iothub.extract_properties_from_topic(topic, message)
                self.handle_pipeline_event(pipeline_events_iothub.C2DMessageEvent(message))

            elif mqtt_topic_iothub.is_input_topic(topic):
                message = Message(event.payload)
                mqtt_topic_iothub.extract_properties_from_topic(topic, message)
                input_name = mqtt_topic_iothub.get_input_name_from_topic(topic)
                self.handle_pipeline_event(
                    pipeline_events_iothub.InputMessageEvent(input_name, message)
                )

            elif mqtt_topic_iothub.is_method_topic(topic):
                rid = mqtt_topic_iothub.get_method_request_id_from_topic(topic)
                method_name = mqtt_topic_iothub.get_method_name_from_topic(topic)
                method_received = MethodRequest(
                    request_id=rid, name=method_name, payload=json.loads(event.payload)
                )
                self._handle_pipeline_event(pipeline_events_iothub.MethodRequest(method_received))

            else:
                logger.warning("Warning: dropping message with topic {}".format(topic))

        else:
            # all other messages get passed up
            PipelineStage._handle_pipeline_event(self, event)
