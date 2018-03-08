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
#include "iothub_service_client_auth.h"
#include "iothub_sc_version.h"
#include "iothub_registrymanager.h"
#include "iothub_messaging.h"
#include "iothub_devicemethod.h"
#include "iothub_devicetwin.h"
#include "iothubtransporthttp.h"
#include "iothubtransportamqp.h"

#define IMPORT_NAME iothub_service_client_mock

// "platform.h"

int platform_init(void)
{
    return 0;
}

void platform_deinit(void)
{
}

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
//
//// "iothub_client_version.h"
//
//const char* IoTHubxClient_GetVersionString(void)
//{
//    return IOTHUB_SDK_VERSION;
//}

// "iothub_message.h"

IOTHUB_MESSAGE_HANDLE mockMessageHandle = (IOTHUB_MESSAGE_HANDLE)0x12345678;
#define MOCKMESSAGESIZE 128
char mockBuffer[MOCKMESSAGESIZE] = { 0 };
char mockMessageId[MOCKMESSAGESIZE] = { 0 };
char mockCorrelationId[MOCKMESSAGESIZE] = { 0 };
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

void IoTHubMessage_Destroy(IOTHUB_MESSAGE_HANDLE iotHubMessageHandle)
{
    (void)iotHubMessageHandle;
}

//  singlylinkedlist.h
SINGLYLINKEDLIST_HANDLE mockSinglylinkedlistHandle = (SINGLYLINKEDLIST_HANDLE)0x12345678;
LIST_ITEM_HANDLE mockListItemHandle = (LIST_ITEM_HANDLE)0x12345678;

SINGLYLINKEDLIST_HANDLE singlylinkedlist_create()
{
    return mockSinglylinkedlistHandle;
}

void singlylinkedlist_destroy(SINGLYLINKEDLIST_HANDLE list)
{
    list = NULL;
}

int singlylinkedlist_remove(SINGLYLINKEDLIST_HANDLE list, LIST_ITEM_HANDLE item)
{
    (void)list;
    (void)item;
    return 0;
}

LIST_ITEM_HANDLE singlylinkedlist_get_head_item(SINGLYLINKEDLIST_HANDLE list)
{
    (void)list;
    return NULL;
}

LIST_ITEM_HANDLE singlylinkedlist_get_next_item(LIST_ITEM_HANDLE item_handle)
{
    (void)item_handle;
    return NULL;
}

const void* singlylinkedlist_item_get_value(LIST_ITEM_HANDLE item_handle)
{
    (void)item_handle;
    return NULL;
}

//  iothub_service_client_auth.h
IOTHUB_SERVICE_CLIENT_AUTH_HANDLE mockAuthHandle = (IOTHUB_SERVICE_CLIENT_AUTH_HANDLE)0x12345678;

IOTHUB_SERVICE_CLIENT_AUTH_HANDLE IoTHubServiceClientAuth_CreateFromConnectionString(const char* connectionString)
{
    (void)connectionString;
    return mockAuthHandle;
}

void IoTHubServiceClientAuth_Destroy(IOTHUB_SERVICE_CLIENT_AUTH_HANDLE serviceClientHandle)
{
    (void)serviceClientHandle;
}

//  iothub_registrymanager.h
IOTHUB_REGISTRYMANAGER_HANDLE mockRegistryManagerHandle = (IOTHUB_REGISTRYMANAGER_HANDLE)0x12345678;
 
IOTHUB_REGISTRYMANAGER_HANDLE IoTHubRegistryManager_Create(IOTHUB_SERVICE_CLIENT_AUTH_HANDLE serviceClientHandle)
{
    (void)serviceClientHandle;
    return mockRegistryManagerHandle;
}
 
void IoTHubRegistryManager_Destroy(IOTHUB_REGISTRYMANAGER_HANDLE registryManagerHandle)
{
    (void)registryManagerHandle;
}

 
IOTHUB_REGISTRYMANAGER_RESULT IoTHubRegistryManager_CreateDevice(IOTHUB_REGISTRYMANAGER_HANDLE registryManagerHandle, const IOTHUB_REGISTRY_DEVICE_CREATE* deviceCreate, IOTHUB_DEVICE* device)
{
    (void)registryManagerHandle, deviceCreate, device;
    return IOTHUB_REGISTRYMANAGER_OK;
}

