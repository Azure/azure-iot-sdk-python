# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import six.moves.urllib as urllib
from azure.iot.device.common.pipeline import (
    pipeline_ops_base,
    pipeline_ops_mqtt,
    pipeline_events_mqtt,
    operation_flow,
    pipeline_thread,
)
from azure.iot.device.common.pipeline.pipeline_stages_base import PipelineStage
from azure.iot.device.provisioning.pipeline import constant, mqtt_topic
from azure.iot.device.provisioning.pipeline import (
    pipeline_events_provisioning,
    pipeline_ops_provisioning,
)

logger = logging.getLogger(__name__)


class ProvisioningMQTTConverterStage(PipelineStage):
    """
    PipelineStage which converts other Provisioning pipeline operations into MQTT operations. This stage also
    converts MQTT pipeline events into Provisioning pipeline events.
    """

    def __init__(self):
        super(ProvisioningMQTTConverterStage, self).__init__()
        self.action_to_topic = {}

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):

        if isinstance(op, pipeline_ops_provisioning.SetProvisioningClientConnectionArgsOperation):
            # get security client args from above, save some, use some to build topic names,
            # always pass it down because MQTT protocol stage will also want to receive these args.

            client_id = op.registration_id
            client_version = urllib.parse.quote_plus(constant.USER_AGENT)
            username = "{id_scope}/registrations/{registration_id}/api-version={api_version}&ClientVersion={client_version}".format(
                id_scope=op.id_scope,
                registration_id=op.registration_id,
                api_version=constant.API_VERSION,
                client_version=client_version,
            )

            hostname = op.provisioning_host

            operation_flow.delegate_to_different_op(
                stage=self,
                original_op=op,
                new_op=pipeline_ops_mqtt.SetMQTTConnectionArgsOperation(
                    client_id=client_id,
                    hostname=hostname,
                    username=username,
                    client_cert=op.client_cert,
                    sas_token=op.sas_token,
                ),
            )

        elif isinstance(op, pipeline_ops_provisioning.SendRegistrationRequestOperation):
            # Convert Sending the request into MQTT Publish operations
            topic = mqtt_topic.get_topic_for_register(op.request_id)
            operation_flow.delegate_to_different_op(
                stage=self,
                original_op=op,
                new_op=pipeline_ops_mqtt.MQTTPublishOperation(
                    topic=topic, payload=op.request_payload
                ),
            )

        elif isinstance(op, pipeline_ops_provisioning.SendQueryRequestOperation):
            # Convert Sending the request into MQTT Publish operations
            topic = mqtt_topic.get_topic_for_query(op.request_id, op.operation_id)
            operation_flow.delegate_to_different_op(
                stage=self,
                original_op=op,
                new_op=pipeline_ops_mqtt.MQTTPublishOperation(
                    topic=topic, payload=op.request_payload
                ),
            )

        elif isinstance(op, pipeline_ops_base.EnableFeatureOperation):
            # Enabling for register gets translated into an MQTT subscribe operation
            topic = mqtt_topic.get_topic_for_subscribe()
            operation_flow.delegate_to_different_op(
                stage=self,
                original_op=op,
                new_op=pipeline_ops_mqtt.MQTTSubscribeOperation(topic=topic),
            )

        elif isinstance(op, pipeline_ops_base.DisableFeatureOperation):
            # Disabling a register response gets turned into an MQTT unsubscribe operation
            topic = mqtt_topic.get_topic_for_subscribe()
            operation_flow.delegate_to_different_op(
                stage=self,
                original_op=op,
                new_op=pipeline_ops_mqtt.MQTTUnsubscribeOperation(topic=topic),
            )

        else:
            # All other operations get passed down
            operation_flow.pass_op_to_next_stage(self, op)

    @pipeline_thread.runs_on_pipeline_thread
    def _handle_pipeline_event(self, event):
        """
        Pipeline Event handler function to convert incoming MQTT messages into the appropriate DPS
        events, based on the topic of the message
        """
        if isinstance(event, pipeline_events_mqtt.IncomingMQTTMessageEvent):
            topic = event.topic

            if mqtt_topic.is_dps_response_topic(topic):
                logger.info(
                    "Received payload:{payload} on topic:{topic}".format(
                        payload=event.payload, topic=topic
                    )
                )
                key_values = mqtt_topic.extract_properties_from_topic(topic)
                status_code = mqtt_topic.extract_status_code_from_topic(topic)
                request_id = key_values["rid"][0]
                if event.payload is not None:
                    response = event.payload.decode("utf-8")
                # Extract pertinent information from mqtt topic
                # like status code request_id and send it upwards.
                operation_flow.pass_event_to_previous_stage(
                    self,
                    pipeline_events_provisioning.RegistrationResponseEvent(
                        request_id, status_code, key_values, response
                    ),
                )
            else:
                logger.warning("Unknown topic: {} passing up to next handler".format(topic))
                operation_flow.pass_event_to_previous_stage(self, event)

        else:
            # all other messages get passed up
            operation_flow.pass_event_to_previous_stage(self, event)
