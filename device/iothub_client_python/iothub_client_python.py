#!/usr/bin/env python

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

# Dummy API definitions of IotHub Device Client for generating API documentation

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


class IoTHubClientResult(Enum):
    OK = 0
    INVALID_ARG = 1
    ERROR = 2
    INVALID_SIZE = 3
    INDEFINITE_TIME = 4


class IoTHubClientStatus(Enum):
    IDLE = 0
    BUSY = 1


class IoTHubClientConfirmationResult(Enum):
    OK = 0
    BECAUSE_DESTROY = 1
    MESSAGE_TIMEOUT = 2
    ERROR = 3


class IoTHubMessageDispositionResult(Enum):
    ACCEPTED = 0
    REJECTED = 1
    ABANDONED = 2


class IoTHubMessageContent(Enum):
    BYTEARRAY = 0
    STRING = 1
    UNKNOWN = 2


class IoTHubConnectionStatus(Enum):
    AUTHENTICATED = 0
    UNAUTHENTICATED = 1


class IoTHubClientConnectionStatusReason(Enum):
    EXPIRED_SAS_TOKEN = 0
    DEVICE_DISABLED = 1
    BAD_CREDENTIAL = 2
    RETRY_EXPIRED = 3
    NO_NETWORK = 4
    COMMUNICATION_ERROR = 5
    CONNECTION_OK = 6


class IoTHubClientRetryPolicy(Enum):
    RETRY_NONE = 0
    RETRY_IMMEDIATE = 1
    RETRY_INTERVAL = 2
    RETRY_LINEAR_BACKOFF = 3
    RETRY_EXPONENTIAL_BACKOFF = 4
    RETRY_EXPONENTIAL_BACKOFF_WITH_JITTER = 5
    RETRY_RANDOM = 6


class IoTHubTwinUpdateState(Enum):
    COMPLETE = 0
    PARTIAL = 1


class IoTHubTransportProvider(Enum):
    HTTP = 0
    AMQP = 1
    MQTT = 2
    AMQP_WS = 3
    MQTT_WS = 4


class IoTHubClientFileUploadResult(Enum):
    OK = 0
    ERROR = 1


class IoTHubSecurityType(Enum):
    UNKNOWN = 0
    SAS = 1
    X509 = 2


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


class IoTHubClientError(IoTHubError):
    """IoTHubClient specific exception class, derived from IoTHubError.
    """
    pass


class GetRetryPolicyReturnValue:
    """Data structure to hold the return value of a IoTHubClient.get_retry_policy() call.

    :ivar retry_policy: The retry policy
    :type retry_policy: IoTHubClientRetryPolicy(Enum)
    :ivar retry_timeoutLimitInSeconds: The retry timeout limit in seconds
    :type retry_timeoutLimitInSeconds: int
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


class IoTHubMessageDiagnosticPropertyData:
    """IoTHubMessageDiagnosticPropertyData instance is used to hold
    a data structure for diagnostic property.

    :ivar diagnostic_id: The name of the diagnostic property
    :type diagnostic_id: str
    :ivar diagnostic_time_utc: The time of the diagnostic property (UTC time string)
    :type diagnostic_time_utc: str
    """

    def __init__(self, diagnostic_id, diagnostic_time_utc):
        """Creates an IoTHubMessageDiagnosticPropertyData instance and sets
        the diagnostic property name and time.

        :param diagnostic_id: The name of the diagnostic property
        :type diagnostic_id: str
        :param diagnostic_time_utc: The time of the diagnostic property (UTC time string)
        :type diagnostic_time_utc: str
        """
        pass


class IoTHubMessage:
    """IoTHubMessage instance is used to hold a message communicate with IoTHub.
    Users of the SDK should create an instance of this class using one of the
    constructor provided and use that instance with IoTHubClient.
    """

    def __init__(self, source_str):
        """Creates an IoTHubMessage instance and sets the message body to the content of
        the given string source.

        :param source_str: A string containing the message data
        :type source_str: str
        """
        pass

    def __init__(self, source_bytearray):
        """Creates an IoTHubMessage instance and sets the message body to the content of
        the given bytearray source.

        :param source_bytearray: A bytearray containing the message data
        :type source_bytearray: bytearray
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
        """
        pass

    @property
    def correlation_id(self):
        """Public attribute for correlation_id

        :return: The value of the correlation_id property of the message
        :rtype: str
        """
        pass

    def get_bytearray(self):
        """Gets the content of the message as a bytearray.

        :return: The content of the message
        :rtype: bytearray
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

    def get_content_type_system_property(self):
        """Gets the name of the content type as defined in the system property of the message.

        :return: The name of the content type
        :rtype: str
        """
        pass

    def set_content_type_system_property(self, content_type):
        """Sets the name of the content type to the system property of the message.

        :param content_type: The name of the content type
        :type content_type: str
        :return: The result of the operation
        :rtype: IoTHubMessageResult(Enum)
        """
        pass

    def get_content_encoding_system_property(self):
        """Gets the name of the encoding as defined in the system property of the message.

        :return: The name of the encoding
        :rtype: str
        """
        pass

    def set_content_encoding_system_property(self, content_encoding):
        """Sets the name of the content encoding to the system property of the message.

        :param content_encoding: The name of the content encoding
        :type content_encoding: str
        :return: The result of the operation
        :rtype: IoTHubMessageResult(Enum)
        """
        pass

    def get_diagnostic_property_data(self):
        """Gets the diagnostic property data (property name and creation time) from the message.

        :return: The struct containing the diagnostic data
        :rtype: IoTHubMessageDiagnosticPropertyData
        """
        pass

    def set_diagnostic_property_data(self, diagnostic_data):
        """Sets the diagnostic data property of the message.

        :param diagnostic_data: The diagnostic data struct
        :type diagnostic_data: IoTHubMessageDiagnosticPropertyData
        :return: The result of the operation
        :rtype: IoTHubMessageResult(Enum)
        """
        pass

    @property
    def input_name(self):
        """Public attribute for input_name.  Read-only.

        :return: The input name on which the message was sent, if there was one.
        :rtype: str
        """
        pass

    @property
    def output_name(self):
        """Public attribute for output_name.  Read-only.

        :return: The output name on which the message will be sent, if there was one.
        :rtype: str
        """
        pass

    @property
    def connection_device_id(self):
        """Public attribute for connection device id.  Read-only.

        :return: The the device Id from which this message was sent, if there is one.
        :rtype: str
        """
        pass

    @property
    def connection_device_id(self):
        """Public attribute for connection module id.  Read-only.

        :return: The the module Id from which this message was sent, if there is one.
        :rtype: str
        """
        pass


