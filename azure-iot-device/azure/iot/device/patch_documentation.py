# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module provides hard coded patches used to modify items from the libraries.
Currently we have to do like this so that we don't use exec anywhere"""


def execute_patch_for_sync():
    from azure.iot.device.iothub.sync_clients import IoTHubDeviceClient as IoTHubDeviceClient

    def connect(self):
        return super(IoTHubDeviceClient, self).connect()

    connect.__doc__ = IoTHubDeviceClient.connect.__doc__
    setattr(IoTHubDeviceClient, "connect", connect)

    def disconnect(self):
        return super(IoTHubDeviceClient, self).disconnect()

    disconnect.__doc__ = IoTHubDeviceClient.disconnect.__doc__
    setattr(IoTHubDeviceClient, "disconnect", disconnect)

    def get_twin(self):
        return super(IoTHubDeviceClient, self).get_twin()

    get_twin.__doc__ = IoTHubDeviceClient.get_twin.__doc__
    setattr(IoTHubDeviceClient, "get_twin", get_twin)

    def patch_twin_reported_properties(self, reported_properties_patch):
        return super(IoTHubDeviceClient, self).patch_twin_reported_properties(
            reported_properties_patch
        )

    patch_twin_reported_properties.__doc__ = (
        IoTHubDeviceClient.patch_twin_reported_properties.__doc__
    )
    setattr(IoTHubDeviceClient, "patch_twin_reported_properties", patch_twin_reported_properties)

    def receive_method_request(self, method_name=None, block=True, timeout=None):
        return super(IoTHubDeviceClient, self).receive_method_request(method_name, block, timeout)

    receive_method_request.__doc__ = IoTHubDeviceClient.receive_method_request.__doc__
    setattr(IoTHubDeviceClient, "receive_method_request", receive_method_request)

    def receive_twin_desired_properties_patch(self, block=True, timeout=None):
        return super(IoTHubDeviceClient, self).receive_twin_desired_properties_patch(block, timeout)

    receive_twin_desired_properties_patch.__doc__ = (
        IoTHubDeviceClient.receive_twin_desired_properties_patch.__doc__
    )
    setattr(
        IoTHubDeviceClient,
        "receive_twin_desired_properties_patch",
        receive_twin_desired_properties_patch,
    )

    def send_message(self, message):
        return super(IoTHubDeviceClient, self).send_message(message)

    send_message.__doc__ = IoTHubDeviceClient.send_message.__doc__
    setattr(IoTHubDeviceClient, "send_message", send_message)

    def send_method_response(self, method_response):
        return super(IoTHubDeviceClient, self).send_method_response(method_response)

    send_method_response.__doc__ = IoTHubDeviceClient.send_method_response.__doc__
    setattr(IoTHubDeviceClient, "send_method_response", send_method_response)

    def create_from_connection_string(cls, connection_string, **kwargs):
        return super(IoTHubDeviceClient, cls).create_from_connection_string(
            connection_string, **kwargs
        )

    create_from_connection_string.__doc__ = IoTHubDeviceClient.create_from_connection_string.__doc__
    setattr(
        IoTHubDeviceClient,
        "create_from_connection_string",
        classmethod(create_from_connection_string),
    )

    def create_from_symmetric_key(cls, symmetric_key, hostname, device_id, **kwargs):
        return super(IoTHubDeviceClient, cls).create_from_symmetric_key(
            symmetric_key, hostname, device_id, **kwargs
        )

    create_from_symmetric_key.__doc__ = IoTHubDeviceClient.create_from_symmetric_key.__doc__
    setattr(IoTHubDeviceClient, "create_from_symmetric_key", classmethod(create_from_symmetric_key))

    def create_from_x509_certificate(cls, x509, hostname, device_id, **kwargs):
        return super(IoTHubDeviceClient, cls).create_from_x509_certificate(
            x509, hostname, device_id, **kwargs
        )

    create_from_x509_certificate.__doc__ = IoTHubDeviceClient.create_from_x509_certificate.__doc__
    setattr(
        IoTHubDeviceClient,
        "create_from_x509_certificate",
        classmethod(create_from_x509_certificate),
    )
    from azure.iot.device.iothub.sync_clients import IoTHubModuleClient as IoTHubModuleClient

    def connect(self):
        return super(IoTHubModuleClient, self).connect()

    connect.__doc__ = IoTHubModuleClient.connect.__doc__
    setattr(IoTHubModuleClient, "connect", connect)

    def disconnect(self):
        return super(IoTHubModuleClient, self).disconnect()

    disconnect.__doc__ = IoTHubModuleClient.disconnect.__doc__
    setattr(IoTHubModuleClient, "disconnect", disconnect)

    def get_twin(self):
        return super(IoTHubModuleClient, self).get_twin()

    get_twin.__doc__ = IoTHubModuleClient.get_twin.__doc__
    setattr(IoTHubModuleClient, "get_twin", get_twin)

    def patch_twin_reported_properties(self, reported_properties_patch):
        return super(IoTHubModuleClient, self).patch_twin_reported_properties(
            reported_properties_patch
        )

    patch_twin_reported_properties.__doc__ = (
        IoTHubModuleClient.patch_twin_reported_properties.__doc__
    )
    setattr(IoTHubModuleClient, "patch_twin_reported_properties", patch_twin_reported_properties)

    def receive_method_request(self, method_name=None, block=True, timeout=None):
        return super(IoTHubModuleClient, self).receive_method_request(method_name, block, timeout)

    receive_method_request.__doc__ = IoTHubModuleClient.receive_method_request.__doc__
    setattr(IoTHubModuleClient, "receive_method_request", receive_method_request)

    def receive_twin_desired_properties_patch(self, block=True, timeout=None):
        return super(IoTHubModuleClient, self).receive_twin_desired_properties_patch(block, timeout)

    receive_twin_desired_properties_patch.__doc__ = (
        IoTHubModuleClient.receive_twin_desired_properties_patch.__doc__
    )
    setattr(
        IoTHubModuleClient,
        "receive_twin_desired_properties_patch",
        receive_twin_desired_properties_patch,
    )

    def send_message(self, message):
        return super(IoTHubModuleClient, self).send_message(message)

    send_message.__doc__ = IoTHubModuleClient.send_message.__doc__
    setattr(IoTHubModuleClient, "send_message", send_message)

    def send_method_response(self, method_response):
        return super(IoTHubModuleClient, self).send_method_response(method_response)

    send_method_response.__doc__ = IoTHubModuleClient.send_method_response.__doc__
    setattr(IoTHubModuleClient, "send_method_response", send_method_response)

    def create_from_connection_string(cls, connection_string, **kwargs):
        return super(IoTHubModuleClient, cls).create_from_connection_string(
            connection_string, **kwargs
        )

    create_from_connection_string.__doc__ = IoTHubModuleClient.create_from_connection_string.__doc__
    setattr(
        IoTHubModuleClient,
        "create_from_connection_string",
        classmethod(create_from_connection_string),
    )

    def create_from_edge_environment(cls, **kwargs):
        return super(IoTHubModuleClient, cls).create_from_edge_environment(**kwargs)

    create_from_edge_environment.__doc__ = IoTHubModuleClient.create_from_edge_environment.__doc__
    setattr(
        IoTHubModuleClient,
        "create_from_edge_environment",
        classmethod(create_from_edge_environment),
    )

    def create_from_x509_certificate(cls, x509, hostname, device_id, module_id, **kwargs):
        return super(IoTHubModuleClient, cls).create_from_x509_certificate(
            x509, hostname, device_id, module_id, **kwargs
        )

    create_from_x509_certificate.__doc__ = IoTHubModuleClient.create_from_x509_certificate.__doc__
    setattr(
        IoTHubModuleClient,
        "create_from_x509_certificate",
        classmethod(create_from_x509_certificate),
    )
    from azure.iot.device.provisioning.provisioning_device_client import (
        ProvisioningDeviceClient as ProvisioningDeviceClient,
    )

    def create_from_symmetric_key(
        cls, provisioning_host, registration_id, id_scope, symmetric_key, **kwargs
    ):
        return super(ProvisioningDeviceClient, cls).create_from_symmetric_key(
            provisioning_host, registration_id, id_scope, symmetric_key, **kwargs
        )

    create_from_symmetric_key.__doc__ = ProvisioningDeviceClient.create_from_symmetric_key.__doc__
    setattr(
        ProvisioningDeviceClient,
        "create_from_symmetric_key",
        classmethod(create_from_symmetric_key),
    )

    def create_from_x509_certificate(
        cls, provisioning_host, registration_id, id_scope, x509, **kwargs
    ):
        return super(ProvisioningDeviceClient, cls).create_from_x509_certificate(
            provisioning_host, registration_id, id_scope, x509, **kwargs
        )

    create_from_x509_certificate.__doc__ = (
        ProvisioningDeviceClient.create_from_x509_certificate.__doc__
    )
    setattr(
        ProvisioningDeviceClient,
        "create_from_x509_certificate",
        classmethod(create_from_x509_certificate),
    )
