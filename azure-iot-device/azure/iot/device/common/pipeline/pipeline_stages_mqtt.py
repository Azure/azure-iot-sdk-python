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
)
from azure.iot.device.common.mqtt_client_operator import MQTTClientOperator

logger = logging.getLogger(__name__)


class MQTTClientStage(PipelineStage):
    """
    PipelineStage object which is responsible for interfacing with the MQTT protocol wrapper object.
    This stage handles all MQTT operations and any other operations (such as ConnectOperation) which
    is not in the MQTT group of operations, but can only be run at the protocol level.
    """

    def _run_op(self, op):
        if isinstance(op, pipeline_ops_mqtt.SetMQTTConnectionArgsOperation):
            # pipeline_ops_mqtt.SetMQTTConnectionArgsOperation is where we create our MQTTClientOperator object and set
            # all of its properties.
            logger.info("{}({}): got connection args".format(self.name, op.name))
            self.hostname = op.hostname
            self.username = op.username
            self.client_id = op.client_id
            self.ca_cert = op.ca_cert
            self.sas_token = None
            self.trusted_certificate_chain = None
            self.client_operator = MQTTClientOperator(
                client_id=self.client_id,
                hostname=self.hostname,
                username=self.username,
                ca_cert=self.ca_cert,
            )
            self.client_operator.on_mqtt_connected = self.on_connected
            self.client_operator.on_mqtt_disconnected = self.on_disconnected
            self.client_operator.on_mqtt_message_received = self._on_message_received
            self.pipeline_root.client_operator = self.client_operator
            operation_flow.complete_op(self, op)

        elif isinstance(op, pipeline_ops_base.SetSasTokenOperation):
            # When we get a sas token from above, we just save it for later
            logger.info("{}({}): got password".format(self.name, op.name))
            self.sas_token = op.sas_token
            operation_flow.complete_op(self, op)

        elif isinstance(op, pipeline_ops_base.SetClientAuthenticationCertificateOperation):
            # When we get a certificate from above, we just save it for later
            logger.info("{}({}): got certificate".format(self.name, op.name))
            self.trusted_certificate_chain = op.certificate
            operation_flow.complete_op(self, op)

        elif isinstance(op, pipeline_ops_base.ConnectOperation):
            logger.info("{}({}): conneting".format(self.name, op.name))

            def on_connected():
                logger.info("{}({}): on_connected.  completing op.".format(self.name, op.name))
                self.client_operator.on_mqtt_connected = self.on_connected
                self.on_connected()
                operation_flow.complete_op(self, op)

            # A note on exceptions handling in Connect, Disconnct, and Reconnet:
            #
            # All calls into self.client_operator can raise an exception, and this is OK.
            # The exception handler in PipelineStage.run_op() will catch these errors
            # and propagate them to the caller.  This is an intentional design of the
            # pipeline, that stages, etc, don't need to worry about catching exceptions
            # except for special cases.
            #
            # The code right below this comment is This is a special case.  In addition
            # to this "normal" exception handling, we add another exception handler
            # into this class' Connect, Reconnect, and Disconnect code.  We need to
            # do this because client_operator.on_mqtt_connected and client_operator.on_mqtt_disconnected
            # are both _handler_ functions instead of _callbacks_.
            #
            # Because they're handlers instead of callbacks, we need to change the
            # handlers while the connection is established.  We do this so we can
            # know when the protocol is connected so we can move on to the next step.
            # Once the connection is established, we change the handler back to its
            # old value before finishing.
            #
            # The exception handling below is to reset the handler back to its original
            # value in the case where client_operator.connect raises an exception.  Again,
            # this extra exception handling is only necessary in the Connect, Disconnect,
            # and Reconnect case because they're the only cases that use handlers instead
            # of callbacks.
            #
            self.client_operator.on_mqtt_connected = on_connected
            try:
                self.client_operator.connect(
                    password=self.sas_token, client_certificate=self.trusted_certificate_chain
                )
            except Exception as e:
                self.client_operator.on_mqtt_connected = self.on_connected
                raise e

        elif isinstance(op, pipeline_ops_base.ReconnectOperation):
            logger.info("{}({}): reconnecting".format(self.name, op.name))

            def on_connected():
                logger.info("{}({}): on_connected.  completing op.".format(self.name, op.name))
                self.client_operator.on_mqtt_connected = self.on_connected
                self.on_connected()
                operation_flow.complete_op(self, op)

            # See "A note on exception handling" above
            self.client_operator.on_mqtt_connected = on_connected
            try:
                self.client_operator.reconnect(self.sas_token)
            except Exception as e:
                self.client_operator.on_mqtt_connected = self.on_connected
                raise e

        elif isinstance(op, pipeline_ops_base.DisconnectOperation):
            logger.info("{}({}): disconnecting".format(self.name, op.name))

            def on_disconnected():
                logger.info("{}({}): on_disconnected.  completing op.".format(self.name, op.name))
                self.client_operator.on_mqtt_disconnected = self.on_disconnected
                self.on_disconnected()
                operation_flow.complete_op(self, op)

            # See "A note on exception handling" above
            self.client_operator.on_mqtt_disconnected = on_disconnected
            try:
                self.client_operator.disconnect()
            except Exception as e:
                self.client_operator.on_mqtt_disconnected = self.on_disconnected
                raise e

        elif isinstance(op, pipeline_ops_mqtt.MQTTPublishOperation):
            logger.info("{}({}): publishing on {}".format(self.name, op.name, op.topic))

            def on_published():
                logger.info("{}({}): PUBACK received. completing op.".format(self.name, op.name))
                operation_flow.complete_op(self, op)

            self.client_operator.publish(topic=op.topic, payload=op.payload, callback=on_published)

        elif isinstance(op, pipeline_ops_mqtt.MQTTSubscribeOperation):
            logger.info("{}({}): subscribing to {}".format(self.name, op.name, op.topic))

            def on_subscribed():
                logger.info("{}({}): SUBACK received. completing op.".format(self.name, op.name))
                operation_flow.complete_op(self, op)

            self.client_operator.subscribe(topic=op.topic, callback=on_subscribed)

        elif isinstance(op, pipeline_ops_mqtt.MQTTUnsubscribeOperation):
            logger.info("{}({}): unsubscribing from {}".format(self.name, op.name, op.topic))

            def on_unsubscribed():
                logger.info("{}({}): UNSUBACK received.  completing op.".format(self.name, op.name))
                operation_flow.complete_op(self, op)

            self.client_operator.unsubscribe(topic=op.topic, callback=on_unsubscribed)

        else:
            operation_flow.pass_op_to_next_stage(self, op)

    def _on_message_received(self, topic, payload):
        """
        Handler that gets called by the protocol library when an incoming message arrives.
        Convert that message into a pipeline event and pass it up for someone to handle.
        """
        self.handle_pipeline_event(
            pipeline_events_mqtt.IncomingMQTTMessageEvent(topic=topic, payload=payload)
        )
