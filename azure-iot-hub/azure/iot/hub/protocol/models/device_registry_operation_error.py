# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class DeviceRegistryOperationError(Model):
    """Encapsulates device registry operation error details.

    :param device_id: The ID of the device that indicated the error.
    :type device_id: str
    :param error_code: ErrorCode associated with the error. Possible values
     include: 'InvalidErrorCode', 'GenericBadRequest',
     'InvalidProtocolVersion', 'DeviceInvalidResultCount', 'InvalidOperation',
     'ArgumentInvalid', 'ArgumentNull', 'IotHubFormatError',
     'DeviceStorageEntitySerializationError', 'BlobContainerValidationError',
     'ImportWarningExistsError', 'InvalidSchemaVersion',
     'DeviceDefinedMultipleTimes', 'DeserializationError',
     'BulkRegistryOperationFailure', 'DefaultStorageEndpointNotConfigured',
     'InvalidFileUploadCorrelationId', 'ExpiredFileUploadCorrelationId',
     'InvalidStorageEndpoint', 'InvalidMessagingEndpoint',
     'InvalidFileUploadCompletionStatus', 'InvalidStorageEndpointOrBlob',
     'RequestCanceled', 'InvalidStorageEndpointProperty', 'EtagDoesNotMatch',
     'RequestTimedOut', 'UnsupportedOperationOnReplica', 'NullMessage',
     'ConnectionForcefullyClosedOnNewConnection', 'InvalidDeviceScope',
     'ConnectionForcefullyClosedOnFaultInjection',
     'ConnectionRejectedOnFaultInjection', 'InvalidRouteTestInput',
     'InvalidSourceOnRoute', 'RoutingNotEnabled',
     'InvalidContentEncodingOrType', 'InvalidEndorsementKey',
     'InvalidRegistrationId', 'InvalidStorageRootKey',
     'InvalidEnrollmentGroupId', 'TooManyEnrollments',
     'RegistrationIdDefinedMultipleTimes', 'CustomAllocationFailed',
     'CustomAllocationIotHubNotSpecified',
     'CustomAllocationUnauthorizedAccess', 'CannotRegisterModuleToModule',
     'TenantHubRoutingNotEnabled', 'InvalidConfigurationTargetCondition',
     'InvalidConfigurationContent',
     'CannotModifyImmutableConfigurationContent',
     'InvalidConfigurationCustomMetricsQuery', 'InvalidPnPInterfaceDefinition',
     'InvalidPnPDesiredProperties', 'InvalidPnPReportedProperties',
     'InvalidPnPWritableReportedProperties', 'GenericUnauthorized',
     'IotHubNotFound', 'IotHubUnauthorizedAccess', 'IotHubUnauthorized',
     'ElasticPoolNotFound', 'SystemModuleModifyUnauthorizedAccess',
     'GenericForbidden', 'IotHubSuspended', 'IotHubQuotaExceeded',
     'JobQuotaExceeded', 'DeviceMaximumQueueDepthExceeded',
     'IotHubMaxCbsTokenExceeded', 'DeviceMaximumActiveFileUploadLimitExceeded',
     'DeviceMaximumQueueSizeExceeded', 'RoutingEndpointResponseForbidden',
     'InvalidMessageExpiryTime', 'OperationNotAvailableInCurrentTier',
     'DeviceModelMaxPropertiesExceeded',
     'DeviceModelMaxIndexablePropertiesExceeded', 'IotDpsSuspended',
     'IotDpsSuspending', 'GenericNotFound', 'DeviceNotFound', 'JobNotFound',
     'QuotaMetricNotFound', 'SystemPropertyNotFound', 'AmqpAddressNotFound',
     'RoutingEndpointResponseNotFound', 'CertificateNotFound',
     'ElasticPoolTenantHubNotFound', 'ModuleNotFound',
     'AzureTableStoreNotFound', 'IotHubFailingOver', 'FeatureNotSupported',
     'DigitalTwinInterfaceNotFound', 'QueryStoreClusterNotFound',
     'DeviceNotOnline', 'DeviceConnectionClosedRemotely', 'EnrollmentNotFound',
     'DeviceRegistrationNotFound', 'AsyncOperationNotFound',
     'EnrollmentGroupNotFound', 'DeviceRecordNotFound', 'GroupRecordNotFound',
     'DeviceGroupNotFound', 'ProvisioningSettingsNotFound',
     'ProvisioningRecordNotFound', 'LinkedHubNotFound',
     'CertificateAuthorityNotFound', 'ConfigurationNotFound', 'GroupNotFound',
     'DigitalTwinModelNotFound', 'InterfaceNameModelNotFound',
     'GenericMethodNotAllowed', 'OperationNotAllowedInCurrentState',
     'ImportDevicesNotSupported', 'BulkAddDevicesNotSupported',
     'GenericConflict', 'DeviceAlreadyExists', 'LinkCreationConflict',
     'CallbackSubscriptionConflict', 'ModelAlreadyExists', 'DeviceLocked',
     'DeviceJobAlreadyExists', 'JobAlreadyExists', 'EnrollmentConflict',
     'EnrollmentGroupConflict', 'RegistrationStatusConflict',
     'DeviceRecordConflict', 'GroupRecordConflict', 'DeviceGroupConflict',
     'ProvisioningSettingsConflict', 'ProvisioningRecordConflict',
     'LinkedHubConflict', 'CertificateAuthorityConflict',
     'ModuleAlreadyExistsOnDevice', 'ConfigurationAlreadyExists',
     'ApplyConfigurationAlreadyInProgressOnDevice',
     'DigitalTwinModelAlreadyExists',
     'DigitalTwinModelExistsWithOtherModelType',
     'InterfaceNameModelAlreadyExists', 'GenericPreconditionFailed',
     'PreconditionFailed', 'DeviceMessageLockLost', 'JobRunPreconditionFailed',
     'InflightMessagesInLink', 'GenericRequestEntityTooLarge',
     'MessageTooLarge', 'TooManyDevices', 'TooManyModulesOnDevice',
     'ConfigurationCountLimitExceeded', 'DigitalTwinModelCountLimitExceeded',
     'InterfaceNameCompressionModelCountLimitExceeded',
     'GenericUnsupportedMediaType', 'IncompatibleDataType',
     'GenericTooManyRequests', 'ThrottlingException',
     'ThrottleBacklogLimitExceeded', 'ThrottlingBacklogTimeout',
     'ThrottlingMaxActiveJobCountExceeded', 'DeviceThrottlingLimitExceeded',
     'ClientClosedRequest', 'GenericServerError', 'ServerError',
     'JobCancelled', 'StatisticsRetrievalError', 'ConnectionForcefullyClosed',
     'InvalidBlobState', 'BackupTimedOut', 'AzureStorageTimeout',
     'GenericTimeout', 'InvalidThrottleParameter', 'EventHubLinkAlreadyClosed',
     'ReliableBlobStoreError', 'RetryAttemptsExhausted',
     'AzureTableStoreError', 'CheckpointStoreNotFound',
     'DocumentDbInvalidReturnValue', 'ReliableDocDbStoreStoreError',
     'ReliableBlobStoreTimeoutError', 'ConfigReadFailed',
     'InvalidContainerReceiveLink', 'InvalidPartitionEpoch', 'RestoreTimedOut',
     'StreamReservationFailure', 'UnexpectedPropertyValue',
     'OrchestrationOperationFailed', 'ModelRepoEndpointError',
     'ResolutionError', 'GenericBadGateway', 'InvalidResponseWhileProxying',
     'GenericServiceUnavailable', 'ServiceUnavailable', 'PartitionNotFound',
     'IotHubActivationFailed', 'ServerBusy', 'IotHubRestoring',
     'ReceiveLinkOpensThrottled', 'ConnectionUnavailable', 'DeviceUnavailable',
     'ConfigurationNotAvailable', 'GroupNotAvailable', 'GenericGatewayTimeout',
     'GatewayTimeout'
    :type error_code: str or ~protocol.models.enum
    :param error_status: Additional details associated with the error.
    :type error_status: str
    :param module_id:
    :type module_id: str
    :param operation:
    :type operation: str
    """

    _attribute_map = {
        'device_id': {'key': 'deviceId', 'type': 'str'},
        'error_code': {'key': 'errorCode', 'type': 'str'},
        'error_status': {'key': 'errorStatus', 'type': 'str'},
        'module_id': {'key': 'moduleId', 'type': 'str'},
        'operation': {'key': 'operation', 'type': 'str'},
    }

    def __init__(self, **kwargs):
        super(DeviceRegistryOperationError, self).__init__(**kwargs)
        self.device_id = kwargs.get('device_id', None)
        self.error_code = kwargs.get('error_code', None)
        self.error_status = kwargs.get('error_status', None)
        self.module_id = kwargs.get('module_id', None)
        self.operation = kwargs.get('operation', None)
