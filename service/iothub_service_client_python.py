#!/usr/bin/env python

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

# Dummy API definitions of IotHub Service Client for generating API documentation

from enum import Enum

class IoTHubMapResult(Enum):
    OK = 0
    ERROR = 1
    INVALIDARG = 2
    KEYEXISTS = 3
    KEYNOTFOUND = 4
    FILTER_REJECT = 5


class IoTHubMessageResult(Enum):
    OK = 0
    INVALID_ARG = 1
    INVALID_TYPE = 2
    ERROR = 3


class IoTHubMessageDispositionResult(Enum):
    ACCEPTED = 0
    REJECTED = 1
    ABANDONED = 2


class IoTHubMessageContent(Enum):
    BYTEARRAY = 0
    STRING = 1
    UNKNOWN = 2


class IoTHubRegistryManagerResult(Enum):
    OK = 0
    INVALID_ARG = 1
    ERROR = 2
    JSON_ERROR = 3
    HTTPAPI_ERROR = 4
    HTTP_STATUS_ERROR = 5
    DEVICE_EXIST = 6
    DEVICE_NOT_EXIST = 7
    CALLBACK_NOT_SET = 8


class IoTHubRegistryManagerAuthMethod(Enum):
    SHARED_PRIVATE_KEY = 0
    X509_THUMBPRINT = 1
    X509_CERTIFICATE_AUTHORITY = 2


class IoTHubMessagingResult(Enum):
    OK = 0
    INVALID_ARG = 1
    ERROR = 2
    INVALID_JSON = 3
    DEVICE_EXIST = 4
    CALLBACK_NOT_SET = 5


class IoTHubDeviceConnectionState(Enum):
    CONNECTED = 0
    DISCONNECTED = 1


class IoTHubDeviceStatus(Enum):
    ENABLED = 0
    DISABLED = 1


class IoTHubFeedbackStatusCode(Enum):
    SUCCESS = 0
    EXPIRED = 1
    DELIVER_COUNT_EXCEEDED = 2
    REJECTED = 3
    UNKNOWN = 4


class IoTHubDeviceMethodResult(Enum):
    OK = 0
    INVALID_ARG = 1
    ERROR = 2
    HTTPAPI_ERROR = 3


class IoTHubDeviceTwinResult(Enum):
    OK = 0
    INVALID_ARG = 1
    ERROR = 2
    HTTPAPI_ERROR = 3


class IoTHubError:
    """Generic exception base class.
    IoTHub errors derived from BaseException --> IoTHubError --> IoTHubXXXError
    """
    pass


class IoTHubMapError(IoTHubError):
    """IoTHubMap specific exception class, derived from IoTHubError.
    """
    pass


class IoTHubMessageError(IoTHubError):
    """IoTHubMessage specific exception class, derived from IoTHubError.
    """
    pass


class IoTHubServiceClientAuthError(IoTHubError):
    """IoTHubServiceClientAut specific exception class, derived from IoTHubError.
    """
    pass


class IoTHubRegistryManagerError(IoTHubError):
    """IoTHubRegistryManager specific exception class, derived from IoTHubError.
    """
    pass


class IoTHubMessagingError(IoTHubError):
    """IoTHubMessaging specific exception class, derived from IoTHubError.
    """
    pass


class IoTHubDeviceMethodError(IoTHubError):
    """IoTHubDeviceMethod specific exception class, derived from IoTHubError.
    """
    pass


class IoTHubDeviceTwinError(IoTHubError):
    """IoTHubDeviceTwin specific exception class, derived from IoTHubError.
    """
    pass


