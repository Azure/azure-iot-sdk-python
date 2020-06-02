# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import six.moves.urllib as urllib
from azure.iot.device.common import version_compat
from azure.iot.device.common.pipeline import (
    pipeline_ops_base,
    pipeline_ops_mqtt,
    pipeline_events_mqtt,
    pipeline_thread,
    pipeline_events_base,
    pipeline_exceptions,
)
from azure.iot.device.common.pipeline.pipeline_stages_base import PipelineStage
from azure.iot.device.provisioning.pipeline import mqtt_topic_provisioning
from azure.iot.device.provisioning.pipeline import pipeline_ops_provisioning
from azure.iot.device import constant as pkg_constant
from . import constant as pipeline_constant
from azure.iot.device import user_agent

logger = logging.getLogger(__name__)


class ProvisioningMQTTTranslationStage(PipelineStage):
    """
    PipelineStage which converts other Provisioning pipeline operations into MQTT operations. This stage also
    converts MQTT pipeline events into Provisioning pipeline events.
    """

    def __init__(self):
        super(ProvisioningMQTTTranslationStage, self).__init__()
        self.action_to_topic = {}

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):

        if isinstance(op, pipeline_ops_base.InitializePipelineOperation):

            client_id = self.pipeline_root.pipeline_configuration.registration_id
            query_param_seq = [
                ("api-version", pkg_constant.PROVISIONING_API_VERSION),
                ("ClientVersion", user_agent.get_provisioning_user_agent()),
            ]
            username = "{id_scope}/registrations/{registration_id}/{query_params}".format(
                id_scope=self.pipeline_root.pipeline_configuration.id_scope,
                registration_id=self.pipeline_root.pipeline_configuration.registration_id,
                query_params=version_compat.urlencode(
                    query_param_seq, quote_via=urllib.parse.quote
                ),
            )

            # Dynamically attach the derived MQTT values to the InitalizePipelineOperation
            # to be used later down the pipeline
            op.username = username
            op.client_id = client_id

            self.send_op_down(op)

        elif isinstance(op, pipeline_ops_base.RequestOperation):
            if op.request_type == pipeline_constant.REGISTER:
                topic = mqtt_topic_provisioning.get_register_topic_for_publish(
                    request_id=op.request_id
                )
                worker_op = op.spawn_worker_op(
                    worker_op_type=pipeline_ops_mqtt.MQTTPublishOperation,
                    topic=topic,
                    payload=op.request_body,
                )
                self.send_op_down(worker_op)
            elif op.request_type == pipeline_constant.QUERY:
                topic = mqtt_topic_provisioning.get_query_topic_for_publish(
                    request_id=op.request_id, operation_id=op.query_params["operation_id"]
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

        elif isinstance(op, pipeline_ops_base.EnableFeatureOperation):
            # The only supported feature is REGISTER
            if not op.feature_name == pipeline_constant.REGISTER:
                raise pipeline_exceptions.OperationError(
                    "Trying to enable/disable invalid feature - {}".format(op.feature_name)
                )
            # Enabling for register gets translated into an MQTT subscribe operation
            topic = mqtt_topic_provisioning.get_register_topic_for_subscribe()
            worker_op = op.spawn_worker_op(
                worker_op_type=pipeline_ops_mqtt.MQTTSubscribeOperation, topic=topic
            )
            self.send_op_down(worker_op)

        elif isinstance(op, pipeline_ops_base.DisableFeatureOperation):
            # The only supported feature is REGISTER
            if not op.feature_name == pipeline_constant.REGISTER:
                raise pipeline_exceptions.OperationError(
                    "Trying to enable/disable invalid feature - {}".format(op.feature_name)
                )
            # Disabling a register response gets turned into an MQTT unsubscribe operation
            topic = mqtt_topic_provisioning.get_register_topic_for_subscribe()
            worker_op = op.spawn_worker_op(
                worker_op_type=pipeline_ops_mqtt.MQTTUnsubscribeOperation, topic=topic
            )
            self.send_op_down(worker_op)

        else:
            # All other operations get passed down
            super(ProvisioningMQTTTranslationStage, self)._run_op(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _handle_pipeline_event(self, event):
        """
        Pipeline Event handler function to convert incoming MQTT messages into the appropriate DPS
        events, based on the topic of the message
        """
        if isinstance(event, pipeline_events_mqtt.IncomingMQTTMessageEvent):
            topic = event.topic

            if mqtt_topic_provisioning.is_dps_response_topic(topic):
                logger.info(
                    "Received payload:{payload} on topic:{topic}".format(
                        payload=event.payload, topic=topic
                    )
                )
                key_values = mqtt_topic_provisioning.extract_properties_from_dps_response_topic(
                    topic
                )
                retry_after = key_values.get("retry-after", None)
                status_code = mqtt_topic_provisioning.extract_status_code_from_dps_response_topic(
                    topic
                )
                request_id = key_values["rid"]

                self.send_event_up(
                    pipeline_events_base.ResponseEvent(
                        request_id=request_id,
                        status_code=int(status_code, 10),
                        response_body=event.payload,
                        retry_after=retry_after,
                    )
                )
            else:
                logger.warning("Unknown topic: {} passing up to next handler".format(topic))
                self.send_event_up(event)

        else:
            # all other messages get passed up
            self.send_event_up(event)
