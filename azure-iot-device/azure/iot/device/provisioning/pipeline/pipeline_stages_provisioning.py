# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from azure.iot.device.common.pipeline import pipeline_ops_base, pipeline_thread
from azure.iot.device.common.pipeline.pipeline_stages_base import PipelineStage
from . import pipeline_ops_provisioning
from azure.iot.device import exceptions
from azure.iot.device.provisioning.pipeline import constant
from azure.iot.device.provisioning.models.registration_result import (
    RegistrationResult,
    RegistrationState,
)
import logging
import weakref
import json
import abc
from threading import Timer
from .constant import REGISTER, QUERY
from .mqtt_topic import get_optional_element

logger = logging.getLogger(__name__)


class UseSecurityClientStage(PipelineStage):
    """
    PipelineStage which extracts relevant SecurityClient values for a new
    SetProvisioningClientConnectionArgsOperation.

    All other operations are passed down.
    """

    @pipeline_thread.runs_on_pipeline_thread
    def _execute_op(self, op):
        if isinstance(op, pipeline_ops_provisioning.SetSymmetricKeySecurityClientOperation):

            security_client = op.security_client
            worker_op = op.spawn_worker_op(
                worker_op_type=pipeline_ops_provisioning.SetProvisioningClientConnectionArgsOperation,
                provisioning_host=security_client.provisioning_host,
                registration_id=security_client.registration_id,
                id_scope=security_client.id_scope,
                sas_token=security_client.get_current_sas_token(),
            )
            self.send_op_down(worker_op)

        elif isinstance(op, pipeline_ops_provisioning.SetX509SecurityClientOperation):
            security_client = op.security_client
            worker_op = op.spawn_worker_op(
                worker_op_type=pipeline_ops_provisioning.SetProvisioningClientConnectionArgsOperation,
                provisioning_host=security_client.provisioning_host,
                registration_id=security_client.registration_id,
                id_scope=security_client.id_scope,
                client_cert=security_client.get_x509_certificate(),
            )
            self.send_op_down(worker_op)

        else:
            self.send_op_down(op)


class CommonProvisioningStage(PipelineStage):
    @pipeline_thread.runs_on_pipeline_thread
    def _get_error(self, provisioning_op, prov_op_name, error):
        if error:
            return error
        elif 300 <= provisioning_op.status_code < 429:
            logger.error(
                "Received error with status code {status_code} for {prov_op_name} request operation".format(
                    prov_op_name=prov_op_name, status_code=provisioning_op.status_code
                )
            )
            logger.error("response body: {}".format(provisioning_op.response_body))
            return exceptions.ServiceError(
                "{prov_op_name} request returned a service error status code {status_code}".format(
                    prov_op_name=prov_op_name, status_code=provisioning_op.status_code
                )
            )
        else:
            return None

    @pipeline_thread.runs_on_pipeline_thread
    def _decode_response(self, provisioning_op):
        return json.loads(provisioning_op.response_body.decode("utf-8"))

    @pipeline_thread.runs_on_pipeline_thread
    def _get_registration_status(self, decoded_response):
        return get_optional_element(decoded_response, "status")

    @pipeline_thread.runs_on_pipeline_thread
    def _get_operation_id(self, decoded_response):
        return get_optional_element(decoded_response, "operationId")

    @pipeline_thread.runs_on_pipeline_thread
    def _form_complete_result(self, operation_id, decoded_response, status):
        """
        Create the registration result from the complete decoded json response for details regarding the registration process.
        """
        decoded_state = (get_optional_element(decoded_response, "registrationState"),)
        registration_state = None
        if decoded_state is not None:
            # Everything needs to be converted to string explicitly for python 2
            # as everything is by default a unicode character

            registration_state = RegistrationState(
                device_id=get_optional_element(decoded_state[0], "deviceId"),
                assigned_hub=get_optional_element(decoded_state[0], "assignedHub"),
                sub_status=get_optional_element(decoded_state[0], "substatus"),
                created_date_time=get_optional_element(decoded_state[0], "createdDateTimeUtc"),
                last_update_date_time=get_optional_element(
                    decoded_state[0], "lastUpdatedDateTimeUtc"
                ),
                etag=get_optional_element(decoded_state[0], "etag"),
            )

        registration_result = RegistrationResult(
            operation_id=operation_id, status=status, registration_state=registration_state
        )
        return registration_result