class IoTHubMap:
    """IoTHubMap is a generic map implementation storing key/value pairs.
    """

    def add(self, key, value):
        """Adds the given key/value pair to the map.
        If the given key exists the function does nothing.

        :param key: The name of the key
        :type key: str
        :param value: The value string
        :type value: str
        :return: OK if success (raise otherwise)
        :rtype: IoTHubMapResult(Enum)
        :raises: IoTHubMapError if the operation failed
        """
        pass

    def add_or_update(self, key, value):
        """Adds the given key/value pair to the map.
        If the given key exists the function updates the value.

        :param key: The name of the key
        :type key: str
        :param value: The value string
        :type value: str
        :return: OK if success (raise otherwise)
        :rtype: IoTHubMapResult(Enum)
        :raises: IoTHubMapError if the operation failed
        """
        pass

    def delete(self, key):
        """Deletes the key/value pair identified by the given key.

        :param key: The name of the key
        :type key: str
        :return: OK if success (raise otherwise)
        :rtype: IoTHubMapResult(Enum)
        :raises: IoTHubMapError if the operation failed
        """
        pass

    def contains_key(self, key):
        """Indicates if the map contains the given key.

        :param key: The name of the key
        :type key: str
        :return: OK if the key has been found (raise otherwise)
        :rtype: IoTHubMapResult(Enum)
        :raises: IoTHubMapError if the operation failed
        """
        pass

    def contains_value(self, value):
        """Indicates if the map contains the given value.

        :param value: The value
        :type value: str
        :return: OK if the value has been found (raise otherwise)
        :rtype: IoTHubMapResult(Enum)
        :raises: IoTHubMapError if the operation failed
        """
        pass

    def get_value_from_key(self, key):
        """Returns with the value of the given key.

        :param key: The name of the key
        :type key: str
        :return: The value if the key has been found (raise otherwise)
        :rtype: str
        :raises: IoTHubMapError if the operation failed
        """
        pass

    def get_internals(self):
        """Returns with a Python dictionary containing all the elements of the map.

        :return: A dictionary containing the map (raise otherwise)
        :rtype: dictionary
        :raises: IoTHubMapError if the operation failed
        """
        pass


class IoTHubMessage:
    """IoTHubMessage instance is used to hold a message communicate with IoTHub.
    Users of the SDK should create an instance of this class using one of the
    constructors provided and use that instance with IoTHubClient.
    """

    def __init__(self, source_str):
        """Creates an IoTHubMessage instance and sets the message body to the content of
        the given string source.

        :param source_str: A string containing the message data
        :type source_str: str
        :return: IoTHubMessage instance
        :raises: IoTHubMessageError if the object creation failed
        """
        pass

    def __init__(self, source_byte_array):
        """Creates an IoTHubMessage instance and sets the message body to the content of
        the given byte array source.

        :param source_byte_array: A bytearray containing the message data
        :type source_byte_array: bytearray
        :return: IoTHubMessage instance
        :raises: IoTHubMessageError if the object creation failed
        """
        pass

    @property
    def properties(self):
        """Getter for message properties

        :return: Map of message properties
        :rtype: IoTHubMap
        """
        pass

    @property
    def message_id(self):
        """Public attribute for message_id

        :return: The value of the message_id property of the message
        :rtype: str
        :raises: IoTHubMessageError if setting the property failed
        """
        pass

    @property
    def correlation_id(self):
        """Public attribute for correlation_id

        :return: The value of the correlation_id property of the message
        :rtype: str
        :raises: IoTHubMessageError if setting the property failed
        """
        pass

    def get_bytearray(self):
        """Gets the content of the message as a bytearray.

        :return: The content of the message
        :rtype: bytearray
        :raises: IoTHubMessageError if the operation failed
        """
        pass

    def get_string(self):
        """Gets the content of the message as a string.

        :return: The content of the message
        :rtype: str
        """
        pass

    def get_content_type(self):
        """Gets the type of the content of the message as a IoTHubMessageContent enum.

        :return: The type of the content of the message
        :rtype: IoTHubMessageContent(Enum)
        """
        pass