IOTHUB_REGISTRYMANAGER_RESULT IoTHubRegistryManager_GetDevice(IOTHUB_REGISTRYMANAGER_HANDLE registryManagerHandle, const char* deviceId, IOTHUB_DEVICE* device)
{
    (void)registryManagerHandle, deviceId;
    device = NULL;
    return IOTHUB_REGISTRYMANAGER_OK;
}
 
IOTHUB_REGISTRYMANAGER_RESULT IoTHubRegistryManager_UpdateDevice(IOTHUB_REGISTRYMANAGER_HANDLE registryManagerHandle, IOTHUB_REGISTRY_DEVICE_UPDATE* deviceUpdate)
{
    (void)registryManagerHandle, deviceUpdate;
    return IOTHUB_REGISTRYMANAGER_OK;
}
 
IOTHUB_REGISTRYMANAGER_RESULT IoTHubRegistryManager_DeleteDevice(IOTHUB_REGISTRYMANAGER_HANDLE registryManagerHandle, const char* deviceId)
{
    (void)registryManagerHandle, deviceId;
    return IOTHUB_REGISTRYMANAGER_OK;
}

IOTHUB_REGISTRYMANAGER_RESULT IoTHubRegistryManager_GetDeviceList(IOTHUB_REGISTRYMANAGER_HANDLE registryManagerHandle, size_t numberOfDevices, SINGLYLINKEDLIST_HANDLE deviceList)
{
    (void)registryManagerHandle, numberOfDevices, deviceList;
    return IOTHUB_REGISTRYMANAGER_OK;
}
 
IOTHUB_REGISTRYMANAGER_RESULT IoTHubRegistryManager_GetStatistics(IOTHUB_REGISTRYMANAGER_HANDLE registryManagerHandle, IOTHUB_REGISTRY_STATISTICS* registryStatistics)
{
    (void)registryManagerHandle;
    registryStatistics = NULL;
    return IOTHUB_REGISTRYMANAGER_OK;
}

IOTHUB_REGISTRYMANAGER_RESULT IoTHubRegistryManager_CreateModule(IOTHUB_REGISTRYMANAGER_HANDLE registryManagerHandle, const IOTHUB_REGISTRY_MODULE_CREATE* moduleCreate, IOTHUB_MODULE* module)
{
    (void)registryManagerHandle, moduleCreate, module;
    return IOTHUB_REGISTRYMANAGER_OK;
}

IOTHUB_REGISTRYMANAGER_RESULT IoTHubRegistryManager_GetModule(IOTHUB_REGISTRYMANAGER_HANDLE registryManagerHandle, const char* deviceId, const char* moduleId, IOTHUB_MODULE* module)
{
    (void)registryManagerHandle, deviceId, moduleId, module;
    return IOTHUB_REGISTRYMANAGER_OK;
}

IOTHUB_REGISTRYMANAGER_RESULT IoTHubRegistryManager_UpdateModule(IOTHUB_REGISTRYMANAGER_HANDLE registryManagerHandle, IOTHUB_REGISTRY_MODULE_UPDATE* moduleUpdate)
{
    (void)registryManagerHandle, moduleUpdate;
    return IOTHUB_REGISTRYMANAGER_OK;
}

IOTHUB_REGISTRYMANAGER_RESULT IoTHubRegistryManager_DeleteModule(IOTHUB_REGISTRYMANAGER_HANDLE registryManagerHandle, const char* deviceId, const char* moduleId)
{
    (void)registryManagerHandle, deviceId, moduleId;
    return IOTHUB_REGISTRYMANAGER_OK;
}