class DeviceMethodReturnValue:
    """Data structure to hold the return value for device method call.

    :ivar response: Response string
    :type response: str
    :ivar status: Arbitrary status value
    :type status: int
    """
    pass


class IoTHubConfig:
    def __init__(self, protocol, device_id, device_key, device_sas_token, iot_hub_name, iot_hub_suffix, protocol_gateway_host_name):
        """Creates an IoTHubConfig instance using the given protocol, deviceId, deviceKey, deviceSasToken,
        iotHubName, iotHubSuffix and protocolGatewayHostName

        :param protocol: Transport protocol used to connect to IoTHub
        :type protocol: IoTHubTransportProvider(Enum)
        :param device_id: Device ID (aka device name)
        :type device_id: str
        :param device_key: The device key used to authenticate the device
        :type device_key: str
        :param device_sas_token: The device SAS Token used to authenticate the device in place of device key
        :type device_sas_token: str
        :param iot_hub_name: The IoT Hub name to which the device is connecting
        :type iot_hub_name: str
        :param iot_hub_suffix: The suffix part of the IoTHub uri (e.g., private.azure-devices-int.net)
        :type iot_hub_suffix: str
        :param protocol_gateway_host_name: The hostname of the gateway used with HTTP
        :type protocol_gateway_host_name: srt
        """
        pass


class IoTHubTransport:
    def __init__(self, iothub_transport_provider, iothub_name, iothub_suffix):
        """Creates an IoTHubTransport instance using the given protocol and the name and suffix of the IoTHub.

        :param iothub_transport_provider: Transport protocol used to connect to IoTHub
        :type iothub_transport_provider: IoTHubTransportProvider(Enum)
        :param iothub_name: The IoT Hub name to which the device is connecting
        :type iothub_name: str
        :param iothub_suffix: The suffix part of the IoTHub uri (e.g., private.azure-devices-int.net).
        :type iothub_suffix: str
        :raises: IoTHubClientError if failed to create the transport
        """
        pass