class IoTHubDevice:
    """IoTHubDevice instance holds device properties of an IoTHub device.
    """
    @property
    def deviceId(self):
        """Public attribute for deviceId (device name on IoTHub)

        :return: The value of the deviceId property
        :rtype: str
        """
        pass

    @property
    def primaryKey(self):
        """Public attribute for primaryKey

        :return: The value of the primaryKey property
        :rtype: str
        """
        pass

    @property
    def secondaryKey(self):
        """Public attribute for secondaryKey

        :return: The value of the secondaryKey property
        :rtype: str
        """
        pass

    @property
    def generationId(self):
        """Public attribute for generationId

        :return: The value of the generationId property
        :rtype: str
        """
        pass

    @property
    def eTag(self):
        """Public attribute for eTag

        :return: The value of the eTag property
        :rtype: str
        """
        pass

    @property
    def connectionState(self):
        """Public attribute for connectionState

        :return: The value of the connectionState property
        :rtype: IoTHubDeviceConnectionState(Enum)
        """
        pass

    @property
    def connectionStateUpdatedTime(self):
        """Public attribute for connectionStateUpdatedTime

        :return: The value of the connectionStateUpdatedTime property
        :rtype: str
        """
        pass

    @property
    def status(self):
        """Public attribute for status

        :return: The value of the status property
        :rtype: IoTHubDeviceStatus(Enum)
        """
        pass

    @property
    def statusReason(self):
        """Public attribute for statusReason

        :return: The value of the statusReason property
        :rtype: str
        """
        pass

    @property
    def statusUpdatedTime(self):
        """Public attribute for statusUpdatedTime

        :return: The value of the statusUpdatedTime property
        :rtype: str
        """
        pass

    @property
    def lastActivityTime(self):
        """Public attribute for lastActivityTime

        :return: The value of the lastActivityTime property
        :rtype: str
        """
        pass

    @property
    def cloudToDeviceMessageCount(self):
        """Public attribute for cloudToDeviceMessageCount

        :return: The value of the cloudToDeviceMessageCount property
        :rtype: int
        """
        pass

    @property
    def isManaged(self):
        """Public attribute for isManaged

        :return: The value of the isManaged property
        :rtype: bool
        """
        pass

    @property
    def configuration(self):
        """Public attribute for configuration

        :return: The value of the configuration property
        :rtype: str
        """
        pass

    @property
    def deviceProperties(self):
        """Public attribute for deviceProperties

        :return: The value of the deviceProperties property
        :rtype: str
        """
        pass

    @property
    def serviceProperties(self):
        """Public attribute for serviceProperties

        :return: The value of the serviceProperties property
        :rtype: str
        """
        pass

    @property
    def authMethod(self):
        """Public attribute for authMethod

        :return: The value of the authMethod property
        :rtype: IoTHubRegistryManagerAuthMethod(Enum)
        """
        pass


class IoTHubRegistryStatistics:
    """IoTHubRegistryStatistics instance holds registry statistics data (used in GetRegistryStatistics).
    """
    @property
    def totalDeviceCount(self):
        """Public attribute for totalDeviceCount

        :return: The value of the totalDeviceCount property
        :rtype: int
        """
        pass

    @property
    def enabledDeviceCount(self):
        """Public attribute for enabledDeviceCount

        :return: The value of the enabledDeviceCount property
        :rtype: int
        """
        pass

    @property
    def disabledDeviceCount(self):
        """Public attribute for disabledDeviceCount

        :return: The value of the disabledDeviceCount property
        :rtype: int
        """
        pass


class IoTHubServiceFeedbackBatch:
    """IoTHubServiceFeedbackBatch instance holds a list (batch) of service feedbacks data.
    """
    @property
    def userId(self):
        """Public attribute for userId

        :return: The value of the userId property
        :rtype: str
        """
        pass

    @property
    def lockToken(self):
        """Public attribute for lockToken

        :return: The value of the lockToken property
        :rtype: str
        """
        pass

    @property
    def feedbackRecordList(self):
        """Public attribute for feedbackRecordList

        :return: The value of the feedbackRecordList property
        :rtype: list
        """
        pass


class IoTHubServiceFeedbackRecord:
    """IoTHubServiceFeedbackRecord instance holds service feedback message data.
    """
    @property
    def description(self):
        """Public attribute for description

        :return: The value of the description property
        :rtype: str
        """
        pass

    @property
    def deviceId(self):
        """Public attribute for deviceId

        :return: The value of the deviceId property
        :rtype: str
        """
        pass

    @property
    def correlationId(self):
        """Public attribute for correlationId

        :return: The value of the correlationId property
        :rtype: str
        """
        pass

    @property
    def generationId(self):
        """Public attribute for generationId

        :return: The value of the generationId property
        :rtype: str
        """
        pass

    @property
    def enqueuedTimeUtc(self):
        """Public attribute for enqueuedTimeUtc

        :return: The value of the enqueuedTimeUtc property
        :rtype: str
        """
        pass

    @property
    def statusCode(self):
        """Public attribute for statusCode

        :return: The value of the statusCode property
        :rtype: IoTHubFeedbackStatusCode(Enum)
        """
        pass

    @property
    def originalMessageId(self):
        """Public attribute for originalMessageId

        :return: The value of the originalMessageId property
        :rtype: str
        """
        pass


