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


class SetEdgeHubConnectionArgsOperation(PipelineOperation):
    """
    A PipelineOperation object which contains connection arguments which were retrieved from an authorization provider,
    likely by a pipeline stage which handles the SetAuthProviderOperation operation.

    This operation is in the group of EdgeHub operations because the arguments which it accepts are very specific to
    EdgeHub connections and would not apply to other types of client connections (such as a DPS client).
    """

    def __init__(
        self,
        device_id,
        hostname,
        callback,
        module_id=None,
        gateway_hostname=None,
        ca_cert=None,
        client_cert=None,
        sas_token=None,
    ):
        """
        Initializer for setEdgeHubConnectionArgsOperation objects.

        :param str device_id: The device id for the device that we are connecting.
        :param str hostname: The hostname of the iothub service we are connecting to.
        :param str module_id: (optional) If we are connecting as a module, this contains the module id
          for the module we are connecting.
        :param str gateway_hostname: (optional) If we are going through a gateway host, this is the
          hostname for the gateway
        :param str ca_cert: (Optional) The CA certificate to use if the server that we're going to
          connect to uses server-side TLS
        :param X509 client_cert: (Optional) The x509 object containing a client certificate and key used to connect
          to the service
        :param str sas_token: The token string which will be used to authenticate with the service
        :param Function callback: The function that gets called when this operation is complete or has failed.
         The callback function must accept A PipelineOperation object which indicates the specific operation which
         has completed or failed.
        """
        super(SetEdgeHubConnectionArgsOperation, self).__init__(callback=callback)
        self.device_id = device_id
        self.module_id = module_id
        self.hostname = hostname
        self.gateway_hostname = gateway_hostname
        self.ca_cert = ca_cert
        self.client_cert = client_cert
        self.sas_token = sas_token


class MethodInvokeOperation(PipelineOperation):
    """
    A PipleineOperation object which contains arguments used to send a method invoke to an IoTHub or EdgeHub server.

    This operation is in the group of EdgeHub operations because it is very specific to the EdgeHub client.
    """

    def __init__(self, device_id, module_id, method_params, callback):
        """
        Initializer for MethodInvokeOperation objects.

        :param method_response: The method response to be sent to IoTHub/EdgeHub
        :type method_response: MethodResponse
        :param callback: The function that gets called when this operation is complete or has failed.
         The callback function must accept a PipelineOperation object which indicates the specific operation has which
         has completed or failed.
        :type callback: Function/callable
        """
        super(MethodInvokeOperation, self).__init__(callback=callback)
        self.device_id = device_id
        self.module_id = module_id
        self.method_params = method_params
