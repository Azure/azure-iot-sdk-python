# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import uuid
import json
import traceback
from threading import Timer
from transitions import Machine
from azure.iot.device.provisioning.pipeline import constant
import six.moves.urllib as urllib
from .request_response_provider import RequestResponseProvider
from azure.iot.device.provisioning.models.registration_result import (
    RegistrationResult,
    RegistrationState,
)
from .registration_query_status_result import RegistrationQueryStatusResult


logger = logging.getLogger(__name__)

POS_STATUS_CODE_IN_TOPIC = 3
POS_QUERY_PARAM_PORTION = 2


class PollingMachine(object):
    """
    Class that is responsible for sending the initial registration request and polling the
    registration process for constant updates.
    """

    def __init__(self, provisioning_pipeline):
        """
        :param provisioning_pipeline: The pipeline for provisioning.
        """
        self._polling_timer = None
        self._query_timer = None

        self._register_callback = None
        self._cancel_callback = None

        self._registration_error = None
        self._registration_result = None

        self._operations = {}

        self._request_response_provider = RequestResponseProvider(provisioning_pipeline)
        self._payload = None

        states = [
            "disconnected",
            "initializing",
            "registering",
            "waiting_to_poll",
            "polling",
            "completed",
            "error",
            "cancelling",
        ]

        transitions = [
            {
                "trigger": "_trig_register",
                "source": "disconnected",
                "before": "_initialize_register",
                "dest": "initializing",
            },
            {
                "trigger": "_trig_register",
                "source": "error",
                "before": "_initialize_register",
                "dest": "initializing",
            },
            {"trigger": "_trig_register", "source": "registering", "dest": None},
            {
                "trigger": "_trig_send_register_request",
                "source": "initializing",
                "before": "_send_register_request",
                "dest": "registering",
            },
            {
                "trigger": "_trig_send_register_request",
                "source": "waiting_to_poll",
                "before": "_send_register_request",
                "dest": "registering",
            },
            {
                "trigger": "_trig_wait",
                "source": "registering",
                "dest": "waiting_to_poll",
                "after": "_wait_for_interval",
            },
            {"trigger": "_trig_wait", "source": "cancelling", "dest": None},
            {
                "trigger": "_trig_wait",
                "source": "polling",
                "dest": "waiting_to_poll",
                "after": "_wait_for_interval",
            },
            {
                "trigger": "_trig_poll",
                "source": "waiting_to_poll",
                "dest": "polling",
                "after": "_query_operation_status",
            },
            {"trigger": "_trig_poll", "source": "cancelling", "dest": None},
            {
                "trigger": "_trig_complete",
                "source": ["registering", "waiting_to_poll", "polling"],
                "dest": "completed",
                "after": "_call_complete",
            },
            {
                "trigger": "_trig_error",
                "source": ["registering", "waiting_to_poll", "polling"],
                "dest": "error",
                "after": "_call_error",
            },
            {"trigger": "_trig_error", "source": "cancelling", "dest": None},
            {
                "trigger": "_trig_cancel",
                "source": ["disconnected", "completed"],
                "dest": None,
                "after": "_inform_no_process",
            },
            {
                "trigger": "_trig_cancel",
                "source": ["initializing", "registering", "waiting_to_poll", "polling"],
                "dest": "cancelling",
                "after": "_call_cancel",
            },
        ]

        def _on_transition_complete(event_data):
            if not event_data.transition:
                dest = "[no transition]"
            else:
                dest = event_data.transition.dest
            logger.debug(
                "Transition complete.  Trigger={}, Src={}, Dest={}, result={}, error{}".format(
                    event_data.event.name,
                    event_data.transition.source,
                    dest,
                    str(event_data.result),
                    str(event_data.error),
                )
            )

        self._state_machine = Machine(
            model=self,
            states=states,
            transitions=transitions,
            initial="disconnected",
            send_event=True,  # Use event_data structures to pass transition arguments
            finalize_event=_on_transition_complete,
            queued=True,
        )

    def register(self, payload=None, callback=None):
        """
        Register the device with the provisioning service.
        :param:Callback to be called upon finishing the registration process
        """
        logger.info("register called from polling machine")
        self._register_callback = callback
        self._payload = payload
        self._trig_register()

    def cancel(self, callback=None):
        """
        Cancels the current registration process of the device.
        :param:Callback to be called upon finishing the cancellation process
        """
        logger.info("cancel called from polling machine")
        self._cancel_callback = callback
        self._trig_cancel()

    def _initialize_register(self, event_data):
        logger.info("Initializing the registration process.")
        self._request_response_provider.enable_responses(callback=self._on_subscribe_completed)

    def _send_register_request(self, event_data):
        """
        Send the registration request.
        """
        logger.info("Sending registration request")
        self._set_query_timer()

        request_id = str(uuid.uuid4())

        self._operations[request_id] = constant.PUBLISH_TOPIC_REGISTRATION.format(request_id)
        self._request_response_provider.send_request(
            request_id=request_id,
            request_payload=self._payload,
            operation_id=None,
            callback_on_response=self._on_register_response_received,
        )

    def _query_operation_status(self, event_data):
        """
        Poll the service for operation status.
        """
        logger.info("Querying operation status from polling machine")
        self._set_query_timer()

        request_id = str(uuid.uuid4())
        result = event_data.args[0].args[0]

        operation_id = result.operation_id
        self._operations[request_id] = constant.PUBLISH_TOPIC_QUERYING.format(
            request_id, operation_id
        )
        self._request_response_provider.send_request(
            request_id=request_id,
            request_payload=" ",
            operation_id=operation_id,
            callback_on_response=self._on_query_response_received,
        )

    def _on_register_response_received(self, request_id, status_code, key_values_dict, response):
        """
        The function to call in case of a response from a registration request.
        :param request_id: The id of the original register request.
        :param status_code: The status code in the response.
        :param key_values_dict: The dictionary containing the query parameters of the returned topic.
        :param response: The complete response from the service.
        """
        self._query_timer.cancel()

        retry_after = (
            None if "retry-after" not in key_values_dict else str(key_values_dict["retry-after"][0])
        )
        intermediate_registration_result = RegistrationQueryStatusResult(request_id, retry_after)

        if int(status_code, 10) >= 429:
            del self._operations[request_id]
            self._trig_wait(intermediate_registration_result)
        elif int(status_code, 10) >= 300:  # pure failure
            self._registration_error = ValueError("Incoming message failure")
            self._trig_error()
        else:  # successful case, transition into complete or poll status
            self._process_successful_response(request_id, retry_after, response)

    def _on_query_response_received(self, request_id, status_code, key_values_dict, response):
        """
        The function to call in case of a response from a polling/query request.
        :param request_id: The id of the original query request.
        :param status_code: The status code in the response.
        :param key_values_dict: The dictionary containing the query parameters of the returned topic.
        :param response: The complete response from the service.
        """
        self._query_timer.cancel()
        self._polling_timer.cancel()

        retry_after = (
            None if "retry-after" not in key_values_dict else str(key_values_dict["retry-after"][0])
        )
        intermediate_registration_result = RegistrationQueryStatusResult(request_id, retry_after)

        if int(status_code, 10) >= 429:
            if request_id in self._operations:
                publish_query_topic = self._operations[request_id]
                del self._operations[request_id]
                topic_parts = publish_query_topic.split("$")
                key_values_publish_topic = urllib.parse.parse_qs(
                    topic_parts[POS_QUERY_PARAM_PORTION]
                )
                operation_id = key_values_publish_topic["operationId"][0]
                intermediate_registration_result.operation_id = operation_id
                self._trig_wait(intermediate_registration_result)
            else:
                self._registration_error = ValueError("This request was never sent")
                self._trig_error()
        elif int(status_code, 10) >= 300:  # pure failure
            self._registration_error = ValueError("Incoming message failure")
            self._trig_error()
        else:  # successful status code case, transition into complete or another poll status
            self._process_successful_response(request_id, retry_after, response)

    def _process_successful_response(self, request_id, retry_after, response):
        """
        Fucntion to call in case of 200 response from the service
        :param request_id: The request id
        :param retry_after: The time after which to try again.
        :param response: The complete response
        """
        del self._operations[request_id]
        successful_result = self._decode_json_response(request_id, retry_after, response)
        if successful_result.status == "assigning":
            self._trig_wait(successful_result)
        elif successful_result.status == "assigned" or successful_result.status == "failed":
            complete_registration_result = self._decode_complete_json_response(
                successful_result, response
            )
            self._registration_result = complete_registration_result
            self._trig_complete()
        else:
            self._registration_error = ValueError("Other types of failure have occurred.", response)
            self._trig_error()

    def _inform_no_process(self, event_data):
        raise RuntimeError("There is no registration process to cancel.")

    def _call_cancel(self, event_data):
        """
        Completes the cancellation process
        """
        logger.info("Cancel called from polling machine")
        self._clear_timers()
        self._request_response_provider.disconnect(callback=self._on_disconnect_completed_cancel)

    def _call_error(self, event_data):
        logger.info("Failed register from polling machine")

        self._clear_timers()
        self._request_response_provider.disconnect(callback=self._on_disconnect_completed_error)

    def _call_complete(self, event_data):
        logger.info("Complete register from polling machine")
        self._clear_timers()
        self._request_response_provider.disconnect(callback=self._on_disconnect_completed_register)

    def _clear_timers(self):
        """
        Clears all the timers and disconnects from the service
        """
        if self._query_timer is not None:
            self._query_timer.cancel()
        if self._polling_timer is not None:
            self._polling_timer.cancel()

    def _set_query_timer(self):
        def time_up_query():
            logger.error("Time is up for query timer")
            self._query_timer.cancel()
            # TimeoutError not defined in python 2
            self._registration_error = ValueError("Time is up for query timer")
            self._trig_error()

        self._query_timer = Timer(constant.DEFAULT_TIMEOUT_INTERVAL, time_up_query)
        self._query_timer.start()

    def _wait_for_interval(self, event_data):
        def time_up_polling():
            self._polling_timer.cancel()
            logger.debug("Done waiting for polling interval of {} secs".format(polling_interval))
            if result.operation_id is None:
                self._trig_send_register_request(event_data)
            else:
                self._trig_poll(event_data)

        result = event_data.args[0]
        polling_interval = (
            constant.DEFAULT_POLLING_INTERVAL
            if result.retry_after is None
            else int(result.retry_after, 10)
        )

        self._polling_timer = Timer(polling_interval, time_up_polling)
        logger.debug("Waiting for " + str(constant.DEFAULT_POLLING_INTERVAL) + " secs")
        self._polling_timer.start()  # This is waiting for that polling interval

    def _decode_complete_json_response(self, query_result, response):
        """
        Decodes the complete json response for details regarding the registration process.
        :param query_result: The partially formed result.
        :param response: The complete response from the service
        """
        decoded_result = json.loads(response)

        decoded_state = (
            None
            if "registrationState" not in decoded_result
            else decoded_result["registrationState"]
        )
        registration_state = None
        if decoded_state is not None:
            # Everything needs to be converted to string explicitly for python 2
            # as everything is by default a unicode character
            registration_state = RegistrationState(
                None if "deviceId" not in decoded_state else str(decoded_state["deviceId"]),
                None if "assignedHub" not in decoded_state else str(decoded_state["assignedHub"]),
                None if "substatus" not in decoded_state else str(decoded_state["substatus"]),
                None
                if "createdDateTimeUtc" not in decoded_state
                else str(decoded_state["createdDateTimeUtc"]),
                None
                if "lastUpdatedDateTimeUtc" not in decoded_state
                else str(decoded_state["lastUpdatedDateTimeUtc"]),
                None if "etag" not in decoded_state else str(decoded_state["etag"]),
                None if "payload" not in decoded_state else str(decoded_state["payload"]),
            )

        registration_result = RegistrationResult(
            request_id=query_result.request_id,
            operation_id=query_result.operation_id,
            status=query_result.status,
            registration_state=registration_state,
        )
        return registration_result

    def _decode_json_response(self, request_id, retry_after, response):
        """
        Decodes the json response for operation id and status
        :param request_id: The request id.
        :param retry_after: The time in secs after which to retry.
        :param response: The complete response from the service.
        """
        decoded_result = json.loads(response)

        operation_id = (
            None if "operationId" not in decoded_result else str(decoded_result["operationId"])
        )
        status = None if "status" not in decoded_result else str(decoded_result["status"])

        return RegistrationQueryStatusResult(request_id, retry_after, operation_id, status)

    def _on_disconnect_completed_error(self):
        logger.info("on_disconnect_completed for Device Provisioning Service")
        callback = self._register_callback
        if callback:
            self._register_callback = None
            try:
                callback(error=self._registration_error)
            except Exception:
                logger.error("Unexpected error calling callback supplied to register")
                logger.error(traceback.format_exc())

    def _on_disconnect_completed_cancel(self):
        logger.info("on_disconnect_completed after cancelling current Device Provisioning Service")
        callback = self._cancel_callback

        if callback:
            self._cancel_callback = None
            callback()

    def _on_disconnect_completed_register(self):
        logger.info("on_disconnect_completed after registration to Device Provisioning Service")
        callback = self._register_callback

        if callback:
            self._register_callback = None
            try:
                callback(result=self._registration_result)
            except Exception:
                logger.error("Unexpected error calling callback supplied to register")
                logger.error(traceback.format_exc())

    def _on_subscribe_completed(self):
        logger.debug("on_subscribe_completed for Device Provisioning Service")
        self._trig_send_register_request()