class IoTHubDeviceMethodResponse:
    """IoTHubDeviceMethodResponse instance holds a data structure for method responses.
    """
    @property
    def originalMessageId(self):
        """Public attribute for status

        :return: The value of the status property
        :rtype: int
        """
        pass

    @property
    def originalMessageId(self):
        """Public attribute for payload

        :return: The value of the payload property
        :rtype: str
        """
        pass


class IoTHubServiceClientAuth:
    """IoTHubServiceClientAuth instance holds service client authentication handle
    to communicate with IoTHub.
    """
    def __init__(self, connection_str):
        """Creates an IoTHubServiceClientAuth instance from the given IoTHub connection string.

        :param connection_str: IoTHub connection string
        :type connection_str: str
        """
        pass


class IoTHubRegistryManager:
    """IoTHubRegistryManager instance is used to manage devices on a given IoTHub.
    """
    def __init__(self, connection_string):
        """Creates an IoTHubRegistryManager object using the given IoTHub connection string

        :param connection_string:
        :type: str
        """
        pass

    def __init__(self, service_client_auth_handle):
        """Creates an IoTHubMessaging object using the given IoTHub service client authentication handle

        :param service_client_auth_handle:
        :type: str
        """
        pass

    def create_device(self, device_id, primary_key, secondary_key, auth_method):
        """Creates a device on IoTHub using the given parameters.
        
        :param device_id: The name of the device
        :type device_id: str
        :param primary_key: The primary key of the device
        :type primary_key: str
        :param secondary_key: The secondary key of the device
        :type secondary_key: str
        :param auth_method: The authentication method used to authenticate the device client
        :type auth_method: IoTHubRegistryManagerAuthMethod(Enum)
        :return: The device client instance
        :rtype: IoTHubDevice
        """
        pass

    def get_device(self, device_id):
        """Gets the device instance by name (id).
        
        :param device_id: The name (id) of the device to get
        :type device_id: str
        :return: The device client object
        :rtype: IoTHubDevice
        """
        pass

    def update_device(self, device_id, primary_key, secondary_key, status, auth_method):
        """Updates device attributes on the given device. All attributes need to be provided.
        
        :param device_id: The name (id) of the device to update
        :type device_id: str
        :param primary_key: The new primary key of the device
        :type primary_key: str
        :param secondary_key: The new secondary key of the device
        :type secondary_key: str
        :param status: The new status of the device
        :type status: str
        :param auth_method: The new authetication method used to authenticate the device client
        :type auth_method: IoTHubRegistryManagerAuthMethod(Enum)
        :raises: IoTHubRegistryManagerError if the update operation is failed
        """
        pass

    def delete_device(self, device_id):
        """Deletes the given device from IoTHub.
        
        :param device_id: The device name (id) to delete
        :type device_id: str
        :raises: IoTHubRegistryManagerError if the delete operation is failed
        """
        pass

    def get_device_list(self, number_of_devices):
        """Gets the list of devices registered on IoTHub.
        It will return with the requested number of devices.
        If the requested number more than the number of registered devices,
        than it will return the actual number of devices.

        :param number_of_devices: The requested number of devices
        :type number_of_devices: int
        :return: The list of devices
        :rtype: list
        """
        pass

    def get_statistics(self):
        """Returns with a data structure containing device registry statistics.
        Contains total, enabled and disabled device count.

        :return: IoTHubRegistryStatistics instance
        :rtype: IoTHubRegistryStatistics
        """
        pass

    def create_module(self, device_id, primary_key, secondary_key, module_id, auth_method):
        """Creates a module on IoTHub using the given parameters.
        
        :param device_id: The name of the device associated with module_id
        :type device_id: str
        :param primary_key: The primary key of the device
        :type primary_key: str
        :param secondary_key: The secondary key of the device
        :type secondary_key: str
        :param auth_method: The authentication method used to authenticate the device client
        :type auth_method: IoTHubRegistryManagerAuthMethod(Enum)
        :param module_id: The name of the module to create
        :type module_id: str
        :return: The device client instance
        :rtype: IoTHubDevice
        """
        pass

    def get_module(self, device_id, module_id):
        """Gets the device instance by device name (id) and module name (id).
        
        :param device_id: The name (id) of the device associated with the module
        :type device_id: str
        :param module_id: The name (id) of the module to get
        :type module_id: str
        :return: The device client object
        :rtype: IoTHubDevice
        """
        pass

    def update_module(self, device_id, primary_key, secondary_key, module_id, auth_method):
        """Updates device attributes on the given device. All attributes need to be provided.
        
        :param device_id: The name (id) of the device associated with the module
        :type device_id: str
        :param primary_key: The new primary key of the device
        :type primary_key: str
        :param secondary_key: The new secondary key of the device
        :type secondary_key: str
        :param device_id: The name (id) of the module to update
        :type device_id: str
        :param auth_method: The new authetication method used to authenticate the device client
        :type auth_method: IoTHubRegistryManagerAuthMethod(Enum)
        :raises: IoTHubRegistryManagerError if the update operation is failed
        """
        pass

    def delete_module(self, device_id, module_id):
        """Deletes the given module from IoTHub.
        
        :param device_id: The device name (id) associated with the module
        :type device_id: str
        :param module_id: The module name (id) to delete
        :type module_id: str
        :raises: IoTHubRegistryManagerError if the delete operation is failed
        """
        pass