IOTHUB_REGISTRYMANAGER_RESULT IoTHubRegistryManager_GetModuleList(IOTHUB_REGISTRYMANAGER_HANDLE registryManagerHandle, const char* deviceId, SINGLYLINKEDLIST_HANDLE moduleList)
{
    (void)registryManagerHandle, deviceId, moduleList;
    return IOTHUB_REGISTRYMANAGER_OK;
}

//  iothub_messaging.h
IOTHUB_MESSAGING_CLIENT_HANDLE mockMessagingHandle = (IOTHUB_MESSAGING_CLIENT_HANDLE)0x12345678;

IOTHUB_MESSAGING_CLIENT_HANDLE IoTHubMessaging_Create(IOTHUB_SERVICE_CLIENT_AUTH_HANDLE serviceClientHandle)
{
    (void)serviceClientHandle;
    return mockMessagingHandle;
}

void IoTHubMessaging_Destroy(IOTHUB_MESSAGING_CLIENT_HANDLE messagingClientHandle)
{
    (void)messagingClientHandle;
}

IOTHUB_MESSAGING_RESULT IoTHubMessaging_Open(IOTHUB_MESSAGING_CLIENT_HANDLE messagingClientHandle, IOTHUB_OPEN_COMPLETE_CALLBACK openCompleteCallback, void* userContextCallback)
{
    (void)messagingClientHandle, openCompleteCallback, userContextCallback;
    return IOTHUB_MESSAGING_OK;
}

void IoTHubMessaging_Close(IOTHUB_MESSAGING_CLIENT_HANDLE messagingClientHandle)
{
    (void)messagingClientHandle;
}

IOTHUB_MESSAGING_RESULT IoTHubMessaging_SendAsync(IOTHUB_MESSAGING_CLIENT_HANDLE messagingClientHandle, const char* deviceId, IOTHUB_MESSAGE_HANDLE message, IOTHUB_SEND_COMPLETE_CALLBACK sendCompleteCallback, void* userContextCallback)
{
    (void)messagingClientHandle, deviceId, message, sendCompleteCallback, userContextCallback;
    return IOTHUB_MESSAGING_OK;
}

IOTHUB_MESSAGING_RESULT IoTHubMessaging_SendAsyncModule(IOTHUB_MESSAGING_CLIENT_HANDLE messagingClientHandle, const char* deviceId, const char* moduleId, IOTHUB_MESSAGE_HANDLE message, IOTHUB_SEND_COMPLETE_CALLBACK sendCompleteCallback, void* userContextCallback)
{
    (void)messagingClientHandle, moduleId, deviceId, message, sendCompleteCallback, userContextCallback;
    return IOTHUB_MESSAGING_OK;
}

IOTHUB_MESSAGING_RESULT IoTHubMessaging_SetFeedbackMessageCallback(IOTHUB_MESSAGING_CLIENT_HANDLE messagingClientHandle, IOTHUB_FEEDBACK_MESSAGE_RECEIVED_CALLBACK feedbackMessageReceivedCallback, void* userContextCallback)
{
    (void)messagingClientHandle, feedbackMessageReceivedCallback, userContextCallback;
    return IOTHUB_MESSAGING_OK;
}

//  iothub_devicemethod.h
IOTHUB_SERVICE_CLIENT_DEVICE_METHOD_HANDLE mockDeviceMethodHandle = (IOTHUB_SERVICE_CLIENT_DEVICE_METHOD_HANDLE)0x12345678;

IOTHUB_SERVICE_CLIENT_DEVICE_METHOD_HANDLE IoTHubDeviceMethod_Create(IOTHUB_SERVICE_CLIENT_AUTH_HANDLE serviceClientHandle)
{
    (void)serviceClientHandle;
    return mockDeviceMethodHandle;
}

void  IoTHubDeviceMethod_Destroy(IOTHUB_SERVICE_CLIENT_DEVICE_METHOD_HANDLE serviceClientDeviceMethodHandle)
{
    (void)serviceClientDeviceMethodHandle;
}

