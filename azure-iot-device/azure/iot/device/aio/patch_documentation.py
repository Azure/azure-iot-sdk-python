# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module provides hard coded patches used to modify items from the libraries.
Currently we have to do like this so that we don't use exec anywhere"""


def execute_patch_for_async():
    from azure.iot.device.iothub.aio.async_clients import IoTHubDeviceClient as IoTHubDeviceClient_

    async def connect(self):
        return await super(IoTHubDeviceClient_, self).connect()

    connect.__doc__ = IoTHubDeviceClient_.connect.__doc__
    setattr(IoTHubDeviceClient_, "connect", connect)

    async def disconnect(self):
        return await super(IoTHubDeviceClient_, self).disconnect()

    disconnect.__doc__ = IoTHubDeviceClient_.disconnect.__doc__
    setattr(IoTHubDeviceClient_, "disconnect", disconnect)

    async def get_storage_info_for_blob(self, blob_name):
        return await super(IoTHubDeviceClient_, self).get_storage_info_for_blob(blob_name)

    get_storage_info_for_blob.__doc__ = IoTHubDeviceClient_.get_storage_info_for_blob.__doc__
    setattr(IoTHubDeviceClient_, "get_storage_info_for_blob", get_storage_info_for_blob)

    async def get_twin(self):
        return await super(IoTHubDeviceClient_, self).get_twin()

    get_twin.__doc__ = IoTHubDeviceClient_.get_twin.__doc__
    setattr(IoTHubDeviceClient_, "get_twin", get_twin)

    async def notify_blob_upload_status(
        self, correlation_id, is_success, status_code, status_description
    ):
        return await super(IoTHubDeviceClient_, self).notify_blob_upload_status(
            correlation_id, is_success, status_code, status_description
        )

    notify_blob_upload_status.__doc__ = IoTHubDeviceClient_.notify_blob_upload_status.__doc__
    setattr(IoTHubDeviceClient_, "notify_blob_upload_status", notify_blob_upload_status)

    async def patch_twin_reported_properties(self, reported_properties_patch):
        return await super(IoTHubDeviceClient_, self).patch_twin_reported_properties(
            reported_properties_patch
        )

    patch_twin_reported_properties.__doc__ = (
        IoTHubDeviceClient_.patch_twin_reported_properties.__doc__
    )
    setattr(IoTHubDeviceClient_, "patch_twin_reported_properties", patch_twin_reported_properties)

    async def receive_method_request(self, method_name=None):
        return await super(IoTHubDeviceClient_, self).receive_method_request(method_name)

    receive_method_request.__doc__ = IoTHubDeviceClient_.receive_method_request.__doc__
    setattr(IoTHubDeviceClient_, "receive_method_request", receive_method_request)

    async def receive_twin_desired_properties_patch(self):
        return await super(IoTHubDeviceClient_, self).receive_twin_desired_properties_patch()

    receive_twin_desired_properties_patch.__doc__ = (
        IoTHubDeviceClient_.receive_twin_desired_properties_patch.__doc__
    )
    setattr(
        IoTHubDeviceClient_,
        "receive_twin_desired_properties_patch",
        receive_twin_desired_properties_patch,
    )

    async def send_message(self, message):
        return await super(IoTHubDeviceClient_, self).send_message(message)

    send_message.__doc__ = IoTHubDeviceClient_.send_message.__doc__
    setattr(IoTHubDeviceClient_, "send_message", send_message)

    async def send_method_response(self, method_response):
        return await super(IoTHubDeviceClient_, self).send_method_response(method_response)

    send_method_response.__doc__ = IoTHubDeviceClient_.send_method_response.__doc__
    setattr(IoTHubDeviceClient_, "send_method_response", send_method_response)

    def create_from_connection_string(cls, connection_string, **kwargs):
        return super(IoTHubDeviceClient_, cls).create_from_connection_string(
            connection_string, **kwargs
        )

    create_from_connection_string.__doc__ = (
        IoTHubDeviceClient_.create_from_connection_string.__doc__
    )
    setattr(
        IoTHubDeviceClient_,
        "create_from_connection_string",
        classmethod(create_from_connection_string),
    )

    def create_from_symmetric_key(cls, symmetric_key, hostname, device_id, **kwargs):
        return super(IoTHubDeviceClient_, cls).create_from_symmetric_key(
            symmetric_key, hostname, device_id, **kwargs
        )

    create_from_symmetric_key.__doc__ = IoTHubDeviceClient_.create_from_symmetric_key.__doc__
    setattr(
        IoTHubDeviceClient_, "create_from_symmetric_key", classmethod(create_from_symmetric_key)
    )

    def create_from_x509_certificate(cls, x509, hostname, device_id, **kwargs):
        return super(IoTHubDeviceClient_, cls).create_from_x509_certificate(
            x509, hostname, device_id, **kwargs
        )

    create_from_x509_certificate.__doc__ = IoTHubDeviceClient_.create_from_x509_certificate.__doc__
    setattr(
        IoTHubDeviceClient_,
        "create_from_x509_certificate",
        classmethod(create_from_x509_certificate),
    )
    from azure.iot.device.iothub.aio.async_clients import IoTHubModuleClient as IoTHubModuleClient_

    async def connect(self):
        return await super(IoTHubModuleClient_, self).connect()

    connect.__doc__ = IoTHubModuleClient_.connect.__doc__
    setattr(IoTHubModuleClient_, "connect", connect)

    async def disconnect(self):
        return await super(IoTHubModuleClient_, self).disconnect()

    disconnect.__doc__ = IoTHubModuleClient_.disconnect.__doc__
    setattr(IoTHubModuleClient_, "disconnect", disconnect)

    async def get_storage_info_for_blob(self, blob_name):
        return await super(IoTHubModuleClient_, self).get_storage_info_for_blob(blob_name)

    get_storage_info_for_blob.__doc__ = IoTHubModuleClient_.get_storage_info_for_blob.__doc__
    setattr(IoTHubModuleClient_, "get_storage_info_for_blob", get_storage_info_for_blob)

    async def get_twin(self):
        return await super(IoTHubModuleClient_, self).get_twin()

    get_twin.__doc__ = IoTHubModuleClient_.get_twin.__doc__
    setattr(IoTHubModuleClient_, "get_twin", get_twin)

    async def notify_blob_upload_status(
        self, correlation_id, is_success, status_code, status_description
    ):
        return await super(IoTHubModuleClient_, self).notify_blob_upload_status(
            correlation_id, is_success, status_code, status_description
        )

    notify_blob_upload_status.__doc__ = IoTHubModuleClient_.notify_blob_upload_status.__doc__
    setattr(IoTHubModuleClient_, "notify_blob_upload_status", notify_blob_upload_status)

    async def patch_twin_reported_properties(self, reported_properties_patch):
        return await super(IoTHubModuleClient_, self).patch_twin_reported_properties(
            reported_properties_patch
        )

    patch_twin_reported_properties.__doc__ = (
        IoTHubModuleClient_.patch_twin_reported_properties.__doc__
    )
    setattr(IoTHubModuleClient_, "patch_twin_reported_properties", patch_twin_reported_properties)

    async def receive_method_request(self, method_name=None):
        return await super(IoTHubModuleClient_, self).receive_method_request(method_name)

    receive_method_request.__doc__ = IoTHubModuleClient_.receive_method_request.__doc__
    setattr(IoTHubModuleClient_, "receive_method_request", receive_method_request)

    async def receive_twin_desired_properties_patch(self):
        return await super(IoTHubModuleClient_, self).receive_twin_desired_properties_patch()

    receive_twin_desired_properties_patch.__doc__ = (
        IoTHubModuleClient_.receive_twin_desired_properties_patch.__doc__
    )
    setattr(
        IoTHubModuleClient_,
        "receive_twin_desired_properties_patch",
        receive_twin_desired_properties_patch,
    )

    async def send_message(self, message):
        return await super(IoTHubModuleClient_, self).send_message(message)

    send_message.__doc__ = IoTHubModuleClient_.send_message.__doc__
    setattr(IoTHubModuleClient_, "send_message", send_message)

    async def send_method_response(self, method_response):
        return await super(IoTHubModuleClient_, self).send_method_response(method_response)

    send_method_response.__doc__ = IoTHubModuleClient_.send_method_response.__doc__
    setattr(IoTHubModuleClient_, "send_method_response", send_method_response)

    def create_from_connection_string(cls, connection_string, **kwargs):
        return super(IoTHubModuleClient_, cls).create_from_connection_string(
            connection_string, **kwargs
        )

    create_from_connection_string.__doc__ = (
        IoTHubModuleClient_.create_from_connection_string.__doc__
    )
    setattr(
        IoTHubModuleClient_,
        "create_from_connection_string",
        classmethod(create_from_connection_string),
    )

    def create_from_edge_environment(cls, **kwargs):
        return super(IoTHubModuleClient_, cls).create_from_edge_environment(**kwargs)

    create_from_edge_environment.__doc__ = IoTHubModuleClient_.create_from_edge_environment.__doc__
    setattr(
        IoTHubModuleClient_,
        "create_from_edge_environment",
        classmethod(create_from_edge_environment),
    )

    def create_from_x509_certificate(cls, x509, hostname, device_id, module_id, **kwargs):
        return super(IoTHubModuleClient_, cls).create_from_x509_certificate(
            x509, hostname, device_id, module_id, **kwargs
        )

    create_from_x509_certificate.__doc__ = IoTHubModuleClient_.create_from_x509_certificate.__doc__
    setattr(
        IoTHubModuleClient_,
        "create_from_x509_certificate",
        classmethod(create_from_x509_certificate),
    )
    from azure.iot.device.provisioning.aio.async_provisioning_device_client import (
        ProvisioningDeviceClient as ProvisioningDeviceClient_,
    )

    def create_from_symmetric_key(
        cls, provisioning_host, registration_id, id_scope, symmetric_key, **kwargs
    ):
        return super(ProvisioningDeviceClient_, cls).create_from_symmetric_key(
            provisioning_host, registration_id, id_scope, symmetric_key, **kwargs
        )

    create_from_symmetric_key.__doc__ = ProvisioningDeviceClient_.create_from_symmetric_key.__doc__
    setattr(
        ProvisioningDeviceClient_,
        "create_from_symmetric_key",
        classmethod(create_from_symmetric_key),
    )

    def create_from_x509_certificate(
        cls, provisioning_host, registration_id, id_scope, x509, **kwargs
    ):
        return super(ProvisioningDeviceClient_, cls).create_from_x509_certificate(
            provisioning_host, registration_id, id_scope, x509, **kwargs
        )

    create_from_x509_certificate.__doc__ = (
        ProvisioningDeviceClient_.create_from_x509_certificate.__doc__
    )
    setattr(
        ProvisioningDeviceClient_,
        "create_from_x509_certificate",
        classmethod(create_from_x509_certificate),
    )