class IoTHubMessaging:
    """IoTHubMessaging instance is used to send messages from IoTHub to devices.
    """
    def __init__(self, connection_string):
        """Creates an IoTHubMessaging object using the given IoTHub connection string.

        :param connection_string: IoTHub connection string
        :type: str
        """
        pass

    def __init__(self, service_client_auth_handle):
        """Creates an IoTHubMessaging object using the given IoTHub service client authentication handle.

        :param service_client_auth_handle: IoTHubServiceClientAuth instance
        :type: IoTHubServiceClientAuth
        """
        pass

    def open(self, open_complete_Callback, user_context):
        """Opens the messaging channel to the IoTHub. Sets up the given callbacks.
        
        :param open_complete_Callback: The callback will be called when the communication channel is opened
        :type open_complete_Callback: Callable Python function
        :param user_context:  The user context object used in the open_complete_Callback
        :type user_context: any
        :raises: IoTHubMessagingError if the open failed
        """
        pass

    def close(self):
        """Closes the messaging channel.
        :raises: IoTHubMessagingError if the close failed
        """
        pass

    def send_async(self, device_id, message, send_complete_callback, user_context):
        """
        
        :param device_id: The device name (id) to send the message to
        :type device_id: str
        :param message: The IoTHubMessage instance to send
        :type message: IoTHubMessage
        :param send_complete_callback: The callback will be called if send operation completed
        :type send_complete_callback: Callable Python function
        :param user_context: The user context object used in the sendCompleteCallback
        :type user_context: any
        :raises: IoTHubMessagingError if send operation failed
        """
        pass

    def send_async(self, device_id, module_id, message, send_complete_callback, user_context):
        """
        
        :param device_id: The device name (id) associated with module_id
        :type device_id: str
        :param module_id: The module name (id) to send the message to
        :type module_id: str
        :param message: The IoTHubMessage instance to send
        :type message: IoTHubMessage
        :param send_complete_callback: The callback will be called if send operation completed
        :type send_complete_callback: Callable Python function
        :param user_context: The user context object used in the sendCompleteCallback
        :type user_context: any
        :raises: IoTHubMessagingError if send operation failed
        """
        pass


    def set_feedback_message_callback(self, feedback_message_received_callback, user_context):
        """
        
        :param feedback_message_received_callback: The callback will be called if feedback was received
        :type feedback_message_received_callback: Callable Python function
        :param user_context: The user context object used in the feedback_message_received_callback
        :type user_context: any
        :raises: IoTHubMessagingError if setting the callback failed
        """
        pass


