# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from azure.iot.device.common.pipeline import PipelineOperation


# TODO: Combine SetAuthProviderOperation and SetX509AuthProviderOperation once
# auth provider is reduced to a simple vector
class SetX509AuthProviderOperation(PipelineOperation):
    """
    A PipelineOperation object which tells the pipeline to use a particular X509 authorization provider.
    Some pipeline stage is expected to extract arguments out of the auth provider and pass them
    on so an even lower stage can use those arguments to connect.

    This operation is in the group of IoTHub operations because authorization providers are currently
    very IoTHub-specific
    """

    def __init__(self, auth_provider, callback):
        """
        Initializer for SetAuthProviderOperation objects.

        :param object auth_provider: The X509 authorization provider object to use to retrieve connection parameters
          which can be used to connect to the service.
        :param Function callback: The function that gets called when this operation is complete or has failed.
          The callback function must accept A PipelineOperation object which indicates the specific operation which
          has completed or failed.
        """
        super(SetX509AuthProviderOperation, self).__init__(callback=callback)
        self.auth_provider = auth_provider


class SetAuthProviderOperation(PipelineOperation):
    """
    A PipelineOperation object which tells the pipeline to use a particular authorization provider.
    Some pipeline stage is expected to extract arguments out of the auth provider and pass them
    on so an even lower stage can use those arguments to connect.

    This operation is in the group of IoTHub operations because autorization providers are currently
    very IoTHub-specific
    """

    def __init__(self, auth_provider, callback):
        """
        Initializer for SetAuthProviderOperation objects.

        :param object auth_provider: The authorization provider object to use to retrieve connection parameters
          which can be used to connect to the service.
        :param Function callback: The function that gets called when this operation is complete or has failed.
         The callback function must accept A PipelineOperation object which indicates the specific operation which
         has completed or failed.
        """
        super(SetAuthProviderOperation, self).__init__(callback=callback)
        self.auth_provider = auth_provider


class SetIoTHubConnectionArgsOperation(PipelineOperation):
    """
    A PipelineOperation object which contains connection arguments which were retrieved from an authorization provider,
    likely by a pipeline stage which handles the SetAuthProviderOperation operation.

    This operation is in the group of IoTHub operations because the arguments which it accepts are very specific to
    IoTHub connections and would not apply to other types of client connections (such as a DPS client).
    """

    def __init__(
        self,
        device_id,
        hostname,
        callback,
        module_id=None,
        gateway_hostname=None,
        server_verification_cert=None,
        client_cert=None,
        sas_token=None,
    ):
        """
        Initializer for SetIoTHubConnectionArgsOperation objects.

        :param str device_id: The device id for the device that we are connecting.
        :param str hostname: The hostname of the iothub service we are connecting to.
        :param str module_id: (optional) If we are connecting as a module, this contains the module id
          for the module we are connecting.
        :param str gateway_hostname: (optional) If we are going through a gateway host, this is the
          hostname for the gateway
        :param str server_verification_cert: (Optional) The full path to the the server verification certificate to use
          if the server that we're going to connect to uses server-side TLS
        :param X509 client_cert: (Optional) The x509 object containing a client certificate and key used to connect
          to the service
        :param str sas_token: The token string which will be used to authenticate with the service
        :param Function callback: The function that gets called when this operation is complete or has failed.
         The callback function must accept A PipelineOperation object which indicates the specific operation which
         has completed or failed.
        """
        super(SetIoTHubConnectionArgsOperation, self).__init__(callback=callback)
        self.device_id = device_id
        self.module_id = module_id
        self.hostname = hostname
        self.gateway_hostname = gateway_hostname
        self.server_verification_cert = server_verification_cert
        self.client_cert = client_cert
        self.sas_token = sas_token


class SendD2CMessageOperation(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to send a telemetry message to an IoTHub or EdegHub server.

    This operation is in the group of IoTHub operations because it is very specific to the IoTHub client
    """

    def __init__(self, message, callback):
        """
        Initializer for SendD2CMessageOperation objects.

        :param Message message: The message that we're sending to the service
        :param Function callback: The function that gets called when this operation is complete or has failed.
         The callback function must accept A PipelineOperation object which indicates the specific operation which
         has completed or failed.
        """
        super(SendD2CMessageOperation, self).__init__(callback=callback)
        self.message = message


class SendOutputEventOperation(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to send an output message to an EdgeHub server.

    This operation is in the group of IoTHub operations because it is very specific to the IoTHub client
    """

    def __init__(self, message, callback):
        """
        Initializer for SendOutputEventOperation objects.

        :param Message message: The output message that we're sending to the service. The name of the output is
          expected to be stored in the output_name attribute of this object
        :param Function callback: The function that gets called when this operation is complete or has failed.
         The callback function must accept A PipelineOperation object which indicates the specific operation which
         has completed or failed.
        """
        super(SendOutputEventOperation, self).__init__(callback=callback)
        self.message = message


class SendMethodResponseOperation(PipelineOperation):
    """
    A PipleineOperation object which contains arguments used to send a method response to an IoTHub or EdgeHub server.

    This operation is in the group of IoTHub operations because it is very specific to the IoTHub client.
    """

    def __init__(self, method_response, callback):
        """
        Initializer for SendMethodResponseOperation objects.

        :param method_response: The method response to be sent to IoTHub/EdgeHub
        :type method_response: MethodResponse
        :param callback: The function that gets called when this operation is complete or has failed.
         The callback function must accept a PipelineOperation object which indicates the specific operation has which
         has completed or failed.
        :type callback: Function/callable
        """
        super(SendMethodResponseOperation, self).__init__(callback=callback)
        self.method_response = method_response


class GetTwinOperation(PipelineOperation):
    """
    A PipelineOperation object which represents a request to get a device twin or a module twin from an Azure
    IoT Hub or Azure Iot Edge Hub service.

    :ivar twin: Upon completion, this contains the twin which was retrieved from the service.
    :type twin: Twin
    """

    def __init__(self, callback):
        """
        Initializer for GetTwinOperation objects.
        """
        super(GetTwinOperation, self).__init__(callback=callback)
        self.twin = None


class PatchTwinReportedPropertiesOperation(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to send a reported properties patch to the Azure
    IoT Hub or Azure IoT Edge Hub service.
    """

    def __init__(self, patch, callback):
        """
        Initializer for PatchTwinReportedPropertiesOperation object

        :param patch: The reported properties patch to send to the service.
        :type patch: dict, str, int, float, bool, or None (JSON compatible values)
        """
        super(PatchTwinReportedPropertiesOperation, self).__init__(callback=callback)
        self.patch = patch
