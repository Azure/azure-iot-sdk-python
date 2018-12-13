
// Copyright(c) Microsoft.All rights reserved.
// Licensed under the MIT license.See LICENSE file in the project root for full license information.

#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable:4244) /* This is because boost python has a cast issue in caller.hpp */
#endif

#include <boost/python.hpp>

#ifdef _MSC_VER
#pragma warning(pop)
#endif

#pragma warning(disable:4996) /* This is because of we need strncpy */

#include <string>
#include <vector>
#include <list>

#include "azure_c_shared_utility/platform.h"
#ifndef MACOSX
#include "azure_prov_client/iothub_security_factory.h"
#endif

#include "iothub_client.h"
#include "iothub_device_client.h"
#include "iothub_module_client.h"
#include "internal/iothub_client_edge.h"
#include "iothub_client_version.h"
#include "iothub_message.h"
#include "internal/iothubtransport.h"
#include "iothubtransporthttp.h"
#include "iothubtransportamqp.h"
#include "iothubtransportmqtt.h"

#ifdef USE_WEBSOCKETS
#include "iothubtransportamqp_websockets.h"
#include "iothubtransportmqtt_websockets.h"
#endif

#define IMPORT_NAME iothub_client_mock

// "platform.h"

int platform_init(void)
{
    return 0;
}

void platform_deinit(void)
{
}

#ifndef MACOSX
int iothub_security_init(IOTHUB_SECURITY_TYPE sec_type)
{
    (void)sec_type;
    return 0;
}

void iothub_security_deinit(void)
{
}
#endif

// "map.h"

MAP_HANDLE mockMapHandle = (MAP_HANDLE)0x12345678;

#define MOCKMAPSIZE 128
#define MOCKARRAYSIZE 8
MAP_FILTER_CALLBACK mockFilterFunc = NULL;
char mockKey[MOCKMAPSIZE] = { 0 };
char *mockKeyArray[MOCKARRAYSIZE] = { mockKey };
char mockValue[MOCKMAPSIZE] = { 0 };
char *mockValueArray[MOCKARRAYSIZE] = { mockValue };

MAP_HANDLE Map_Create(MAP_FILTER_CALLBACK mapFilterFunc)
{
    // reset mock buffers
    memset(mockKey, 0, sizeof(mockKey));
    memset(mockValue, 0, sizeof(mockValue));
    mockFilterFunc = mapFilterFunc;
    return mockMapHandle;
}

void Map_Destroy(MAP_HANDLE handle)
{
    (void)handle;
}

MAP_HANDLE Map_Clone(MAP_HANDLE handle)
{
    (void)handle;
    return mockMapHandle;
}

MAP_RESULT Map_Add(MAP_HANDLE handle, const char* key, const char* value)
{
    MAP_RESULT result = MAP_OK;

    (void)handle;
    if (mockFilterFunc != NULL)
    {
        result = mockFilterFunc(key, value) ? MAP_FILTER_REJECT : MAP_OK;
    }

    if (result == MAP_OK)
    {
        if (strcmp(mockKey, key) == 0)
        {
            result = MAP_KEYEXISTS;
        }
        else
        {
            strcpy(mockKey, key);
            strcpy(mockValue, value);
        }
    }
    return result;
}

MAP_RESULT Map_AddOrUpdate(MAP_HANDLE handle, const char* key, const char* value)
{
    MAP_RESULT result = MAP_OK;

    (void)handle;
    if (mockFilterFunc != NULL)
    {
        result = mockFilterFunc(key, value) ? MAP_FILTER_REJECT : MAP_OK;
    }

    if (result == MAP_OK)
    {
        strcpy(mockKey, key);
        strcpy(mockValue, value);
    }

    return result;
}

MAP_RESULT Map_Delete(MAP_HANDLE handle, const char* key)
{
    MAP_RESULT result = MAP_KEYNOTFOUND;

    (void)handle;
    if (strcmp(mockKey, key) == 0)
    {
        memset(mockKey, 0, sizeof(mockKey));
        memset(mockValue, 0, sizeof(mockValue));
        result = MAP_OK;
    }

    return result;
}

