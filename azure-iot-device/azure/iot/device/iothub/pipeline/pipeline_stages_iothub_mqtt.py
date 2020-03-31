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
from azure.iot.device.product_info import ProductInfo

logger = logging.getLogger(__name__)


class IoTHubMQTTTranslationStage(PipelineStage):
    """
    PipelineStage which converts other Iot and IoTHub operations into MQTT operations.  This stage also
    converts mqtt pipeline events into Iot and IoTHub pipeline events.
    """

    def __init__(self):
        super(IoTHubMQTTTranslationStage, self).__init__()
        self.feature_to_topic = {}
        self.device_id = None
        self.module_id = None

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):

        if isinstance(op, pipeline_ops_iothub.SetIoTHubConnectionArgsOperation):
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

            # For MQTT, the entire user agent string should be appended to the username field in the connect packet
            # For example, the username may look like this without custom parameters:
            # yosephsandboxhub.azure-devices.net/alpha/?api-version=2018-06-30&DeviceClientType=py-azure-iot-device%2F2.0.0-preview.12
            # The customer user agent string would simply be appended to the end of this username, in URL Encoded format.
            query_param_seq = [
                ("api-version", pkg_constant.IOTHUB_API_VERSION),
                (
                    "DeviceClientType",
                    ProductInfo.get_iothub_user_agent()
                    + str(self.pipeline_root.pipeline_configuration.product_info),
                ),
            ]
            username = "{hostname}/{client_id}/?{query_params}".format(
                hostname=op.hostname,
                client_id=client_id,
                query_params=version_compat.urlencode(
                    query_param_seq, quote_via=urllib.parse.quote
                ),
            )

            if op.gateway_hostname:
                hostname = op.gateway_hostname
            else:
                hostname = op.hostname

            # TODO: test to make sure client_cert and sas_token travel down correctly
            worker_op = op.spawn_worker_op(
                worker_op_type=pipeline_ops_mqtt.SetMQTTConnectionArgsOperation,
                client_id=client_id,
                hostname=hostname,
                username=username,
                server_verification_cert=op.server_verification_cert,
                client_cert=op.client_cert,
                sas_token=op.sas_token,
            )
            self.send_op_down(worker_op)

        elif (
            isinstance(op, pipeline_ops_base.UpdateSasTokenOperation)
            and self.pipeline_root.connected
        ):
            logger.debug(
                "{}({}): Connected.  Passing op down and reauthorizing after token is updated.".format(
                    self.name, op.name
                )
            )

            # make a callback that either fails the UpdateSasTokenOperation (if the lower level failed it),
            # or issues a ReauthorizeConnectionOperation (if the lower level returned success for the UpdateSasTokenOperation)
            def on_token_update_complete(op, error):
                if error:
                    logger.error(
                        "{}({}) token update failed.  returning failure {}".format(
                            self.name, op.name, error
                        )
                    )
                else:
                    logger.debug(
                        "{}({}) token update succeeded.  reauthorizing".format(self.name, op.name)
                    )

                    # Stop completion of Token Update op, and only continue upon completion of ReauthorizeConnectionOperation
                    op.halt_completion()
                    worker_op = op.spawn_worker_op(
                        worker_op_type=pipeline_ops_base.ReauthorizeConnectionOperation
                    )

                    self.send_op_down(worker_op)

            # now, pass the UpdateSasTokenOperation down with our new callback.
            op.add_callback(on_token_update_complete)
            self.send_op_down(op)

        elif isinstance(op, pipeline_ops_iothub.SendD2CMessageOperation) or isinstance(
            op, pipeline_ops_iothub.SendOutputEventOperation
        ):
            # Convert SendTelementry and SendOutputEventOperation operations into MQTT Publish operations
            topic = mqtt_topic_iothub.encode_message_properties_in_topic(
                op.message, self.telemetry_topic
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
                op.method_response.request_id, str(op.method_response.status)
            )
            payload = json.dumps(op.method_response.payload)
            worker_op = op.spawn_worker_op(
                worker_op_type=pipeline_ops_mqtt.MQTTPublishOperation, topic=topic, payload=payload
            )
            self.send_op_down(worker_op)

        elif isinstance(op, pipeline_ops_base.EnableFeatureOperation):
            # Enabling a feature gets translated into an MQTT subscribe operation
            topic = self.feature_to_topic[op.feature_name]
            worker_op = op.spawn_worker_op(
                worker_op_type=pipeline_ops_mqtt.MQTTSubscribeOperation, topic=topic
            )
            self.send_op_down(worker_op)

        elif isinstance(op, pipeline_ops_base.DisableFeatureOperation):
            # Disabling a feature gets turned into an MQTT unsubscribe operation
            topic = self.feature_to_topic[op.feature_name]
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
    def _set_topic_names(self, device_id, module_id):
        """
        Build topic names based on the device_id and module_id passed.
        """
        self.telemetry_topic = mqtt_topic_iothub.get_telemetry_topic_for_publish(
            device_id, module_id
        )
        self.feature_to_topic = {
            pipeline_constant.C2D_MSG: (mqtt_topic_iothub.get_c2d_topic_for_subscribe(device_id)),
            pipeline_constant.INPUT_MSG: (
                mqtt_topic_iothub.get_input_topic_for_subscribe(device_id, module_id)
            ),
            pipeline_constant.METHODS: (mqtt_topic_iothub.get_method_topic_for_subscribe()),
            pipeline_constant.TWIN: (mqtt_topic_iothub.get_twin_response_topic_for_subscribe()),
            pipeline_constant.TWIN_PATCHES: (
                mqtt_topic_iothub.get_twin_patch_topic_for_subscribe()
            ),
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
                mqtt_topic_iothub.extract_message_properties_from_topic(topic, message)
                self.send_event_up(pipeline_events_iothub.C2DMessageEvent(message))

            elif mqtt_topic_iothub.is_input_topic(topic, self.device_id, self.module_id):
                message = Message(event.payload)
                mqtt_topic_iothub.extract_message_properties_from_topic(topic, message)
                input_name = mqtt_topic_iothub.get_input_name_from_topic(topic)
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
            super(IoTHubMQTTTranslationStage, self)._handle_pipeline_event(event)