IOTHUB_DEVICE_METHOD_RESULT IoTHubDeviceMethod_Invoke(IOTHUB_SERVICE_CLIENT_DEVICE_METHOD_HANDLE serviceClientDeviceMethodHandle, const char* deviceId, const char* methodName, const char* methodPayload, unsigned int timeout, int* responseStatus, unsigned char** responsePayload, size_t* responsePayloadSize)
{
    (void)serviceClientDeviceMethodHandle, deviceId, methodName, methodPayload, timeout;
    *responseStatus = 42;
    *responsePayload = (unsigned char *)"RESPONSE";
    *responsePayloadSize = 8;
    return IOTHUB_DEVICE_METHOD_OK;
}

IOTHUB_DEVICE_METHOD_RESULT IoTHubDeviceMethod_InvokeModule(IOTHUB_SERVICE_CLIENT_DEVICE_METHOD_HANDLE serviceClientDeviceMethodHandle, const char* deviceId, const char* moduleId,  const char* methodName, const char* methodPayload, unsigned int timeout, int* responseStatus, unsigned char** responsePayload, size_t* responsePayloadSize)
{
    (void)serviceClientDeviceMethodHandle, deviceId, moduleId, methodName, methodPayload, timeout;
    *responseStatus = 42;
    *responsePayload = (unsigned char *)"RESPONSE";
    *responsePayloadSize = 8;
    return IOTHUB_DEVICE_METHOD_OK;
}

//  iothub_devicetwin.h
IOTHUB_SERVICE_CLIENT_DEVICE_TWIN_HANDLE mockDeviceTwinHandle = (IOTHUB_SERVICE_CLIENT_DEVICE_TWIN_HANDLE)0x12345678;

IOTHUB_SERVICE_CLIENT_DEVICE_TWIN_HANDLE IoTHubDeviceTwin_Create(IOTHUB_SERVICE_CLIENT_AUTH_HANDLE serviceClientHandle)
{
    (void)serviceClientHandle;
    return mockDeviceTwinHandle;
}

void  IoTHubDeviceTwin_Destroy(IOTHUB_SERVICE_CLIENT_DEVICE_TWIN_HANDLE serviceClientDeviceTwinHandle)
{
    (void)serviceClientDeviceTwinHandle;
}

char*  IoTHubDeviceTwin_GetTwin(IOTHUB_SERVICE_CLIENT_DEVICE_TWIN_HANDLE serviceClientDeviceTwinHandle, const char* deviceId)
{
    (void)serviceClientDeviceTwinHandle, deviceId;
    return (char*)"";
}

char*  IoTHubDeviceTwin_UpdateTwin(IOTHUB_SERVICE_CLIENT_DEVICE_TWIN_HANDLE serviceClientDeviceTwinHandle, const char* deviceId, const char* deviceTwinJson)
{
    (void)serviceClientDeviceTwinHandle, deviceId, deviceTwinJson;
    return (char*)"";
}

char*  IoTHubDeviceTwin_GetModuleTwin(IOTHUB_SERVICE_CLIENT_DEVICE_TWIN_HANDLE serviceClientDeviceTwinHandle, const char* deviceId, const char* moduleId)
{
    (void)serviceClientDeviceTwinHandle, deviceId, moduleId;
    return (char*)"";
}

char*  IoTHubDeviceTwin_UpdateModuleTwin(IOTHUB_SERVICE_CLIENT_DEVICE_TWIN_HANDLE serviceClientDeviceTwinHandle, const char* deviceId, const char* moduleId, const char* moduleTwinJson)
{
    (void)serviceClientDeviceTwinHandle, deviceId, moduleId, moduleTwinJson;
    return (char*)"";
}

// "iothubtransporthttp.h"
TRANSPORT_PROVIDER *mockProtocol = (TRANSPORT_PROVIDER *)0x12345678;
extern "C" {
    const TRANSPORT_PROVIDER* HTTP_Protocol(void)
    {
        return mockProtocol;
    }

    // "iothubtransportamqp.h"

    const TRANSPORT_PROVIDER* AMQP_Protocol(void)
    {
        return mockProtocol;
    }
}/*extern "C"*/