MAP_RESULT Map_ContainsKey(MAP_HANDLE handle, const char* key, bool* keyExists)
{
    (void)handle;
    *keyExists = strcmp(mockKey, key) == 0;
    return MAP_OK;
}

MAP_RESULT Map_ContainsValue(MAP_HANDLE handle, const char* value, bool* valueExists)
{
    (void)handle;
    *valueExists = strcmp(mockValue, value) == 0;
    return MAP_OK;
}

const char* Map_GetValueFromKey(MAP_HANDLE handle, const char* key)
{
    (void)handle;
    if (strcmp(mockKey, key) == 0)
    {
        return mockValue;
    }
    return NULL;
}

MAP_RESULT Map_GetInternals(MAP_HANDLE handle, const char*const** keys, const char*const** values, size_t* count)
{
    (void)handle;
    *count = 0;
    *keys = mockKeyArray;
    *values = mockValueArray;

    if (*mockKey != '\0')
    {
        *count = 1;
    }

    return MAP_OK;
}

// "iothubtransport.h"

TRANSPORT_HANDLE mockTransportHandle = (TRANSPORT_HANDLE)0x12345678;

TRANSPORT_HANDLE IoTHubTransport_Create(IOTHUB_CLIENT_TRANSPORT_PROVIDER protocol, const char* iotHubName, const char* iotHubSuffix)
{
    (void)protocol;
    (void)iotHubName;
    (void)iotHubSuffix;
    return mockTransportHandle;
}

void IoTHubTransport_Destroy(TRANSPORT_HANDLE transportHandle)
{
    (void)transportHandle;
}

// "iothub_client.h"

IOTHUB_CLIENT_HANDLE mockClientHandle = (IOTHUB_CLIENT_HANDLE)0x12345678;


//
//  IOTHUB_CLIENT
//
IOTHUB_CLIENT_HANDLE IoTHubClient_CreateFromConnectionString(const char* connectionString, IOTHUB_CLIENT_TRANSPORT_PROVIDER protocol)
{
    (void)connectionString;
    (void)protocol;
    return mockClientHandle;
}

IOTHUB_CLIENT_HANDLE IoTHubClient_Create(const IOTHUB_CLIENT_CONFIG* config)
{
    (void)config;
    return mockClientHandle;
}

IOTHUB_CLIENT_HANDLE IoTHubClient_CreateWithTransport(TRANSPORT_HANDLE transportHandle, const IOTHUB_CLIENT_CONFIG* config)
{
    (void)transportHandle;
    (void)config;
    return mockClientHandle;
}

IOTHUB_CLIENT_HANDLE IoTHubClient_CreateFromDeviceAuth(const char* iothub_uri, const char* device_id, IOTHUB_CLIENT_TRANSPORT_PROVIDER protocol)
{
    (void)iothub_uri;
    (void)device_id;
    (void)protocol;
    return mockClientHandle;
}

void IoTHubClient_Destroy(IOTHUB_CLIENT_HANDLE iotHubClientHandle)
{
    (void)iotHubClientHandle;
}

