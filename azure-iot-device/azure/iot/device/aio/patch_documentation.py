# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module provides hard coded patches used to modify items from the libraries.
Currently we have to do like this so that we don't use exec anywhere"""


def execute_patch_for_async():
    from azure.iot.device.iothub.aio.async_clients import IoTHubDeviceClient as IoTHubDeviceClient

    async def connect(self):
        return await super(IoTHubDeviceClient, self).connect()

    connect.__doc__ = IoTHubDeviceClient.connect.__doc__
    setattr(IoTHubDeviceClient, "connect", connect)

    async def disconnect(self):
        return await super(IoTHubDeviceClient, self).disconnect()

    disconnect.__doc__ = IoTHubDeviceClient.disconnect.__doc__
    setattr(IoTHubDeviceClient, "disconnect", disconnect)

    async def get_twin(self):
        return await super(IoTHubDeviceClient, self).get_twin()

    get_twin.__doc__ = IoTHubDeviceClient.get_twin.__doc__
    setattr(IoTHubDeviceClient, "get_twin", get_twin)

    async def patch_twin_reported_properties(self, reported_properties_patch):
        return await super(IoTHubDeviceClient, self).patch_twin_reported_properties(
            reported_properties_patch
        )

    patch_twin_reported_properties.__doc__ = (
        IoTHubDeviceClient.patch_twin_reported_properties.__doc__
    )
    setattr(IoTHubDeviceClient, "patch_twin_reported_properties", patch_twin_reported_properties)

    def receive_method_request(self, method_name=None):
        return super(IoTHubDeviceClient, self).receive_method_request(method_name)

    receive_method_request.__doc__ = IoTHubDeviceClient.receive_method_request.__doc__
    setattr(IoTHubDeviceClient, "receive_method_request", receive_method_request)

    def receive_twin_desired_properties_patch(self):
        return super(IoTHubDeviceClient, self).receive_twin_desired_properties_patch()

    receive_twin_desired_properties_patch.__doc__ = (
        IoTHubDeviceClient.receive_twin_desired_properties_patch.__doc__
    )
    setattr(
        IoTHubDeviceClient,
        "receive_twin_desired_properties_patch",
        receive_twin_desired_properties_patch,
    )

    async def send_message(self, message):
        return await super(IoTHubDeviceClient, self).send_message(message)

    send_message.__doc__ = IoTHubDeviceClient.send_message.__doc__
    setattr(IoTHubDeviceClient, "send_message", send_message)

    async def send_method_response(self, method_response):
        return await super(IoTHubDeviceClient, self).send_method_response(method_response)

    send_method_response.__doc__ = IoTHubDeviceClient.send_method_response.__doc__
    setattr(IoTHubDeviceClient, "send_method_response", send_method_response)

    async def shutdown(self):
        return await super(IoTHubDeviceClient, self).shutdown()

    shutdown.__doc__ = IoTHubDeviceClient.shutdown.__doc__
    setattr(IoTHubDeviceClient, "shutdown", shutdown)

    async def update_sastoken(self, sastoken):
        return await super(IoTHubDeviceClient, self).update_sastoken(sastoken)

    update_sastoken.__doc__ = IoTHubDeviceClient.update_sastoken.__doc__
    setattr(IoTHubDeviceClient, "update_sastoken", update_sastoken)

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

    def create_from_sastoken(cls, sastoken, **kwargs):
        return super(IoTHubDeviceClient, cls).create_from_sastoken(sastoken, **kwargs)

    create_from_sastoken.__doc__ = IoTHubDeviceClient.create_from_sastoken.__doc__
    setattr(IoTHubDeviceClient, "create_from_sastoken", classmethod(create_from_sastoken))

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
    setattr(IoTHubDeviceClient, "connected", IoTHubDeviceClient.connected)
    setattr(
        IoTHubDeviceClient, "on_background_exception", IoTHubDeviceClient.on_background_exception
    )
    setattr(
        IoTHubDeviceClient,
        "on_connection_state_change",
        IoTHubDeviceClient.on_connection_state_change,
    )
    setattr(IoTHubDeviceClient, "on_message_received", IoTHubDeviceClient.on_message_received)
    setattr(
        IoTHubDeviceClient,
        "on_method_request_received",
        IoTHubDeviceClient.on_method_request_received,
    )
    setattr(
        IoTHubDeviceClient, "on_new_sastoken_required", IoTHubDeviceClient.on_new_sastoken_required
    )
    setattr(
        IoTHubDeviceClient,
        "on_twin_desired_properties_patch_received",
        IoTHubDeviceClient.on_twin_desired_properties_patch_received,
    )
    from azure.iot.device.iothub.aio.async_clients import IoTHubModuleClient as IoTHubModuleClient

    async def connect(self):
        return await super(IoTHubModuleClient, self).connect()

    connect.__doc__ = IoTHubModuleClient.connect.__doc__
    setattr(IoTHubModuleClient, "connect", connect)

    async def disconnect(self):
        return await super(IoTHubModuleClient, self).disconnect()

    disconnect.__doc__ = IoTHubModuleClient.disconnect.__doc__
    setattr(IoTHubModuleClient, "disconnect", disconnect)

    async def get_twin(self):
        return await super(IoTHubModuleClient, self).get_twin()

    get_twin.__doc__ = IoTHubModuleClient.get_twin.__doc__
    setattr(IoTHubModuleClient, "get_twin", get_twin)

    async def patch_twin_reported_properties(self, reported_properties_patch):
        return await super(IoTHubModuleClient, self).patch_twin_reported_properties(
            reported_properties_patch
        )

    patch_twin_reported_properties.__doc__ = (
        IoTHubModuleClient.patch_twin_reported_properties.__doc__
    )
    setattr(IoTHubModuleClient, "patch_twin_reported_properties", patch_twin_reported_properties)

    def receive_method_request(self, method_name=None):
        return super(IoTHubModuleClient, self).receive_method_request(method_name)

    receive_method_request.__doc__ = IoTHubModuleClient.receive_method_request.__doc__
    setattr(IoTHubModuleClient, "receive_method_request", receive_method_request)

    def receive_twin_desired_properties_patch(self):
        return super(IoTHubModuleClient, self).receive_twin_desired_properties_patch()

    receive_twin_desired_properties_patch.__doc__ = (
        IoTHubModuleClient.receive_twin_desired_properties_patch.__doc__
    )
    setattr(
        IoTHubModuleClient,
        "receive_twin_desired_properties_patch",
        receive_twin_desired_properties_patch,
    )

    async def send_message(self, message):
        return await super(IoTHubModuleClient, self).send_message(message)

    send_message.__doc__ = IoTHubModuleClient.send_message.__doc__
    setattr(IoTHubModuleClient, "send_message", send_message)

    async def send_method_response(self, method_response):
        return await super(IoTHubModuleClient, self).send_method_response(method_response)

    send_method_response.__doc__ = IoTHubModuleClient.send_method_response.__doc__
    setattr(IoTHubModuleClient, "send_method_response", send_method_response)

    async def shutdown(self):
        return await super(IoTHubModuleClient, self).shutdown()

    shutdown.__doc__ = IoTHubModuleClient.shutdown.__doc__
    setattr(IoTHubModuleClient, "shutdown", shutdown)

    async def update_sastoken(self, sastoken):
        return await super(IoTHubModuleClient, self).update_sastoken(sastoken)

    update_sastoken.__doc__ = IoTHubModuleClient.update_sastoken.__doc__
    setattr(IoTHubModuleClient, "update_sastoken", update_sastoken)

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

    def create_from_sastoken(cls, sastoken, **kwargs):
        return super(IoTHubModuleClient, cls).create_from_sastoken(sastoken, **kwargs)

    create_from_sastoken.__doc__ = IoTHubModuleClient.create_from_sastoken.__doc__
    setattr(IoTHubModuleClient, "create_from_sastoken", classmethod(create_from_sastoken))

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
    setattr(IoTHubModuleClient, "connected", IoTHubModuleClient.connected)
    setattr(
        IoTHubModuleClient, "on_background_exception", IoTHubModuleClient.on_background_exception
    )
    setattr(
        IoTHubModuleClient,
        "on_connection_state_change",
        IoTHubModuleClient.on_connection_state_change,
    )
    setattr(IoTHubModuleClient, "on_message_received", IoTHubModuleClient.on_message_received)
    setattr(
        IoTHubModuleClient,
        "on_method_request_received",
        IoTHubModuleClient.on_method_request_received,
    )
    setattr(
        IoTHubModuleClient, "on_new_sastoken_required", IoTHubModuleClient.on_new_sastoken_required
    )
    setattr(
        IoTHubModuleClient,
        "on_twin_desired_properties_patch_received",
        IoTHubModuleClient.on_twin_desired_properties_patch_received,
    )
    from azure.iot.device.provisioning.aio.async_provisioning_device_client import (
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
    setattr(
        ProvisioningDeviceClient,
        "provisioning_payload",
        ProvisioningDeviceClient.provisioning_payload,
    )
