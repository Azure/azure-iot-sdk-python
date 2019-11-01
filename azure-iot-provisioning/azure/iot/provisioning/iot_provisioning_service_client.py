# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from .auth import ConnectionStringAuthentication
from .protocol.provisioning_service_client import ProvisioningServiceClient as protocol_client
from .protocol.models import (
    CertificateAuthority,
    DeviceGroup,
    DeviceRecord,
    GroupRecord,
    LinkedHub,
    ProvisioningSettings,
    ProvisioningRecord,
    Query,
    QueryAll,
    QueryNext,
    CertificateAuthorityQueryResponse,
)


class IoTProvisioningServiceClient(object):
    def __init__(self, connection_string):
        """Initializer for a IoT Provisioning Service client.

        After a successful creation the class has been authenticated with IoT Provisioning Service and
        it is ready to call the member APIs to communicate with it.

        :param str connection_string: The connection string used to authenticate the connection
            with Provisioning Service.

        :return Instance of the IoTProvisioningServiceClient object.
        :rtype: :class:`azure.iot.provisioning.IoTProvisioningServiceClient`
        """

        self.auth = ConnectionStringAuthentication(connection_string)
        self.protocol = protocol_client(self.auth, "https://" + self.auth["HostName"])

    def get_certificate_authority(self, certificate_authority_name):
        """Retrieves a certificate authority from IoT Provisioning Service.

        :param str certificate_authority_name: The name of the certificate authority.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.CertificateAuthority`
        :returns: The CertificateAuthority object.
        """
        return protocol_client.get_certificate_authority(
            certificate_authority_name, None, False, None
        )

    def create_certificate_authority(self, certificate_authority_name, certificate_authority):
        """Creates a certificate authority on IoT Provisioning Service.

        :param str certificate_authority_name: The desired certificate authority name.
        :param CertificateAuthority certificate_authority: The certificate authority to create.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.CertificateAuthority`
        :returns: CertificateAuthority.
        """
        return protocol_client.create_or_replace_certificate_authority(
            certificate_authority_name, certificate_authority, None, None, False, None
        )

    def replace_certificate_authority(
        self, certificate_authority_name, certificate_authority, etag
    ):
        """Replaces a certificate authority on IoT Provisioning Service.

        :param str certificate_authority_name: The desired certificate authority name.
        :param CertificateAuthority certificate_authority: The certificate authority to replace with.
        :param str etag: The etag of the certificate authority to replace.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.CertificateAuthority`
        :returns: CertificateAuthority.
        """
        if etag:
            return protocol_client.create_or_replace_certificate_authority(
                certificate_authority_name, certificate_authority, etag, None, False, None
            )
        else:
            raise ValueError("For replace operation the etag argument cannot be None")

    def delete_certificate_authority(self, certificate_authority_name, etag):
        """Deletes a certificate authority from IoT Provisioning Service.

        :param str certificate_authority_name: The certificate authority name to delete.
        :param str etag: The etag of the certificate authority to delete.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: None
        :returns: None.
        """
        protocol_client.delete_certificate_authority(
            certificate_authority_name, etag, None, False, None
        )

    def get_device_group(self, device_group_name):
        """Retrieves a device group from IoT Provisioning Service.

        :param str device_group_name: The name of the device group.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.DeviceGroup`
        :returns: The DeviceGroup object.
        """
        return protocol_client.get_device_group(device_group_name, None, False, None)

    def create_device_group(self, device_group_name, device_group):
        """Creates a device group on IoT Provisioning Service.

        :param str device_group_name: The name of the device group to create.
        :param DeviceGroup device_group: The device group to create.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.DeviceGroup`
        :returns: DeviceGroup.
        """
        return protocol_client.create_or_replace_device_group(
            device_group_name, device_group, None, None, False, None
        )

    def replace_device_group(self, device_group_name, device_group, etag):
        """Replaces a device group on IoT Provisioning Service.

        :param str device_group_name: The desired device group name to replace.
        :param DeviceGroup device_group: The new device group to replace with.
        :param str etag: The etag of the device group to replace.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.DeviceGroup`
        :returns: DeviceGroup.
        """
        if etag:
            return protocol_client.create_or_replace_device_group(
                device_group_name, device_group, etag, None, False, None
            )
        else:
            raise ValueError("For replace operation the etag argument cannot be None")

    def delete_device_group(self, device_group_name, etag):
        """Deletes a device group on IoT Provisioning Service.

        :param str device_group_name: The device group name to delete.
        :param str etag: The etag of the device group to delete.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: None
        :returns: None.
        """
        protocol_client.delete_device_group(device_group_name, etag, None, False, None)

    def get_device_record(self, device_group_name, device_id):
        """Retrieves a device authentication record from IoT Provisioning Service.

        :param str device_group_name: The name of the device group.
        :param str device_id: The ID of the device.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.DeviceRecord`
        :returns: The DeviceRecord object.
        """
        return protocol_client.get_device_record(
            device_group_name, device_id, "all", None, False, None
        )

    def create_device_record(self, device_group_name, device_id, device_record):
        """Creates a device authentication record on IoT Provisioning Service.

        :param str device_group_name: The name of the device group to create.
        :param str device_id: The ID of the device.
        :param DeviceRecord device_record: The device authentication record to create.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.DeviceRecord`
        :returns: DeviceRecord.
        """
        return protocol_client.create_or_replace_device_record(
            device_group_name, device_id, device_record, None, None, False, None
        )

    def replace_device_record(self, device_group_name, device_id, device_record, etag):
        """Replaces a device authentication record on IoT Provisioning Service.

        :param str device_group_name: The name of the device group to replace.
        :param str device_id: The ID of the device.
        :param DeviceRecord device_record: The device authentication record to replace with.
        :param str etag: The etag of the device record to replace.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.DeviceRecord`
        :returns: DeviceRecord.
        """
        if etag:
            return protocol_client.create_or_replace_device_record(
                device_group_name, device_id, device_record, etag, None, False, None
            )
        else:
            raise ValueError("For replace operation the etag argument cannot be None")

    def delete_device_record(self, device_group_name, device_id, etag):
        """Deletes a device group on IoT Provisioning Service.

        :param str device_group_name: The device group name to delete.
        :param str device_id: The ID of the device.
        :param str etag: The etag of the device group to delete.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: None
        :returns: None.
        """
        protocol_client.delete_device_record(device_group_name, device_id, etag, None, False, None)

    def get_group_record(self, device_group_name, group_record_name):
        """Retrieves a group authentication record from IoT Provisioning Service.

        :param str device_group_name: The name of the device group.
        :param str group_record_name: The name of the group record.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.GroupRecord`
        :returns: The GroupRecord object.
        """
        return protocol_client.get_group_record(
            device_group_name, group_record_name, "all", None, False, None
        )

    def create_group_record(self, device_group_name, group_record_name, group_record):
        """Creates a group authentication record on IoT Provisioning Service.

        :param str device_group_name: The name of the device group.
        :param str group_record_name: The name of the group group to create.
        :param GroupRecord group_record: The group record to create.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.GroupRecord`
        :returns: GroupRecord.
        """
        return protocol_client.create_or_replace_group_record(
            device_group_name, group_record_name, group_record, None, None, False, None
        )

    def replace_group_record(self, device_group_name, group_record_name, group_record, etag):
        """Replaces a group authentication record on Provisioning Service.

        :param str device_group_name: The name of the device group.
        :param str group_record_name: The name of the group group to replace.
        :param GroupRecord group_record: The group record to replace with.
        :param str etag: The etag of the group record to replace.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.GroupRecord`
        :returns: GroupRecord.
        """
        if etag:
            return protocol_client.create_or_replace_group_record(
                device_group_name, group_record_name, group_record, etag, None, False, None
            )
        else:
            raise ValueError("For replace operation the etag argument cannot be None")

    def delete_group_record(self, device_group_name, group_record_name, etag):
        """Deletes a group record on IoT Provisioning Service.

        :param str device_group_name: The name of the device group.
        :param str group_record_name: The name of the group group to delete.
        :param str etag: The etag of the group record to delete.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: None
        :returns: None.
        """
        protocol_client.delete_group_record(
            device_group_name, group_record_name, etag, None, False, None
        )

    def get_linked_hub(self, linked_hub_name):
        """Retrieves a linked hub from IoT Provisioning Service.

        :param str linked_hub_name: The name of the linked hub.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.LinkedHub`
        :returns: The LinkedHub object.
        """
        return protocol_client.get_linked_hub(linked_hub_name, None, False, None)

    def create_linked_hub(self, linked_hub_name, linked_hub):
        """Creates a linked hub on IoT Provisioning Service.

        :param str linked_hub_name: The name of the linked hub to create.
        :param LinkedHub linked_hub: The linked hub to create.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.LinkedHub`
        :returns: LinkedHub.
        """
        return protocol_client.create_or_replace_linked_hub(
            linked_hub_name, linked_hub, None, None, False, None
        )

    def replace_linked_hub(self, linked_hub_name, linked_hub, etag):
        """Replaces a linked hub on IoT Provisioning Service.

        :param str linked_hub_name: The name of the linked hub to replace.
        :param LinkedHub linked_hub: The linked hub to replace with.
        :param str etag: The etag of the linked hub to replace.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.LinkedHub`
        :returns: LinkedHub.
        """
        if etag:
            return protocol_client.create_or_replace_linked_hub(
                linked_hub_name, linked_hub, etag, None, False, None
            )
        else:
            raise ValueError("For replace operation the etag argument cannot be None")

    def delete_linked_hub(self, linked_hub_name, etag):
        """Deletes a linked hub from IoT Provisioning Service.

        :param str linked_hub_name: The name of the linked hub to delete.
        :param str etag: The etag of the linked hub to delete.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: None
        :returns: None.
        """
        protocol_client.delete_linked_hub(linked_hub_name, etag, None, False, None)

    def get_provisioning_settings(self, provisioning_settings_name):
        """Retrieves a provisioning settings from IoT Provisioning Service.

        :param str provisioning_settings_name: The name of the provisioning settings.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.ProvisioningSettings`
        :returns: The ProvisioningSettings object.
        """
        return protocol_client.get_provisioning_settings(
            provisioning_settings_name, None, False, None
        )

    def create_provisioning_settings(self, provisioning_settings_name, provisioning_settings):
        """Creates a provisioning settings on Provisioning Service.

        :param str provisioning_settings_name: The name of the provisioning settings to create.
        :param ProvisioningSettings provisioning_settings: The provisioning settings to create with.
        :param str etag: The etag of the provisioning settings to create.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.ProvisioningSettings`
        :returns: ProvisioningSettings.
        """
        return protocol_client.create_or_replace_provisioning_settings(
            provisioning_settings_name, provisioning_settings, None, None, False, None
        )

    def replace_provisioning_settings(
        self, provisioning_settings_name, provisioning_settings, etag
    ):
        """Replaces a provisioning settings on Provisioning Service.

        :param str provisioning_settings_name: The name of the provisioning settings to replace.
        :param ProvisioningSettings provisioning_settings: The provisioning settings to replace with.
        :param str etag: The etag of the provisioning settings to replace.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.ProvisioningSettings`
        :returns: ProvisioningSettings.
        """
        if etag:
            return protocol_client.create_or_replace_provisioning_settings(
                provisioning_settings_name, provisioning_settings, etag, None, False, None
            )
        else:
            raise ValueError("For replace operation the etag argument cannot be None")

    def delete_provisioning_settings(self, provisioning_settings_name, etag):
        """Deletes a provisioning settings from Provisioning Service.

        :param str provisioning_settings_name: The name of the provisioning settings to delete.
        :param str etag: The etag of the provisioning settings to delete.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: None
        :returns: None.
        """
        protocol_client.delete_provisioning_settings(
            provisioning_settings_name, etag, None, False, None
        )

    def get_provisioning_record(self, device_group_name, device_id):
        """Retrieves a provisioning record from IoT Provisioning Service.

        :param str device_group_name: The name of the provisioning settings to retreive.
        :param str device_id: The ID of the device.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.ProvisioningRecord`
        :returns: The ProvisioningRecord object.
        """
        return protocol_client.get_provisioning_record(
            device_group_name, device_id, None, False, None
        )

    def query_certificate_authorities(self, query, max_item_count=None):
        """Retrieves a list of the certificate authorities and a continuation
        token to retrieve the next page.

        :param Query query: The {QueryAll} to match the certificate authorities or
            {QueryNext} returned in response.
        :param int max_item_count: Maximum number of results to return in a page.
            If not specified with {QueryAll} the service will return up to 100 results.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.CertificateAuthorityQueryResponse`
        :returns: The CertificateAuthorityQueryResponse object.
        """
        return protocol_client.query_certificate_authorities(
            query, max_item_count, None, False, None
        )

    def query_device_groups(self, query, max_item_count=None):
        """Retrieves a list of the device groups and a continuation
        token to retrieve the next page.

        :param Query query: The {QueryAll} to match the device groups or
            {QueryNext} returned in response.
        :param int max_item_count: Maximum number of results to return in a page.
            If not specified with {QueryAll} the service will return up to 100 results.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.DeviceGroupQueryResponse`
        :returns: The DeviceGroupQueryResponse object.
        """
        return protocol_client.query_device_groups(query, max_item_count, None, False, None)

    def query_device_records(self, query, max_item_count=None):
        """Retrieves a list of the device records and a continuation
        token to retrieve the next page.

        :param Query query: The {QueryAll} to match the device records or
            {QueryNext} returned in response.
        :param int max_item_count: Maximum number of results to return in a page.
            If not specified with {QueryAll} the service will return up to 100 results.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.DeviceRecordQueryResponse`
        :returns: The DeviceRecordQueryResponse object.
        """
        return protocol_client.query_device_records(query, max_item_count, "all", None, False, None)

    def query_group_records(self, query, max_item_count=None):
        """Retrieves a list of the group records and a continuation
        token to retrieve the next page.

        :param Query query: The {QueryAll} to match the group records or
            {QueryNext} returned in response.
        :param int max_item_count: Maximum number of results to return in a page.
            If not specified with {QueryAll} the service will return up to 100 results.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.GroupRecordQueryResponse`
        :returns: The GroupRecordQueryResponse object.
        """
        return protocol_client.query_group_records(query, max_item_count, "all", None, False, None)

    def query_linked_hubs(self, query, max_item_count=None):
        """Retrieves a list of the linked hubs and a continuation
        token to retrieve the next page.

        :param Query query: The {QueryAll} to match the linked hubs or
            {QueryNext} returned in response.
        :param int max_item_count: Maximum number of results to return in a page.
            If not specified with {QueryAll} the service will return up to 100 results.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.LinkedHubQueryResponse`
        :returns: The LinkedHubQueryResponse object.
        """
        return protocol_client.query_linked_hubs(query, max_item_count, None, False, None)

    def query_provisioning_records(self, query, max_item_count=None):
        """Retrieves a list of the provisioning records and a continuation
        token to retrieve the next page.

        :param Query query: The {QueryAll} to match the provisioning records or
            {QueryNext} returned in response.
        :param int max_item_count: Maximum number of results to return in a page.
            If not specified with {QueryAll} the service will return up to 100 results.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.ProvisioningRecordQueryResponse`
        :returns: The ProvisioningRecordQueryResponse object.
        """
        return protocol_client.query_provisioning_records(query, max_item_count, None, False, None)

    def query_provisioning_settings(self, query, max_item_count=None):
        """Retrieves a list of the provisioning settings and a continuation
        token to retrieve the next page.

        :param Query query: The {QueryAll} to match the provisioning settings or
            {QueryNext} returned in response.
        :param int max_item_count: Maximum number of results to return in a page.
            If not specified with {QueryAll} the service will return up to 100 results.

        :raises: `ProvisioningServiceErrorDetailsException`
            if the HTTP response status is not in [200].

        :rtype: :class:`azure.iot.provisioning.ProvisioningSettingsQueryResponse`
        :returns: The ProvisioningSettingsQueryResponse object.
        """
        return protocol_client.query_provisioning_settings(query, max_item_count, None, False, None)