IOTHUB_CLIENT_RESULT IoTHubClient_SendEventAsync(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_MESSAGE_HANDLE eventMessageHandle, IOTHUB_CLIENT_EVENT_CONFIRMATION_CALLBACK eventConfirmationCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)eventMessageHandle;
    (void)eventConfirmationCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubClient_GetSendStatus(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_STATUS *iotHubClientStatus)
{
    (void)iotHubClientHandle;
    (void)iotHubClientStatus;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubClient_SetMessageCallback(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_MESSAGE_CALLBACK_ASYNC messageCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)messageCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubClient_SetConnectionStatusCallback(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_CONNECTION_STATUS_CALLBACK connectionStatusCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)connectionStatusCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubClient_SetRetryPolicy(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_RETRY_POLICY retryPolicy, size_t retryTimeoutLimitInSeconds)
{
    (void)iotHubClientHandle;
    (void)retryPolicy;
    (void)retryTimeoutLimitInSeconds;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubClient_GetRetryPolicy(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_RETRY_POLICY* retryPolicy, size_t* retryTimeoutLimitInSeconds)
{
    (void)iotHubClientHandle;
    (void)retryPolicy;
    (void)retryTimeoutLimitInSeconds;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubClient_SetDeviceTwinCallback(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_DEVICE_TWIN_CALLBACK deviceTwinCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)deviceTwinCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubClient_SendReportedState(IOTHUB_CLIENT_HANDLE iotHubClientHandle, const unsigned char* reportedState, size_t size ,  IOTHUB_CLIENT_REPORTED_STATE_CALLBACK reportedStateCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)reportedState;
    (void)size;
    (void)reportedStateCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubClient_SetDeviceMethodCallback(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_DEVICE_METHOD_CALLBACK_ASYNC deviceMethodCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)deviceMethodCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubClient_SetDeviceMethodCallback_Ex(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_INBOUND_DEVICE_METHOD_CALLBACK inboundDeviceMethodCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)inboundDeviceMethodCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubClient_DeviceMethodResponse(IOTHUB_CLIENT_HANDLE iotHubClientHandle, METHOD_HANDLE methodId, const unsigned char* response, size_t respSize, int statusCode)
{
    (void)iotHubClientHandle;
    (void)methodId;
    (void)response;
    (void)respSize;
    (void)statusCode;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubClient_GetLastMessageReceiveTime(IOTHUB_CLIENT_HANDLE iotHubClientHandle, time_t* lastMessageReceiveTime)
{
    (void)iotHubClientHandle;
    (void)lastMessageReceiveTime;
    return IOTHUB_CLIENT_INDEFINITE_TIME;
}

IOTHUB_CLIENT_RESULT IoTHubClient_SetOption(IOTHUB_CLIENT_HANDLE iotHubClientHandle, const char* optionName, const void* value)
{
    (void)iotHubClientHandle;
    (void)optionName;
    (void)value;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubClient_UploadToBlobAsync(IOTHUB_CLIENT_HANDLE iotHubClientHandle, const char* destinationFileName, const unsigned char* source, size_t size, IOTHUB_CLIENT_FILE_UPLOAD_CALLBACK iotHubClientFileUploadCallback, void* context)
{
    (void)iotHubClientHandle;
    (void)destinationFileName;
    (void)source;
    (void)size;
    (void)iotHubClientFileUploadCallback;
    (void)context;
    return IOTHUB_CLIENT_OK;
}

//
//  IOTHUB_DEVICE_CLIENT
//

IOTHUB_CLIENT_HANDLE IoTHubDeviceClient_CreateFromConnectionString(const char* connectionString, IOTHUB_CLIENT_TRANSPORT_PROVIDER protocol)
{
    (void)connectionString;
    (void)protocol;
    return mockClientHandle;
}

IOTHUB_CLIENT_HANDLE IoTHubDeviceClient_Create(const IOTHUB_CLIENT_CONFIG* config)
{
    (void)config;
    return mockClientHandle;
}

IOTHUB_CLIENT_HANDLE IoTHubDeviceClient_CreateWithTransport(TRANSPORT_HANDLE transportHandle, const IOTHUB_CLIENT_CONFIG* config)
{
    (void)transportHandle;
    (void)config;
    return mockClientHandle;
}

IOTHUB_CLIENT_HANDLE IoTHubDeviceClient_CreateFromDeviceAuth(const char* iothub_uri, const char* device_id, IOTHUB_CLIENT_TRANSPORT_PROVIDER protocol)
{
    (void)iothub_uri;
    (void)device_id;
    (void)protocol;
    return mockClientHandle;
}

void IoTHubDeviceClient_Destroy(IOTHUB_CLIENT_HANDLE iotHubClientHandle)
{
    (void)iotHubClientHandle;
}

IOTHUB_CLIENT_RESULT IoTHubDeviceClient_SendEventAsync(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_MESSAGE_HANDLE eventMessageHandle, IOTHUB_CLIENT_EVENT_CONFIRMATION_CALLBACK eventConfirmationCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)eventMessageHandle;
    (void)eventConfirmationCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubDeviceClient_GetSendStatus(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_STATUS *iotHubClientStatus)
{
    (void)iotHubClientHandle;
    (void)iotHubClientStatus;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubDeviceClient_SetMessageCallback(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_MESSAGE_CALLBACK_ASYNC messageCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)messageCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubDeviceClient_SetConnectionStatusCallback(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_CONNECTION_STATUS_CALLBACK connectionStatusCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)connectionStatusCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubDeviceClient_SetRetryPolicy(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_RETRY_POLICY retryPolicy, size_t retryTimeoutLimitInSeconds)
{
    (void)iotHubClientHandle;
    (void)retryPolicy;
    (void)retryTimeoutLimitInSeconds;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubDeviceClient_GetRetryPolicy(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_RETRY_POLICY* retryPolicy, size_t* retryTimeoutLimitInSeconds)
{
    (void)iotHubClientHandle;
    (void)retryPolicy;
    (void)retryTimeoutLimitInSeconds;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubDeviceClient_SetDeviceTwinCallback(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_DEVICE_TWIN_CALLBACK deviceTwinCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)deviceTwinCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubDeviceClient_SendReportedState(IOTHUB_CLIENT_HANDLE iotHubClientHandle, const unsigned char* reportedState, size_t size ,  IOTHUB_CLIENT_REPORTED_STATE_CALLBACK reportedStateCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)reportedState;
    (void)size;
    (void)reportedStateCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubDeviceClient_SetDeviceMethodCallback(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_DEVICE_METHOD_CALLBACK_ASYNC deviceMethodCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)deviceMethodCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubDeviceClient_DeviceMethodResponse(IOTHUB_CLIENT_HANDLE iotHubClientHandle, METHOD_HANDLE methodId, const unsigned char* response, size_t respSize, int statusCode)
{
    (void)iotHubClientHandle;
    (void)methodId;
    (void)response;
    (void)respSize;
    (void)statusCode;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubDeviceClient_GetLastMessageReceiveTime(IOTHUB_CLIENT_HANDLE iotHubClientHandle, time_t* lastMessageReceiveTime)
{
    (void)iotHubClientHandle;
    (void)lastMessageReceiveTime;
    return IOTHUB_CLIENT_INDEFINITE_TIME;
}

IOTHUB_CLIENT_RESULT IoTHubDeviceClient_SetOption(IOTHUB_CLIENT_HANDLE iotHubClientHandle, const char* optionName, const void* value)
{
    (void)iotHubClientHandle;
    (void)optionName;
    (void)value;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubDeviceClient_UploadToBlobAsync(IOTHUB_CLIENT_HANDLE iotHubClientHandle, const char* destinationFileName, const unsigned char* source, size_t size, IOTHUB_CLIENT_FILE_UPLOAD_CALLBACK iotHubClientFileUploadCallback, void* context)
{
    (void)iotHubClientHandle;
    (void)destinationFileName;
    (void)source;
    (void)size;
    (void)iotHubClientFileUploadCallback;
    (void)context;
    return IOTHUB_CLIENT_OK;
}

//
//  IOTHUB_MODULE_CLIENT
//
IOTHUB_MODULE_CLIENT_HANDLE IoTHubModuleClient_CreateFromConnectionString(const char* connectionString, IOTHUB_CLIENT_TRANSPORT_PROVIDER protocol)
{
    (void)connectionString;
    (void)protocol;
    return (IOTHUB_MODULE_CLIENT_HANDLE)mockClientHandle;
}

void IoTHubModuleClient_Destroy(IOTHUB_CLIENT_HANDLE iotHubClientHandle)
{
    (void)iotHubClientHandle;
}

IOTHUB_CLIENT_RESULT IoTHubModuleClient_SendEventAsync(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_MESSAGE_HANDLE eventMessageHandle, IOTHUB_CLIENT_EVENT_CONFIRMATION_CALLBACK eventConfirmationCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)eventMessageHandle;
    (void)eventConfirmationCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubModuleClient_GetSendStatus(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_STATUS *iotHubClientStatus)
{
    (void)iotHubClientHandle;
    (void)iotHubClientStatus;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubModuleClient_SetMessageCallback(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_MESSAGE_CALLBACK_ASYNC messageCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)messageCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubModuleClient_SetConnectionStatusCallback(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_CONNECTION_STATUS_CALLBACK connectionStatusCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)connectionStatusCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubModuleClient_SetRetryPolicy(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_RETRY_POLICY retryPolicy, size_t retryTimeoutLimitInSeconds)
{
    (void)iotHubClientHandle;
    (void)retryPolicy;
    (void)retryTimeoutLimitInSeconds;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubModuleClient_GetRetryPolicy(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_RETRY_POLICY* retryPolicy, size_t* retryTimeoutLimitInSeconds)
{
    (void)iotHubClientHandle;
    (void)retryPolicy;
    (void)retryTimeoutLimitInSeconds;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubModuleClient_SetModuleTwinCallback(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_DEVICE_TWIN_CALLBACK moduleTwinCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)moduleTwinCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubModuleClient_SendReportedState(IOTHUB_CLIENT_HANDLE iotHubClientHandle, const unsigned char* reportedState, size_t size ,  IOTHUB_CLIENT_REPORTED_STATE_CALLBACK reportedStateCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)reportedState;
    (void)size;
    (void)reportedStateCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubModuleClient_SetModuleMethodCallback(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_CLIENT_DEVICE_METHOD_CALLBACK_ASYNC moduleMethodCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)moduleMethodCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubModuleClient_GetLastMessageReceiveTime(IOTHUB_CLIENT_HANDLE iotHubClientHandle, time_t* lastMessageReceiveTime)
{
    (void)iotHubClientHandle;
    (void)lastMessageReceiveTime;
    return IOTHUB_CLIENT_INDEFINITE_TIME;
}

IOTHUB_CLIENT_RESULT IoTHubModuleClient_SetOption(IOTHUB_CLIENT_HANDLE iotHubClientHandle, const char* optionName, const void* value)
{
    (void)iotHubClientHandle;
    (void)optionName;
    (void)value;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubModuleClient_SendEventToOutputAsync(IOTHUB_CLIENT_HANDLE iotHubClientHandle, IOTHUB_MESSAGE_HANDLE eventMessageHandle, const char* outputName, IOTHUB_CLIENT_EVENT_CONFIRMATION_CALLBACK eventConfirmationCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)eventMessageHandle;
    (void)outputName;
    (void)eventConfirmationCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubModuleClient_SetInputMessageCallback(IOTHUB_CLIENT_HANDLE iotHubClientHandle, const char* inputName, IOTHUB_CLIENT_MESSAGE_CALLBACK_ASYNC eventHandlerCallback, void* userContextCallback)
{
    (void)iotHubClientHandle;
    (void)inputName;
    (void)eventHandlerCallback;
    (void)userContextCallback;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubModuleClient_DeviceMethodInvokeAsync(IOTHUB_MODULE_CLIENT_HANDLE iotHubModuleClientHandle, const char* deviceId, const char* methodName, const char* methodPayload, unsigned int timeout, IOTHUB_METHOD_INVOKE_CALLBACK methodInvokeCallback, void* context)
{
    (void)iotHubModuleClientHandle;
    (void)deviceId;
    (void)methodName;
    (void)methodPayload;
    (void)timeout;
    (void)methodInvokeCallback;
    (void)context;
    return IOTHUB_CLIENT_OK;
}

IOTHUB_CLIENT_RESULT IoTHubModuleClient_ModuleMethodInvokeAsync(IOTHUB_MODULE_CLIENT_HANDLE iotHubModuleClientHandle, const char* deviceId, const char* moduleId, const char* methodName, const char* methodPayload, unsigned int timeout, IOTHUB_METHOD_INVOKE_CALLBACK methodInvokeCallback, void* context)
{
    (void)iotHubModuleClientHandle;
    (void)deviceId;
    (void)moduleId;
    (void)methodName;
    (void)methodPayload;
    (void)timeout;
    (void)methodInvokeCallback;
    (void)context;
    return IOTHUB_CLIENT_OK;
}


// "iothub_client_version.h"

const char* IoTHubClient_GetVersionString(void)
{
    return IOTHUB_SDK_VERSION;
}

// "iothub_message.h"

IOTHUB_MESSAGE_HANDLE mockMessageHandle = (IOTHUB_MESSAGE_HANDLE)0x12345678;
#define MOCKMESSAGESIZE 128
char mockBuffer[MOCKMESSAGESIZE] = { 0 };
char mockMessageId[MOCKMESSAGESIZE] = { 0 };
char mockCorrelationId[MOCKMESSAGESIZE] = { 0 };
// Setter functions for mock values below are not plumbed up to Python layer, so hard-code data.
const char* mockInputName = "python-testmockInput";
const char* mockOutputName = "python-testmockOutput";
const char* mockConnectionModuleId = "python-testmockConnectionModuleId";
const char* mockConnectionDeviceId = "python-testmockConnectionDeviceId";

size_t mockSize = 0;
bool mockString = false;

IOTHUB_MESSAGE_HANDLE IoTHubMessage_CreateFromByteArray(const unsigned char* byteArray, size_t size)
{
    mockSize = size > MOCKMESSAGESIZE ? MOCKMESSAGESIZE : size;
    memcpy(mockBuffer, byteArray, mockSize);
    mockString = false;
    return mockMessageHandle;
}

IOTHUB_MESSAGE_HANDLE IoTHubMessage_CreateFromString(const char* source)
{
    mockString = true;
    (void)strncpy(mockBuffer, source, MOCKMESSAGESIZE);
    return mockMessageHandle;
}

IOTHUB_MESSAGE_HANDLE IoTHubMessage_Clone(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle)
{
    (void)iotHubMessageHandle;
    return mockMessageHandle;
}

IOTHUB_MESSAGE_RESULT IoTHubMessage_GetByteArray(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle, const unsigned char** buffer, size_t* size)
{
    (void)iotHubMessageHandle;
    if (mockString)
    {
        return IOTHUB_MESSAGE_INVALID_TYPE;
    }
    *buffer = (unsigned char*)mockBuffer;
    *size = mockSize;
    return IOTHUB_MESSAGE_OK;
}

const char* IoTHubMessage_GetString(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle)
{
    (void)iotHubMessageHandle;
    if (!mockString)
    {
        return NULL;
    }
    return mockBuffer;
}

IOTHUBMESSAGE_CONTENT_TYPE IoTHubMessage_GetContentType(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle)
{
    (void)iotHubMessageHandle;
    return mockString ? IOTHUBMESSAGE_STRING : IOTHUBMESSAGE_BYTEARRAY;
}


IOTHUB_MESSAGE_RESULT IoTHubMessage_SetContentTypeSystemProperty(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle, const char* contentType)
{
    (void)iotHubMessageHandle;
    (void)contentType;
    return IOTHUB_MESSAGE_OK;
}

const char* IoTHubMessage_GetContentTypeSystemProperty(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle)
{
    (void)iotHubMessageHandle;
    if (!mockString)
    {
        return NULL;
    }
    return mockBuffer;
}


IOTHUB_MESSAGE_RESULT IoTHubMessage_SetContentEncodingSystemProperty(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle, const char* contentEncoding)
{
    (void)iotHubMessageHandle;
    (void)contentEncoding;
    return IOTHUB_MESSAGE_OK;
}

const char* IoTHubMessage_GetContentEncodingSystemProperty(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle)
{
    (void)iotHubMessageHandle;
    if (!mockString)
    {
        return NULL;
    }
    return mockBuffer;
}

const IOTHUB_MESSAGE_DIAGNOSTIC_PROPERTY_DATA* IoTHubMessage_GetDiagnosticPropertyData(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle)
{
    (void)iotHubMessageHandle;
    return NULL;
}

IOTHUB_MESSAGE_RESULT IoTHubMessage_SetDiagnosticPropertyData(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle, const IOTHUB_MESSAGE_DIAGNOSTIC_PROPERTY_DATA* diagnosticData)
{
    (void)iotHubMessageHandle;
    (void)diagnosticData;
    return IOTHUB_MESSAGE_OK;
}

MAP_HANDLE IoTHubMessage_Properties(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle)
{
    (void)iotHubMessageHandle;
    return mockMapHandle;
}

const char* IoTHubMessage_GetMessageId(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle)
{
    (void)iotHubMessageHandle;
    if (*mockMessageId == '\0')
    {
        return NULL;
    }
    return mockMessageId;
}

IOTHUB_MESSAGE_RESULT IoTHubMessage_SetMessageId(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle, const char* messageId)
{
    (void)iotHubMessageHandle;
    (void)strncpy(mockMessageId, messageId, MOCKMESSAGESIZE);
    return IOTHUB_MESSAGE_OK;
}

const char* IoTHubMessage_GetCorrelationId(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle)
{
    (void)iotHubMessageHandle;
    if (*mockCorrelationId == '\0')
    {
        return NULL;
    }
    return mockCorrelationId;
}

IOTHUB_MESSAGE_RESULT IoTHubMessage_SetCorrelationId(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle, const char* correlationId)
{
    (void)iotHubMessageHandle;
    (void)strncpy(mockCorrelationId, correlationId, MOCKMESSAGESIZE);
    return IOTHUB_MESSAGE_OK;
}

const char* IoTHubMessage_GetOutputName(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle)
{
    (void)iotHubMessageHandle;
    return mockOutputName;
}

const char* IoTHubMessage_GetInputName(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle)
{
    (void)iotHubMessageHandle;
    return mockInputName;
}

const char* IoTHubMessage_GetConnectionModuleId(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle)
{
    (void)iotHubMessageHandle;
    return mockConnectionModuleId;
}

const char* IoTHubMessage_GetConnectionDeviceId(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle)
{
    (void)iotHubMessageHandle;
    return mockConnectionDeviceId;
}

void IoTHubMessage_Destroy(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle)
{
    (void)iotHubMessageHandle;
}

IOTHUB_MODULE_CLIENT_HANDLE IoTHubModuleClient_CreateFromEnvironment(IOTHUB_CLIENT_TRANSPORT_PROVIDER protocol)
{
    (void)protocol;
    return (IOTHUB_MODULE_CLIENT_HANDLE)mockMessageHandle;
}

TRANSPORT_PROVIDER *mockProtocol = (TRANSPORT_PROVIDER *)0x12345678;
extern "C"
{
    // "iothubtransporthttp.h"
    const TRANSPORT_PROVIDER* HTTP_Protocol(void)
    {
        return mockProtocol;
    }

    // "iothubtransportamqp.h"

    const TRANSPORT_PROVIDER* AMQP_Protocol(void)
    {
        return mockProtocol;
    }

    // "iothubtransportmqtt.h"

    const TRANSPORT_PROVIDER* MQTT_Protocol(void)
    {
        return mockProtocol;
    }

#ifdef USE_WEBSOCKETS

    // "iothubtransportamqp_webscokets.h"

    const TRANSPORT_PROVIDER* AMQP_Protocol_over_WebSocketsTls(void)
    {
        return mockProtocol;
    }

    // "iothubtransportmqtt_websockets.h"

    const TRANSPORT_PROVIDER* MQTT_WebSocket_Protocol(void)
    {
        return mockProtocol;
    }
#endif

}/*extern "C"*/