class IoTHubDeviceMethod:
    """IoTHubDeviceMethod instance is used to invoke device methods on devices from the IoTHub.
    """
    def __init__(self, connection_string):
        """Creates a IoTHubDeviceMethod instance using the IoTHub connection
        string. The IoTHubDeviceMethod instance to be used to call a method on a device.

        :param connection_string: IoTHub connection string
        :type connection_string: str
        """
        pass

    def __init__(self, service_client_auth_handle):
        """Creates an IoTHubMessaging object using the given IoTHub serviceClientAuthHandle.

        :param service_client_auth_handle: IoTHubServiceClientAuth instance
        :type: IoTHubServiceClientAuth
        """
        pass

    def invoke(self, device_id, method_name, method_payload, timeout):
        """Invokes the given method on the given device with the given payload

        :param device_id: The name (id) of the device
        :type device_id: str
        :param method_name: The name of the method to invoke
        :type method_name: str
        :param method_payload: The payload to use in the method
        :type method_payload: str
        :param timeout: The timeout to use to wait for the method return
        :type timeout: int
        :return: IoTHubDeviceMethodResponse instance
        :rtype: IoTHubDeviceMethodResponse
        :raises: IoTHubDeviceMethodError if invoking the method failed
        """
        pass

    def invoke(self, device_id, module_id, method_name, method_payload, timeout):
        """Invokes the given method on the given module with the given payload

        :param device_id: The name (id) of the device associated with module_id
        :type device_id: str
        :param module_id: The name (id) of the module 
        :type module_id: str
        :param method_name: The name of the method to invoke
        :type method_name: str
        :param method_payload: The payload to use in the method
        :type method_payload: str
        :param timeout: The timeout to use to wait for the method return
        :type timeout: int
        :return: IoTHubDeviceMethodResponse instance
        :rtype: IoTHubDeviceMethodResponse
        :raises: IoTHubDeviceMethodError if invoking the method failed
        """
        pass


class IoTHubDeviceTwin:
    """IoTHubDeviceTwin instance is used to get and update device twin data from the IoTHub.
    """
    def __init__(self, connection_string):
        """Creates a IoTHubDeviceTwin instance using the IoTHub connection string.

        :param connection_string: IoTHub connection string
        :type connection_string: str
        """
        pass

    def __init__(self, service_client_auth_handle):
        """Creates an IoTHubDeviceTwin object using the given IoTHub service client authentication handle.

        :param service_client_auth_handle: IoTHubServiceClientAuth instance
        :type: IoTHubServiceClientAuth
        """
        pass

    def get_twin(self, device_id):
        """Gets the twin representation of the given device.
        
        :param device_id: The name (id) of the device
        :type device_id: str
        :return: The twin representation of the device
        :rtype: str (Json)
        :raises: IoTHubDeviceTwinError if getting the twin failed
        """
        pass

    def get_twin(self, device_id, module_id):
        """Gets the twin representation of the given module.
        
        :param device_id: The name (id) of the device associated with module_id
        :type device_id: str
        :param module_id: The name (id) of the module
        :type module_id: str
        :return: The twin representation of the module
        :rtype: str (Json)
        :raises: IoTHubDeviceTwinError if getting the twin failed
        """
        pass


    def update_twin(self, device_id, device_twin_json):
        """Updates the twin representation of the given device.

        :param device_id:  The name (id) of the device
        :type device_id: str
        :param device_twin_json: The twin representation of the device
        :type device_twin_json: str (Json)
        :return: The updated twin representation of the device
        :rtype: str (Json)
        :raises: IoTHubDeviceTwinError if the update failed
        """
        pass

    def update_twin(self, device_id, module_id, module_twin_json):
        """Updates the twin representation of the given module.
    
        :param device_id:  The name (id) of the device associated with module_id
        :type device_id: str
        :param module_id: The name (id) of the module
        :type module_id: str
        :param module_twin_json: The twin representation of the module
        :type module_twin_json: str (Json)
        :return: The updated twin representation of the module
        :rtype: str (Json)
        :raises: IoTHubDeviceTwinError if the update failed
        """
        pass


