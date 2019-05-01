# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from .pipeline_ops_base import PipelineOperation


class SetAuthProvider(PipelineOperation):
    """
    A PipelineOperation object which tells the pipeline to "disable" a particular feature.

    A "feature" is just a string which represents some set of functionality that needs to be disabled, such as "C2D" or "Twin".

    This object has no notion of what it means to "disable" a feature.  That knowledge is handled by stages in the pipeline which might convert
    this operation to a more specific operation (such as an MQTT unsubscribe operation with a specific topic name).

    This operation is in the group of "Iot" operations because disconnecting is a common operation that many clients might need to do.

    Even though this is an "Iot" operation, it will most likely be handled by a more specific stage (such as an IotHub or Mqtt stage).
    """

    def __init__(self, auth_provider, callback=None):
        """
        Initializer for SetAuthProvider objects.

        :param Function callback: The function that gets called when this operation is complete or has failed.
          The callback function must accept A PipelineOperation object which indicates the specific operation which
          has completed or failed.
        """
        super(SetAuthProvider, self).__init__(callback=callback)
        self.auth_provider = auth_provider


class SetAuthProviderArgs(PipelineOperation):
    """
    A PipelineOperation object which contains connection arguments which were retrieved from an authorization provider,
    likely by a pipeline stage which handles the SetAuthProvider operation.

    This operation is in the group of IoTHub operations because the arguments which it accepts are very specific to
    IotHub connections and would not apply to other types of client connections (such as a DPS client).
    """

    def __init__(
        self, device_id, module_id, hostname, gateway_hostname=None, ca_cert=None, callback=None
    ):
        """
        Initializer for SetAuthProviderArgs objects.

        :param Function callback: The function that gets called when this operation is complete or has failed.
          The callback function must accept A PipelineOperation object which indicates the specific operation which
          has completed or failed.
        """
        super(SetAuthProviderArgs, self).__init__(callback=callback)
        self.device_id = device_id
        self.module_id = module_id
        self.hostname = hostname
        self.gateway_hostname = gateway_hostname
        self.ca_cert = ca_cert


class SendTelemetry(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to send a telemetry message to an IotHub or EdegHub server.

    This operation is in the group of IoTHub operations because it is very specific to the IotHub client
    """

    def __init__(self, message, callback=None):
        """
        Initializer for SendTelemetry objects.

        :param Function callback: The function that gets called when this operation is complete or has failed.
          The callback function must accept A PipelineOperation object which indicates the specific operation which
          has completed or failed.
        """
        super(SendTelemetry, self).__init__(callback=callback)
        self.message = message
        self.needs_connection = True


class SendOutputEvent(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to send an output message to an EdgeHub server.

    This operation is in the group of IoTHub operations because it is very specific to the IotHub client
    """

    def __init__(self, message, callback=None):
        """
        Initializer for SendOutputEvent objects.

        :param Function callback: The function that gets called when this operation is complete or has failed.
          The callback function must accept A PipelineOperation object which indicates the specific operation which
          has completed or failed.
        """
        super(SendOutputEvent, self).__init__(callback=callback)
        self.message = message
        self.needs_connection = True