class RegistrationStage(CommonProvisioningStage):
    """
    This is the first stage that decides converts a registration request
    into a normal request and response operation.
    Upon the receipt of the response this stage decides whether
    to send another registration request or send a query request.
    Depending on the status and result of the response
    this stage may also complete the registration process.
    """

    @pipeline_thread.runs_on_pipeline_thread
    def _execute_op(self, op):
        if isinstance(op, pipeline_ops_provisioning.SendRegistrationRequestOperation):

            def on_registration_response(provisioning_op, error):

                logger.debug(
                    "{stage_name}({op_name}): Received response with status code {status_code} for SendRegistrationRequestOperation".format(
                        stage_name=self.name,
                        op_name=op.name,
                        status_code=provisioning_op.status_code,
                    )
                )

                # This could be an error that has been reported to this stage Or this
                # could be an error because the service responded with status code >=300
                error = self._get_error(provisioning_op, REGISTER, error=error)

                if not error:
                    success_status_code = provisioning_op.status_code
                    retry_interval = (
                        int(provisioning_op.retry_after, 10)
                        if provisioning_op.retry_after is not None
                        else constant.DEFAULT_POLLING_INTERVAL
                    )
                    decoded_response = self._decode_response(provisioning_op)
                    operation_id = self._get_operation_id(decoded_response)

                    # retry after scenario
                    if success_status_code >= 429:

                        self_weakref = weakref.ref(self)

                        @pipeline_thread.invoke_on_pipeline_thread_nowait
                        def do_retry_after():
                            this = self_weakref()
                            logger.info(
                                "{stage_name}({op_name}): retrying".format(
                                    stage_name=this.name, op_name=op.name
                                )
                            )
                            op.retry_after_timer.cancel()
                            op.retry_after_timer = None
                            op.completed = False
                            this._execute_op(op)

                        logger.warning(
                            "{stage_name}({op_name}): Op needs retry with interval {interval} because of {error}.  Setting timer.".format(
                                stage_name=self.name,
                                op_name=op.name,
                                interval=retry_interval,
                                error=error,
                            )
                        )

                        op.retry_after_timer = Timer(retry_interval, do_retry_after)
                        op.retry_after_timer.start()

                    # Service success scenario
                    else:
                        registration_status = self._get_registration_status(decoded_response)
                        if registration_status == "assigned" or registration_status == "failed":
                            # process complete response here
                            complete_registration_result = self._form_complete_result(
                                request_id=provisioning_op.request_id,
                                operation_id=operation_id,
                                decoded_response=decoded_response,
                                status=registration_status,
                            )
                            op.registration_result = complete_registration_result
                            if registration_status == "failed":
                                error = exceptions.ServiceError(
                                    "Query Status operation returned a 'failed' registration status  with a status code of {status_code}".format(
                                        status_code=success_status_code
                                    )
                                )
                            self.complete_op(op, error=error)
                        elif registration_status == "assigning":

                            query_worker_op = pipeline_ops_provisioning.SendQueryRequestOperation(
                                request_payload=" ", operation_id=operation_id, callback=op.callback
                            )

                            original_register_callback = op.callback

                            def copy_result_to_original_op(op, error):
                                logger.debug(
                                    "Copying registration result from Query Status Op to Registration Op"
                                )
                                op.registration_result = query_worker_op.registration_result
                                original_register_callback(op, error=error)

                            op.callback = copy_result_to_original_op
                            self.send_worker_op_down(worker_op=query_worker_op, op=op)
                        else:
                            error = exceptions.ServiceError(
                                "Registration Request encountered an invalid registration status {status} with a status code of {status_code}".format(
                                    status=registration_status, status_code=success_status_code
                                )
                            )
                            self.complete_op(op, error=error)

                else:
                    self.complete_op(op, error=error)

            registration_payload = DeviceRegistrationPayload(
                registration_id=op.registration_id, custom_payload=op.request_payload
            )
            self.send_op_down(
                pipeline_ops_base.RequestAndResponseOperation(
                    request_type=constant.REGISTER,
                    method="PUT",
                    resource_location="/",
                    request_body=registration_payload.get_json_string(),
                    callback=on_registration_response,
                )
            )

        else:
            self.send_op_down(op)


