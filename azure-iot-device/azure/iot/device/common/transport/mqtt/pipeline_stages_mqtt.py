# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
from azure.iot.device.common.transport.pipeline_stages_base import PipelineStage
from azure.iot.device.common.transport import pipeline_ops_base
from . import pipeline_ops_mqtt
from . import pipeline_events_mqtt
from azure.iot.device.common.transport.mqtt.mqtt_provider import MQTTProvider

logger = logging.getLogger(__name__)


class Provider(PipelineStage):
    """
    PipelineStage object which is responsible for interfacing with the MQTT provider object.
    This stage handles all MQTT operations and any other operations (such as Connect) which
    is not in the MQTT group of operations, but can only be run at the protocol level.
    """

    def _run_op(self, op):
        if isinstance(op, pipeline_ops_mqtt.SetConnectionArgs):
            # SetConnectionArgs is where we create our MQTTProvider object and set
            # all of its properties.
            logger.info("{}({}): got connection args".format(self.name, op.name))
            self.hostname = op.hostname
            self.username = op.username
            self.client_id = op.client_id
            self.ca_cert = op.ca_cert
            self.provider = MQTTProvider(
                client_id=self.client_id,
                hostname=self.hostname,
                username=self.username,
                ca_cert=self.ca_cert,
            )
            self.provider.on_mqtt_connected = self.on_connected
            self.provider.on_mqtt_disconnected = self.on_disconnected
            self.provider.on_mqtt_message_received = self._on_message_received
            self.pipeline_root.provider = self.provider
            self.complete_op(op)

        elif isinstance(op, pipeline_ops_base.SetSasToken):
            # When we get a sas token from above, we just save it for later
            logger.info("{}({}): got password".format(self.name, op.name))
            self.sas_token = op.sas_token
            self.complete_op(op)

        elif isinstance(op, pipeline_ops_base.Connect):
            logger.info("{}({}): conneting".format(self.name, op.name))

            def on_connected():
                logger.info("{}({}): on_connected.  completing op.".format(self.name, op.name))
                self.provider.on_mqtt_connected = self.on_connected
                self.on_connected()
                self.complete_op(op)

            self.provider.on_mqtt_connected = on_connected
            self.provider.connect(self.sas_token)

        elif isinstance(op, pipeline_ops_base.Disconnect):
            logger.info("{}({}): disconneting".format(self.name, op.name))

            def on_disconnected():
                logger.info("{}({}): on_disconnected.  completing op.".format(self.name, op.name))
                self.provider.on_mqtt_disconnected = self.on_disconnected
                self.on_disconnected()
                self.complete_op(op)

            self.provider.on_mqtt_disconnected = on_disconnected
            self.provider.disconnect()

        elif isinstance(op, pipeline_ops_mqtt.Publish):
            logger.info("{}({}): publishing on {}".format(self.name, op.name, op.topic))

            def on_published():
                logger.info("{}({}): PUBACK received. completing op.".format(self.name, op.name))
                self.complete_op(op)

            self.provider.publish(topic=op.topic, payload=op.payload, callback=on_published)

        elif isinstance(op, pipeline_ops_mqtt.Subscribe):
            logger.info("{}({}): subscribing to {}".format(self.name, op.name, op.topic))

            def on_subscribed():
                logger.info("{}({}): SUBACK received. completing op.".format(self.name, op.name))
                self.complete_op(op)

            self.provider.subscribe(topic=op.topic, callback=on_subscribed)

        elif isinstance(op, pipeline_ops_mqtt.Unsubscribe):
            logger.info("{}({}): unsubscribing from {}".format(self.name, op.name, op.topic))

            def on_unsubscribed():
                logger.info("{}({}): UNSUBACK received.  completing op.".format(self.name, op.name))
                self.complete_op(op)

            self.provider.unsubscribe(topic=op.topic, callback=on_unsubscribed)

        else:
            self.continue_op(op)

    def _on_message_received(self, topic, payload):
        """
        Handler that gets called by the protocol library when an incoming message arrives.
        Convert that message into a pipeline event and pass it up for someone to handle.
        """
        self.handle_pipeline_event(
            pipeline_events_mqtt.IncomingMessage(topic=topic, payload=payload)
        )
