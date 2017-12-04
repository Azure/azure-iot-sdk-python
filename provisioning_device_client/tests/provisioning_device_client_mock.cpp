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
#include "azure_prov_client/prov_device_client.h"
#include "azure_prov_client/prov_transport.h"
#include "azure_prov_client/prov_security_factory.h"

#if USE_HTTP
#include "azure_prov_client/prov_transport_http_client.h"
#endif

#if USE_AMQP
#include "azure_prov_client/prov_transport_amqp_client.h"
#include "azure_prov_client/prov_transport_amqp_ws_client.h"
#endif

#if USE_MQTT
#include "azure_prov_client/prov_transport_mqtt_client.h"
#include "azure_prov_client/prov_transport_mqtt_ws_client.h"
#endif

#define IMPORT_NAME provisioning_device_client_mock

int platform_init(void)
{
    return 0;
}

void platform_deinit(void)
{
}

int prov_dev_security_init(SECURE_DEVICE_TYPE hsm_type)
{
    (void*)hsm_type;
    return 0;
}

void prov_dev_security_deinit(void)
{
}

PROV_DEVICE_HANDLE mockProvDevHandle = (PROV_DEVICE_HANDLE)0x12345678;

PROV_DEVICE_HANDLE Prov_Device_Create(const char* uri, const char* id_scope, PROV_DEVICE_TRANSPORT_PROVIDER_FUNCTION protocol)
{
    (void*)uri;
    (void*)id_scope;
    (void*)protocol;
    return mockProvDevHandle;
}

void Prov_Device_Destroy(PROV_DEVICE_HANDLE prov_device_handle)
{
    (void*)prov_device_handle;
    return;
}

PROV_DEVICE_RESULT Prov_Device_Register_Device(PROV_DEVICE_HANDLE prov_device_handle, PROV_DEVICE_CLIENT_REGISTER_DEVICE_CALLBACK register_callback, void* user_context, PROV_DEVICE_CLIENT_REGISTER_STATUS_CALLBACK register_status_callback, void* status_user_context)
{
    (void*)prov_device_handle;
    (void*)register_callback;
    (void*)user_context;
    (void*)register_status_callback;
    (void*)status_user_context;
    return PROV_DEVICE_RESULT_OK;
}

PROV_DEVICE_RESULT Prov_Device_SetOption(PROV_DEVICE_HANDLE prov_device_handle, const char* optionName, const void* value)
{
    (void*)prov_device_handle;
    (void*)optionName;
    (void*)value;
    return PROV_DEVICE_RESULT_OK;
}

const char* Prov_Device_GetVersionString()
{
    return (char*)"";
}

PROV_DEVICE_TRANSPORT_PROVIDER* mockProtocol = (PROV_DEVICE_TRANSPORT_PROVIDER *)0x12345678;
extern "C" 
{
    // azure_prov_client/prov_transport_http_client.h
    const PROV_DEVICE_TRANSPORT_PROVIDER* Prov_Device_HTTP_Protocol(void)
    {
        return mockProtocol;
    }

    // azure_prov_client/prov_transport_amqp_client.h
    const PROV_DEVICE_TRANSPORT_PROVIDER* Prov_Device_AMQP_Protocol(void)
    {
        return mockProtocol;
    }

    // azure_prov_client/prov_transport_mqtt_client.h
    const PROV_DEVICE_TRANSPORT_PROVIDER* Prov_Device_MQTT_Protocol(void)
    {
        return mockProtocol;
    }

#ifdef USE_WEBSOCKETS

    // azure_prov_client/prov_transport_amqp_ws_client.h
    const PROV_DEVICE_TRANSPORT_PROVIDER* Prov_Device_AMQP_WS_Protocol(void)
    {
        return mockProtocol;
    }

    // azure_prov_client/prov_transport_mqtt_ws_client.h
    const PROV_DEVICE_TRANSPORT_PROVIDER* Prov_Device_MQTT_WS_Protocol(void)
    {
        return mockProtocol;
    }
#endif

}/*extern "C"*/