class PollingStatusStage(CommonProvisioningStage):
    """
    This stage is responsible for sending the query request once initial response
    is received from the registration response.
    Upon the receipt of the response this stage decides whether
    to send another query request or complete the procedure.
    """

    @pipeline_thread.runs_on_pipeline_thread
    def _execute_op(self, op):
        if isinstance(op, pipeline_ops_provisioning.SendQueryRequestOperation):

            def on_query_response(query_op, error):
                logger.debug(
                    "{stage_name}({op_name}): Received response with status code {status_code} for SendQueryRequestOperation with operation id {oper_id}".format(
                        stage_name=self.name,
                        op_name=op.name,
                        status_code=query_op.status_code,
                        oper_id=query_op.query_params["operation_id"],
                    )
                )

                # This could be an error that has been reported to this stage Or this
                # could be an error because the service responded with status code 300
                error = self._get_error(query_op, QUERY, error=error)

                if not error:
                    success_status_code = query_op.status_code
                    polling_interval = (
                        int(query_op.retry_after, 10)
                        if query_op.retry_after is not None
                        else constant.DEFAULT_POLLING_INTERVAL
                    )
                    decoded_response = self._decode_response(query_op)
                    operation_id = self._get_operation_id(decoded_response)
                    registration_status = self._get_registration_status(decoded_response)

                    # retry after or assigning scenario
                    if success_status_code >= 429 or registration_status == "assigning":

                        self_weakref = weakref.ref(self)

                        @pipeline_thread.invoke_on_pipeline_thread_nowait
                        def do_polling():
                            this = self_weakref()
                            logger.info(
                                "{stage_name}({op_name}): retrying".format(
                                    stage_name=this.name, op_name=op.name
                                )
                            )
                            op.polling_timer.cancel()
                            op.polling_timer = None
                            op.completed = False
                            this._execute_op(op)

                        logger.warning(
                            "{stage_name}({op_name}): Op needs retry with interval {interval} because of {error}. Setting timer.".format(
                                stage_name=self.name,
                                op_name=op.name,
                                interval=polling_interval,
                                error=error,
                            )
                        )

                        op.polling_timer = Timer(polling_interval, do_polling)
                        op.polling_timer.start()

                    # Service success scenario
                    else:
                        registration_status = self._get_registration_status(decoded_response)
                        if registration_status == "assigned" or registration_status == "failed":
                            # process complete response here
                            complete_registration_result = self._form_complete_result(
                                operation_id=operation_id,
                                decoded_response=decoded_response,
                                status=registration_status,
                            )
                            op.registration_result = complete_registration_result

                            if registration_status == "failed":
                                error = exceptions.ServiceError(
                                    "Query Status operation returned a 'failed' registration status  with a status code of {status_code}".format(
                                        status_code=success_status_code
                                    )
                                )
                        else:
                            error = exceptions.ServiceError(
                                "Query Status Operation encountered an invalid registration status {status} with a status code of {status_code}".format(
                                    status=registration_status, status_code=success_status_code
                                )
                            )

                        self.complete_op(op, error=error)

                else:
                    self.complete_op(op, error=error)

            self.send_op_down(
                pipeline_ops_base.RequestAndResponseOperation(
                    request_type=constant.QUERY,
                    method="GET",
                    resource_location="/",
                    query_params={"operation_id": op.operation_id},
                    request_body=op.request_payload,
                    callback=on_query_response,
                )
            )

        else:
            self.send_op_down(op)


class DeviceRegistrationPayload(object):
    """
    The class representing the payload that needs to be sent to the service.
    """

    def __init__(self, registration_id, custom_payload=None):
        # This is not a convention to name variables in python but the
        # DPS service spec needs the name to be exact for it to work
        self.registrationId = registration_id
        self.payload = custom_payload

    def get_json_string(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)