class IoTHubClient:
    """IoTHubClient instance is used to connect a device with an Azure IoTHub.
    Users of the SDK should create an instance of this class using one of the 
    constructors provided and call member functions to communicate with IoTHub.
    Note that all parameters used to create this instance 
    are saved as instance attributes.
    """

    def __init__(self, connection_string, protocol):
        """Creates an IoTHubClient for communication with an existing
        IoTHub using the specified connection string and protocol parameter.

        :param connection_string: A connection string which encapsulates "device connect" permissions on an IoTHub
        :type connection_string: str
        :param protocol: Transport protocol used to connect to IoTHub
        :type protocol: IoTHubTransportProvider(Enum)
        :return IoTHubClient instance
        :rtype: IoTHubClient class
        :raises: IoTHubClientError if failed to create the client
        """
        pass

    def __init__(self, iothub_transport, iothub_config):
        """Creates an IoTHubClient for communication with an existing
        IoTHub using the specified transport and configuration parameter.
        This constructor used for shared transport scenario.

        :param iothub_transport: Transport instance to share.
        :type iothub_transport: IoTHubTransport class
        :param iothub_config: Configuration containing connection parameters
        :type iothub_config: IoTHubConfig class
        :return IoTHubClient instance
        :rtype: IoTHubClient class
        :raises: IoTHubClientError if failed to create the client
        """
        pass

    def __init__(self, iothub_uri, device_id, security_type, protocol):
        """Creates an IoTHubClient for communication with an existing
        IoTHub using the specified iothub_uri, device_id, security_type
        and protocol parameter.
        This constructor used in device provisioning scenario.

        :param iothub_uri: IoTHub hostname uri (received in the registration process)
        :type iothub_uri: str
        :param device_id: Device ID (aka device name)
        :type device_id: str
        :param security_type: Authentication type used in provisioning scenario
        :type security_type: IoTHubSecurityType(Enum)
        :param protocol: Transport protocol used to connect to IoTHub
        :type protocol: IoTHubTransportProvider(Enum)
        :return IoTHubClient instance
        :rtype: IoTHubClient class
        :raises: IoTHubClientError if failed to create the client
        """
        pass

    @property
    def protocol(self):
        """Getter for protocol attribute

        :return: Transport protocol used by this class
        :rtype: IoTHubTransportProvider(Enum)
        """
        pass

    def send_event_async(self, message, message_callback, user_context):
        """Asynchronous call to send the message to IoTHub.

        :param message: IoTHubMessage 
        :type message: IoTHubMessage class
        :param message_callback: Callable Python function
        :type message_callback: f(IoTHubMessage, IoTHubMessageResult, any)
        :param user_context: User specified context that will be provided to the callback
        :type user_context: any
        :raises: IoTHubClientError if the operation failed
        """
        pass

    def send_event_async(self, output_name, message, message_callback, user_context):
        """Asynchronous call to send the message to IoTHub to specific output.

        :param output_name: output to put the message on
        :type output_name: str
        :param message: IoTHubMessage 
        :type message: IoTHubMessage class
        :param message_callback: Callable Python function
        :type message_callback: f(IoTHubMessage, IoTHubMessageResult, any)
        :param user_context: User specified context that will be provided to the callback
        :type user_context: any
        :raises: IoTHubClientError if the operation failed
        """
        pass


    def set_message_callback(self, message_callback, user_context):
        """Sets up a callback function to be invoked when the device client received a message from IoTHub.

        :param message_callback: Callable Python function
        :type message_callback: f(IoTHubMessage, any)
        :param user_context: User specified context that will be provided to the callback
        :type user_context: any
        :raises: IoTHubClientError if the operation failed
        """
        pass

    def set_message_callback(self, input_name, message_callback, user_context):
        """Sets up a callback function to be invoked when the device client received a message from IoTHub on specified input.

        :param input_name: input to receive the message on
        :type input_name: str
        :param message_callback: Callable Python function
        :type message_callback: f(IoTHubMessage, any)
        :param user_context: User specified context that will be provided to the callback
        :type user_context: any
        :raises: IoTHubClientError if the operation failed
        """
        pass


    def set_connection_status_callback(self, connection_status_callback, user_context):
        """Sets up a callback function to be invoked representing the status of the connection to IOTHub.

        :param connection_status_callback: Callable Python function
        :type connection_status_callback: f(IoTHubConnectionStatus, IoTHubClientConnectionStatusReason, any)
        :param user_context: User specified context that will be provided to the callback
        :type user_context: any
        :raises: IoTHubClientError if the operation failed
        """
        pass

    def set_retry_policy(self, retry_policy, retry_timeout_limit_in_seconds):
        """Sets the retry policy to use to reconnect to IoT Hub when a connection drops.

        :param retry_policy: The policy to use to reconnect to IoT Hub when a connection drops
        :type retry_policy: IoTHubClientRetryPolicy(Enum)
        :param retry_timeout_limit_in_seconds: Maximum amount of time(seconds) to attempt reconnection
        :type retry_timeout_limit_in_seconds: int
        :raises: IoTHubClientError if the operation failed
        """
        pass

    def get_retry_policy(self):
        """Gets the retry policy has been used to reconnect to IoT Hub when a connection drops.

        :return: The policy and timout limit to use to reconnect to IoT Hub when a connection drops
        :rtype: GetRetryPolicyReturnValue class
        :raises: IoTHubClientError if the operation failed
        """
        pass

    def set_device_twin_callback(self, device_twin_callback, user_context):
        """Sets up a callback function to be invoked when the device client receives a twin state update.

        :param device_twin_callback: Callable Python function
        :type device_twin_callback: f(IoTHubTwinUpdateState, any, any)
        :param user_context: User specified context that will be provided to the callback
        :type user_context: any
        :raises: IoTHubClientError if the operation failed
        """
        pass

    def send_reported_state(self, reported_state, size, reported_state_callback, user_context):
        """Sends a report of the device's properties and their current values to IoTHub.

        :param reported_state: JSon string containing the device current state
        :type reported_state: str
        :param size: Length of the JSon string (len(str))
        :type size: int
        :param reported_state_callback: Callable Python function
        :type reported_state_callback: f(int, any)
        :param user_context: User specified context that will be provided to the callback
        :type user_context: any
        :raises: IoTHubClientError if the operation failed
        """
        pass

    def set_device_method_callback(self, device_method_callback, user_context):
        """Sets up a callback function for cloud to device method call.

        :param device_method_callback: Callable Python function
        :type device_method_callback: f(str, str, int, any, int, any)
        :param user_context: User specified context that will be provided to the callback
        :type user_context: any
        :raises: IoTHubClientError if the operation failed
        """
        pass

    def set_device_method_callback_ex(self, inbound_device_method_callback):
        """Sets up a callback function for cloud to device async method call.

        :param inbound_device_method_callback: Callable Python function
        :type inbound_device_method_callback: f(str, str, int, any, any)
        :raises: IoTHubClientError if the operation failed
        """
        pass

    def device_method_response(self, method_id, response, size, status_code):
        """Sends the response for cloud to device async method call.

        :param method_id: Identification of the async method called by IoTHub
        :type method_id: any
        :param response: Payload of the response
        :type response: str
        :param size: Length of the response (len(str))
        :type size: int
        :param status_code: Status code reported to IoTHub
        :type status_code: int
        :raises: IoTHubClientError if the operation failed
        """
        pass

    def set_option(self, option_name, option):
        """Sets the given runtime configuration option.
        The options that can be set via this API are:
            - name: timeout
            - value: long
              The maximum time in milliseconds a communication is allowed to use.
              This is only supported for the HTTP
              protocol as of now. When the HTTP protocol uses CURL, the meaning of
              the parameter is "total request time". When the HTTP protocol uses
              winhttp, the meaning is the same as the dwSendTimeout and dwReceiveTimeout parameters of the
              "https://msdn.microsoft.com/en-us/library/windows/desktop/aa384116(v=vs.85).aspx"
              WinHttpSetTimeouts API.

            - name: CURLOPT_LOW_SPEED_LIMIT
            - value: long
              Only available for HTTP protocol and only when CURL is used.
              It has the same meaning as CURL's option with the same name.

            - name: CURLOPT_LOW_SPEED_TIME
            - value: long
              Only available for HTTP protocol and only.
              when CURL is used. It has the same meaning as CURL's option with the same name.

            - name: CURLOPT_FORBID_REUSE
            - value: long
              Only available for HTTP protocol and only when CURL is used.
              It has the same meaning as CURL's option with the same name.

            - name: CURLOPT_FRESH_CONNECT
            - value: long
              Only available for HTTP protocol and only when CURL is used.
              It has the same meaning as CURL's option with the same name.

            - name: CURLOPT_VERBOSE
            - value: long
              Only available for HTTP protocol and only when CURL is used.
              It has the same meaning as CURL's option with the same name.

            - name: messageTimeout
            - value: long
              The maximum time in milliseconds until a message is timeouted.
              The time starts at IoTHubClient_SendEventAsync. By default, messages do not expire.

            - name: c2d_keep_alive_freq_secs
            - value: long
              The AMQP C2D keep alive interval in seconds.
              After the connection established the client requests the server to set the
              keep alive interval for given time.
              If it is not set then the default 240 sec applies.
              If it is set to zero the server will not send keep alive messages to the client.

        :param option_name: Name of the option to set
        :type option_name: str
        :param option: Value of the option to set
        :type option: any
        """
        pass

    def get_send_status(self):
        """Returns the current sending status of the IoTHub device client.

        :return: IoTHubClientStatus instance
        :rtype: IoTHubClientStatus(Enum)
        :raises: IoTHubClientError if the operation failed
        """
        pass

    def get_last_message_receive_time(self):
        """Returns the timestamp of the last message was received at the client.

        :return: Timestamp of the last message received
        :rtype: long
        """
        pass

    def upload_blob_async(self, destination_file_name, source, size, file_upload_callback, user_context):
        """Uploads data from memory to a file in Azure Blob Storage.

        :param destination_file_name: The name of the file to be created in Azure Blob Storage
        :type destination_file_name: str
        :param source: The source of the data
        :type source: str
        :param size: The length of the data
        :type size: int
        :param file_upload_callback: The callback to be invoked when the file upload operation has finished
        :type file_upload_callback: f(IoTHubClientFileUploadResult, any)
        :param user_context: User specified context that will be provided to the callback
        :type user_context: any
        :raises: IoTHubClientError if the operation failed
        """
        pass

