# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import json
from six.moves import urllib
from azure.iot.device.common import version_compat
from azure.iot.device.common.pipeline import (
    pipeline_events_base,
    pipeline_ops_base,
    pipeline_ops_mqtt,
    pipeline_events_mqtt,
    PipelineStage,
    pipeline_thread,
)
from azure.iot.device.iothub.models import Message, MethodRequest
from . import pipeline_ops_iothub, pipeline_events_iothub, mqtt_topic_iothub
from . import constant as pipeline_constant
from . import exceptions as pipeline_exceptions
from azure.iot.device import constant as pkg_constant
from azure.iot.device import user_agent

logger = logging.getLogger(__name__)


class IoTHubMQTTTranslationStage(PipelineStage):
    """
    PipelineStage which converts other Iot and IoTHub operations into MQTT operations.  This stage also
    converts mqtt pipeline events into Iot and IoTHub pipeline events.
    """

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):

        if isinstance(op, pipeline_ops_base.InitializePipelineOperation):

            if self.pipeline_root.pipeline_configuration.module_id:
                # Module Format
                client_id = "{}/{}".format(
                    self.pipeline_root.pipeline_configuration.device_id,
                    self.pipeline_root.pipeline_configuration.module_id,
                )
            else:
                # Device Format
                client_id = self.pipeline_root.pipeline_configuration.device_id

            query_param_seq = []

            # Apply query parameters (i.e. key1=value1&key2=value2...&keyN=valueN format)
            custom_product_info = str(self.pipeline_root.pipeline_configuration.product_info)
            if custom_product_info.startswith(
                pkg_constant.DIGITAL_TWIN_PREFIX
            ):  # Digital Twin Stuff
                query_param_seq.append(("api-version", pkg_constant.DIGITAL_TWIN_API_VERSION))
                query_param_seq.append(("DeviceClientType", user_agent.get_iothub_user_agent()))
                query_param_seq.append(
                    (pkg_constant.DIGITAL_TWIN_QUERY_HEADER, custom_product_info)
                )
            else:
                query_param_seq.append(("api-version", pkg_constant.IOTHUB_API_VERSION))
                query_param_seq.append(
                    ("DeviceClientType", user_agent.get_iothub_user_agent() + custom_product_info)
                )

            username = "{hostname}/{client_id}/?{query_params}".format(
                hostname=self.pipeline_root.pipeline_configuration.hostname,
                client_id=client_id,
                query_params=version_compat.urlencode(
                    query_param_seq, quote_via=urllib.parse.quote
                ),
            )

            # Dynamically attach the derived MQTT values to the InitalizePipelineOperation
            # to be used later down the pipeline
            op.username = username
            op.client_id = client_id

            self.send_op_down(op)

        elif isinstance(op, pipeline_ops_iothub.SendD2CMessageOperation) or isinstance(
            op, pipeline_ops_iothub.SendOutputMessageOperation
        ):
            # Convert SendTelementry and SendOutputMessageOperation operations into MQTT Publish operations
            telemetry_topic = mqtt_topic_iothub.get_telemetry_topic_for_publish(
                device_id=self.pipeline_root.pipeline_configuration.device_id,
                module_id=self.pipeline_root.pipeline_configuration.module_id,
            )
            topic = mqtt_topic_iothub.encode_message_properties_in_topic(
                op.message, telemetry_topic
            )
            worker_op = op.spawn_worker_op(
                worker_op_type=pipeline_ops_mqtt.MQTTPublishOperation,
                topic=topic,
                payload=op.message.data,
            )
            self.send_op_down(worker_op)

        elif isinstance(op, pipeline_ops_iothub.SendMethodResponseOperation):
            # Sending a Method Response gets translated into an MQTT Publish operation
            topic = mqtt_topic_iothub.get_method_topic_for_publish(
                op.method_response.request_id, op.method_response.status
            )
            payload = json.dumps(op.method_response.payload)
            worker_op = op.spawn_worker_op(
                worker_op_type=pipeline_ops_mqtt.MQTTPublishOperation, topic=topic, payload=payload
            )
            self.send_op_down(worker_op)

        elif isinstance(op, pipeline_ops_base.EnableFeatureOperation):
            # Enabling a feature gets translated into an MQTT subscribe operation
            topic = self._get_feature_subscription_topic(op.feature_name)
            worker_op = op.spawn_worker_op(
                worker_op_type=pipeline_ops_mqtt.MQTTSubscribeOperation, topic=topic
            )
            self.send_op_down(worker_op)

        elif isinstance(op, pipeline_ops_base.DisableFeatureOperation):
            # Disabling a feature gets turned into an MQTT unsubscribe operation
            topic = self._get_feature_subscription_topic(op.feature_name)
            worker_op = op.spawn_worker_op(
                worker_op_type=pipeline_ops_mqtt.MQTTUnsubscribeOperation, topic=topic
            )
            self.send_op_down(worker_op)

        elif isinstance(op, pipeline_ops_base.RequestOperation):
            if op.request_type == pipeline_constant.TWIN:
                topic = mqtt_topic_iothub.get_twin_topic_for_publish(
                    method=op.method,
                    resource_location=op.resource_location,
                    request_id=op.request_id,
                )
                worker_op = op.spawn_worker_op(
                    worker_op_type=pipeline_ops_mqtt.MQTTPublishOperation,
                    topic=topic,
                    payload=op.request_body,
                )
                self.send_op_down(worker_op)
            else:
                raise pipeline_exceptions.OperationError(
                    "RequestOperation request_type {} not supported".format(op.request_type)
                )

        else:
            # All other operations get passed down
            super(IoTHubMQTTTranslationStage, self)._run_op(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _get_feature_subscription_topic(self, feature):
        if feature == pipeline_constant.C2D_MSG:
            return mqtt_topic_iothub.get_c2d_topic_for_subscribe(
                self.pipeline_root.pipeline_configuration.device_id
            )
        elif feature == pipeline_constant.INPUT_MSG:
            return mqtt_topic_iothub.get_input_topic_for_subscribe(
                self.pipeline_root.pipeline_configuration.device_id,
                self.pipeline_root.pipeline_configuration.module_id,
            )
        elif feature == pipeline_constant.METHODS:
            return mqtt_topic_iothub.get_method_topic_for_subscribe()
        elif feature == pipeline_constant.TWIN:
            return mqtt_topic_iothub.get_twin_response_topic_for_subscribe()
        elif feature == pipeline_constant.TWIN_PATCHES:
            return mqtt_topic_iothub.get_twin_patch_topic_for_subscribe()
        else:
            logger.error("Cannot retrieve MQTT topic for subscription to invalid feature")
            raise pipeline_exceptions.OperationError(
                "Trying to enable/disable invalid feature - {}".format(feature)
            )

    @pipeline_thread.runs_on_pipeline_thread
    def _handle_pipeline_event(self, event):
        """
        Pipeline Event handler function to convert incoming MQTT messages into the appropriate IoTHub
        events, based on the topic of the message
        """
        # TODO: should we always be decoding the payload? Seems strange to only sometimes do it.
        # Is there value to the user getting the original bytestring from the wire?
        if isinstance(event, pipeline_events_mqtt.IncomingMQTTMessageEvent):
            topic = event.topic
            device_id = self.pipeline_root.pipeline_configuration.device_id
            module_id = self.pipeline_root.pipeline_configuration.module_id

            if mqtt_topic_iothub.is_c2d_topic(topic, device_id):
                message = Message(event.payload)
                mqtt_topic_iothub.extract_message_properties_from_topic(topic, message)
                self.send_event_up(pipeline_events_iothub.C2DMessageEvent(message))

            elif mqtt_topic_iothub.is_input_topic(topic, device_id, module_id):
                message = Message(event.payload)
                mqtt_topic_iothub.extract_message_properties_from_topic(topic, message)
                # CT-TODO: refactor to not need separate input name
                input_name = mqtt_topic_iothub.get_input_name_from_topic(topic)
                message.input_name = input_name
                self.send_event_up(pipeline_events_iothub.InputMessageEvent(input_name, message))

            elif mqtt_topic_iothub.is_method_topic(topic):
                request_id = mqtt_topic_iothub.get_method_request_id_from_topic(topic)
                method_name = mqtt_topic_iothub.get_method_name_from_topic(topic)
                method_received = MethodRequest(
                    request_id=request_id,
                    name=method_name,
                    payload=json.loads(event.payload.decode("utf-8")),
                )
                self.send_event_up(pipeline_events_iothub.MethodRequestEvent(method_received))

            elif mqtt_topic_iothub.is_twin_response_topic(topic):
                request_id = mqtt_topic_iothub.get_twin_request_id_from_topic(topic)
                status_code = int(mqtt_topic_iothub.get_twin_status_code_from_topic(topic))
                self.send_event_up(
                    pipeline_events_base.ResponseEvent(
                        request_id=request_id, status_code=status_code, response_body=event.payload
                    )
                )

            elif mqtt_topic_iothub.is_twin_desired_property_patch_topic(topic):
                self.send_event_up(
                    pipeline_events_iothub.TwinDesiredPropertiesPatchEvent(
                        patch=json.loads(event.payload.decode("utf-8"))
                    )
                )

            else:
                logger.debug("Unknown topic: {} passing up to next handler".format(topic))
                self.send_event_up(event)

        else:
            # all other messages get passed up
            self.send_event_up(event)
