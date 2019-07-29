# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
from . import (
    pipeline_ops_base,
    PipelineStage,
    pipeline_ops_mqtt,
    pipeline_events_mqtt,
    operation_flow,
    pipeline_thread,
)
from azure.iot.device.common.mqtt_transport import MQTTTransport

logger = logging.getLogger(__name__)


class MQTTTransportStage(PipelineStage):
    """
    PipelineStage object which is responsible for interfacing with the MQTT protocol wrapper object.
    This stage handles all MQTT operations and any other operations (such as ConnectOperation) which
    is not in the MQTT group of operations, but can only be run at the protocol level.
    """

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        if isinstance(op, pipeline_ops_mqtt.SetMQTTConnectionArgsOperation):
            # pipeline_ops_mqtt.SetMQTTConnectionArgsOperation is where we create our MQTTTransport object and set
            # all of its properties.
            logger.info("{}({}): got connection args".format(self.name, op.name))
            self.hostname = op.hostname
            self.username = op.username
            self.client_id = op.client_id
            self.ca_cert = op.ca_cert
            self.sas_token = op.sas_token
            self.client_cert = op.client_cert

            self.transport = MQTTTransport(
                client_id=self.client_id,
                hostname=self.hostname,
                username=self.username,
                ca_cert=self.ca_cert,
                x509_cert=self.client_cert,
            )
            self.transport.on_mqtt_connected = self.on_connected
            self.transport.on_mqtt_disconnected = self.on_disconnected
            self.transport.on_mqtt_message_received = self._on_message_received
            self.pipeline_root.transport = self.transport
            operation_flow.complete_op(self, op)

        elif isinstance(op, pipeline_ops_base.ConnectOperation):
            logger.info("{}({}): conneting".format(self.name, op.name))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_connected():
                logger.info("{}({}): on_connected.  completing op.".format(self.name, op.name))
                self.transport.on_mqtt_connected = self.on_connected
                self.on_connected()
                operation_flow.complete_op(self, op)

            # A note on exceptions handling in Connect, Disconnct, and Reconnet:
            #
            # All calls into self.transport can raise an exception, and this is OK.
            # The exception handler in PipelineStage.run_op() will catch these errors
            # and propagate them to the caller.  This is an intentional design of the
            # pipeline, that stages, etc, don't need to worry about catching exceptions
            # except for special cases.
            #
            # The code right below this comment is This is a special case.  In addition
            # to this "normal" exception handling, we add another exception handler
            # into this class' Connect, Reconnect, and Disconnect code.  We need to
            # do this because transport.on_mqtt_connected and transport.on_mqtt_disconnected
            # are both _handler_ functions instead of _callbacks_.
            #
            # Because they're handlers instead of callbacks, we need to change the
            # handlers while the connection is established.  We do this so we can
            # know when the protocol is connected so we can move on to the next step.
            # Once the connection is established, we change the handler back to its
            # old value before finishing.
            #
            # The exception handling below is to reset the handler back to its original
            # value in the case where transport.connect raises an exception.  Again,
            # this extra exception handling is only necessary in the Connect, Disconnect,
            # and Reconnect case because they're the only cases that use handlers instead
            # of callbacks.
            #
            self.transport.on_mqtt_connected = on_connected
            try:
                self.transport.connect(password=self.sas_token)
            except Exception as e:
                self.transport.on_mqtt_connected = self.on_connected
                raise e

        elif isinstance(op, pipeline_ops_base.ReconnectOperation):
            logger.info("{}({}): reconnecting".format(self.name, op.name))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_connected():
                logger.info("{}({}): on_connected.  completing op.".format(self.name, op.name))
                self.transport.on_mqtt_connected = self.on_connected
                self.on_connected()
                operation_flow.complete_op(self, op)

            # See "A note on exception handling" above
            self.transport.on_mqtt_connected = on_connected
            try:
                self.transport.reconnect(password=self.sas_token)
            except Exception as e:
                self.transport.on_mqtt_connected = self.on_connected
                raise e

        elif isinstance(op, pipeline_ops_base.DisconnectOperation):
            logger.info("{}({}): disconnecting".format(self.name, op.name))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_disconnected():
                logger.info("{}({}): on_disconnected.  completing op.".format(self.name, op.name))
                self.transport.on_mqtt_disconnected = self.on_disconnected
                self.on_disconnected()
                operation_flow.complete_op(self, op)

            # See "A note on exception handling" above
            self.transport.on_mqtt_disconnected = on_disconnected
            try:
                self.transport.disconnect()
            except Exception as e:
                self.transport.on_mqtt_disconnected = self.on_disconnected
                raise e

        elif isinstance(op, pipeline_ops_mqtt.MQTTPublishOperation):
            logger.info("{}({}): publishing on {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_published():
                logger.info("{}({}): PUBACK received. completing op.".format(self.name, op.name))
                operation_flow.complete_op(self, op)

            self.transport.publish(topic=op.topic, payload=op.payload, callback=on_published)

        elif isinstance(op, pipeline_ops_mqtt.MQTTSubscribeOperation):
            logger.info("{}({}): subscribing to {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_subscribed():
                logger.info("{}({}): SUBACK received. completing op.".format(self.name, op.name))
                operation_flow.complete_op(self, op)

            self.transport.subscribe(topic=op.topic, callback=on_subscribed)

        elif isinstance(op, pipeline_ops_mqtt.MQTTUnsubscribeOperation):
            logger.info("{}({}): unsubscribing from {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_unsubscribed():
                logger.info("{}({}): UNSUBACK received.  completing op.".format(self.name, op.name))
                operation_flow.complete_op(self, op)

            self.transport.unsubscribe(topic=op.topic, callback=on_unsubscribed)

        else:
            operation_flow.pass_op_to_next_stage(self, op)

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def _on_message_received(self, topic, payload):
        """
        Handler that gets called by the protocol library when an incoming message arrives.
        Convert that message into a pipeline event and pass it up for someone to handle.
        """
        operation_flow.pass_event_to_previous_stage(
            stage=self,
            event=pipeline_events_mqtt.IncomingMQTTMessageEvent(topic=topic, payload=payload),
        )

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def on_connected(self):
        super(MQTTTransportStage, self).on_connected()

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def on_disconnected(self):
        super(MQTTTransportStage, self).on_disconnected()
