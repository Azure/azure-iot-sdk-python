# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import json
import logging
from azure.iot.device.common.pipeline import (
    pipeline_events_base,
    pipeline_ops_base,
    PipelineStage,
    pipeline_thread,
)
from azure.iot.device import exceptions
from azure.iot.device.common import handle_exceptions
from azure.iot.device.common.callable_weak_method import CallableWeakMethod
from . import pipeline_events_iothub, pipeline_ops_iothub
from . import constant

logger = logging.getLogger(__name__)


class EnsureDesiredPropertiesStage(PipelineStage):
    """
    Pipeline stage Responsible for making sure that desired properties are always kept up to date.
    It does this by sending diwn a GetTwinOperation after a connection is reestablished, and, if
    the desired properties have changed since the last time a patch was received, it will send up
    an artificial patch event to send those updated properties to the app.
    """

    def __init__(self):
        self.last_version_seen = None
        self.pending_get_request = None
        super(EnsureDesiredPropertiesStage, self).__init__()

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        if isinstance(op, pipeline_ops_base.EnableFeatureOperation):
            # If we're enabling twin patches, we set last_version_seen to -1
            # as a way of enabling this functionality.  If the ConnectedEvent handler
            # sees this -1, it will send a GetTwinOperation to refresh desired properties.

            if op.feature_name == constant.TWIN_PATCHES:
                logger.info(
                    "{}: enabling twin patches.  setting last_version_seen".format(self.name)
                )
                self.last_version_seen = -1
        self.send_op_down(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _ensure_get_op(self):
        """
        Function which makes sure we have a GetTwin operation in progress.  If we've
        already sent one down and we're waiting for it to return, we don't want to send
        a new one down.  This is because layers below us (especially CoordinateRequestAndResponseStage)
        will do everything they can to ensure we get a response on the already-pending
        GetTwinOperation.
        """
        if not self.pending_get_request:
            logger.info("{}: sending twin GET to ensure freshness".format(self.name))
            self.pending_get_request = pipeline_ops_iothub.GetTwinOperation(
                callback=CallableWeakMethod(self, "_on_get_twin_complete")
            )
            self.send_op_down(self.pending_get_request)
        else:
            logger.info(
                "{}: Outstanding twin GET already exists.  Not sending anything".format(self.name)
            )

    @pipeline_thread.runs_on_pipeline_thread
    def _on_get_twin_complete(self, op, error):
        """
        Function that gets called when a GetTwinOperation _that_we_initiated_ is complete.
        This is where we compare $version values and decide if we want to create an artificial
        TwinDesiredPropertiesPatchEvent or not.
        """

        logger.info("{}: _on_twin_get_complete".format(self.name))
        self.pending_get_request = None
        if error:
            # If the GetTwinOperation failed, we blindly try again.  We run the risk of
            # repeating this forever and might need to add logic to "give up" after some
            # number of failures, but we don't have any real reason to add that just yet.

            logger.info("{}: Twin GET failed with error {}.  Resubmitting.".format(self, error))
            self._ensure_get_op()
        else:
            logger.info("{} Twin GET response received.  Checking versions".format(self))
            new_version = op.twin["desired"]["$version"]
            logger.info(
                "{}: old version = {}, new version = {}".format(
                    self.name, self.last_version_seen, new_version
                )
            )
            if self.last_version_seen != new_version:
                # The twin we received has different (presumably newer) desired properties.
                # Make an artificial patch and send it up

                logger.info("{}: Version changed.  Sending up new patch event".format(self.name))
                self.last_version_seen = new_version
                self.send_event_up(
                    pipeline_events_iothub.TwinDesiredPropertiesPatchEvent(op.twin["desired"])
                )

    @pipeline_thread.runs_on_pipeline_thread
    def _handle_pipeline_event(self, event):
        if isinstance(event, pipeline_events_iothub.TwinDesiredPropertiesPatchEvent):
            # remember the $version when we get a patch.
            version = event.patch["$version"]
            logger.info(
                "{}: Desired patch received.  Saving $version={}".format(self.name, version)
            )
            self.last_version_seen = version
        elif isinstance(event, pipeline_events_base.ConnectedEvent):
            # If last_version_seen is truthy, that means we've seen desired property patches
            # before (or we've enabled them at least).  If this is the case, get the twin to
            # see if the desired props have been updated.
            if self.last_version_seen:
                logger.info("{}: Reconnected.  Getting twin")
                self._ensure_get_op()
        self.send_event_up(event)


class TwinRequestResponseStage(PipelineStage):
    """
    PipelineStage which handles twin operations. In particular, it converts twin GET and PATCH
    operations into RequestAndResponseOperation operations.  This is done at the IoTHub level because
    there is nothing protocol-specific about this code.  The protocol-specific implementation
    for twin requests and responses is handled inside IoTHubMQTTTranslationStage, when it converts
    the RequestOperation to a protocol-specific send operation and when it converts the
    protocol-specific receive event into an ResponseEvent event.
    """

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        def map_twin_error(error, twin_op):
            if error:
                return error
            elif twin_op.status_code >= 300:
                # TODO map error codes to correct exceptions
                logger.error("Error {} received from twin operation".format(twin_op.status_code))
                logger.error("response body: {}".format(twin_op.response_body))
                return exceptions.ServiceError(
                    "twin operation returned status {}".format(twin_op.status_code)
                )

        if isinstance(op, pipeline_ops_iothub.GetTwinOperation):

            # Alias to avoid overload within the callback below
            # CT-TODO: remove the need for this with better callback semantics
            op_waiting_for_response = op

            def on_twin_response(op, error):
                logger.debug("{}({}): Got response for GetTwinOperation".format(self.name, op.name))
                error = map_twin_error(error=error, twin_op=op)
                if not error:
                    op_waiting_for_response.twin = json.loads(op.response_body.decode("utf-8"))
                op_waiting_for_response.complete(error=error)

            self.send_op_down(
                pipeline_ops_base.RequestAndResponseOperation(
                    request_type=constant.TWIN,
                    method="GET",
                    resource_location="/",
                    request_body=" ",
                    callback=on_twin_response,
                )
            )

        elif isinstance(op, pipeline_ops_iothub.PatchTwinReportedPropertiesOperation):

            # Alias to avoid overload within the callback below
            # CT-TODO: remove the need for this with better callback semantics
            op_waiting_for_response = op

            def on_twin_response(op, error):
                logger.debug(
                    "{}({}): Got response for PatchTwinReportedPropertiesOperation operation".format(
                        self.name, op.name
                    )
                )
                error = map_twin_error(error=error, twin_op=op)
                op_waiting_for_response.complete(error=error)

            logger.debug(
                "{}({}): Sending reported properties patch: {}".format(self.name, op.name, op.patch)
            )

            self.send_op_down(
                pipeline_ops_base.RequestAndResponseOperation(
                    request_type=constant.TWIN,
                    method="PATCH",
                    resource_location="/properties/reported/",
                    request_body=json.dumps(op.patch),
                    callback=on_twin_response,
                )
            )

        else:
            super(TwinRequestResponseStage, self)._run_op(op)
