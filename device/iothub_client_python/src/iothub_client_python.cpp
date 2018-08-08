

// Copyright(c) Microsoft.All rights reserved.
// Licensed under the MIT license.See LICENSE file in the project root for full license information.

#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable:4459 4100 4121 4244) /* This is because boost python has a self variable that hides a global */
#endif

#include <boost/python.hpp>

#ifdef _MSC_VER
#pragma warning(pop)
#endif

#include <string>
#include <vector>
#include <list>

#include "azure_c_shared_utility/platform.h"
#include "iothub_client.h"
#include "iothub_device_client.h"
#include "iothub_module_client.h"
#include "iothub_client_version.h"
#include "iothub_client_edge.h"
#ifndef MACOSX
#include "azure_prov_client/iothub_security_factory.h"
#endif

#include "iothub_message.h"
#if USE_HTTP
#include "iothubtransporthttp.h"
#endif
#if USE_AMQP
#include "iothubtransport.h"
#include "iothubtransportamqp.h"
#ifdef USE_WEBSOCKETS
#include "iothubtransportamqp_websockets.h"
#endif
#endif
#if USE_MQTT
#include "iothubtransportmqtt.h"
#ifdef USE_WEBSOCKETS
#include "iothubtransportmqtt_websockets.h"
#endif
#endif

#ifndef IMPORT_NAME
#define IMPORT_NAME iothub_client
#endif

#define VERSION_STRING "1.4.2"

#if PY_MAJOR_VERSION >= 3
#define IS_PY3
#endif

//#define SUPPORT___STR__

// helper for debugging py objects
#define PRINT_PYTHON_OBJECT_NAME(obj)\
{\
    std::string object_classname = boost::python::extract<std::string>(obj.attr("__class__").attr("__name__"));\
    printf("Object: %s\n", object_classname.c_str());\
}

class PlatformCallHandler
{
private:
    static int init_call_count;
public:
    static void Platform_Init()
    {
        if (init_call_count == 0)
        {
            platform_init();
        }
        init_call_count++;
    }

    static void Platform_DeInit()
    {
        if (init_call_count == 1)
        {
            platform_deinit();
        }
        init_call_count--;
    }
};

int PlatformCallHandler::init_call_count = 0;

//
// note: all new allocations throw a std::bad_alloc exception which trigger a MemoryError in Python
//

// helper classes for transitions between Python and C++ layer

class ScopedGILAcquire
{
public:
    inline ScopedGILAcquire()
    {
        gil_state = PyGILState_Ensure();
    }

    inline ~ScopedGILAcquire()
    {
        PyGILState_Release(gil_state);
    }
private:
    PyGILState_STATE gil_state;
};

class ScopedGILRelease
{
public:
    inline ScopedGILRelease()
    {
        thread_state = PyEval_SaveThread();
    }

    inline ~ScopedGILRelease()
    {
        PyEval_RestoreThread(thread_state);
        thread_state = NULL;
    }
private:
    PyThreadState * thread_state;
};

enum SECURITY_TYPE
{
    UNKNOWN,
    SAS,
    X509
};

//
// iothubtransportxxxx.h
//

#ifdef USE_WEBSOCKETS
    enum IOTHUB_TRANSPORT_PROVIDER
    {
#if USE_HTTP
        HTTP,
#endif
#if USE_AMQP
		AMQP,
#endif
#if USE_MQTT
		MQTT,
#endif
#if USE_AMQP
		AMQP_WS,
#endif
#if USE_MQTT
		MQTT_WS
#endif
    };
#else
    enum IOTHUB_TRANSPORT_PROVIDER
    {
#if USE_HTTP
        HTTP,
#endif
#if USE_AMQP
		AMQP,
#endif
#if USE_MQTT
		MQTT
#endif
    };
#endif

//
//  IotHubError exception handler base class
//

PyObject* iotHubErrorType = NULL;

class IoTHubError : public std::exception
{
public:
    IoTHubError(
        std::string _exc,
        std::string _cls,
        std::string _func
        )
    {
        exc = _exc;
        cls = _cls;
        // only display class names in camel case
        func = (_func[0] != 'I') ? CamelToPy(_func) : _func;
    }

    std::string exc;
    std::string cls;
    std::string func;

    std::string str() const
    {
        std::stringstream s;
        s << cls << "." << func << ", " << decode_error();
        return s.str();
    }

    std::string repr() const
    {
        std::stringstream s;
        s << exc << "(" << str() << ")";
        return s.str();
    }

    virtual std::string decode_error() const = 0;

private:

    std::string CamelToPy(std::string &_func)
    {
        std::string py;
        std::string::size_type len = _func.length();
        for (std::string::size_type i = 0; i < len; i++)
        {
            char ch = _func[i];
            if ((i > 0) && isupper(ch))
            {
                py.push_back('_');
            }
            py.push_back((char)tolower(ch));
        }
        return py;
    }

};

PyObject*
createExceptionClass(
    const char* name,
    PyObject* baseTypeObj = PyExc_Exception
    )
{
    namespace bp = boost::python;
    using std::string;
    string scopeName = bp::extract<string>(bp::scope().attr("__name__"));
    string qualifiedName0 = scopeName + "." + name;
    char* qualifiedName1 = const_cast<char*>(qualifiedName0.c_str());

    PyObject* typeObj = PyErr_NewException(qualifiedName1, baseTypeObj, 0);
    if (!typeObj) bp::throw_error_already_set();
    bp::scope().attr(name) = bp::handle<>(bp::borrowed(typeObj));

    return typeObj;
}

//
//  map.h
//

//
//  IoTHubMapError
//

PyObject *iotHubMapErrorType = NULL;

class IoTHubMapError : public IoTHubError
{
public:
    IoTHubMapError(
        std::string _func,
        MAP_RESULT _result
        ) :
        IoTHubError(
            "IoTHubMapError",
            "IoTHubMap",
            _func
            )
    {
        result = _result;
    }

    MAP_RESULT result;

    virtual std::string decode_error() const
    {
        std::stringstream s;
        s << "IoTHubMapResult.";
        switch (result)
        {
        case MAP_OK: s << "OK"; break;
        case MAP_ERROR: s << "ERROR"; break;
        case MAP_INVALIDARG: s << "INVALIDARG"; break;
        case MAP_KEYEXISTS: s << "KEYEXISTS"; break;
        case MAP_KEYNOTFOUND: s << "KEYNOTFOUND"; break;
        case MAP_FILTER_REJECT: s << "FILTER_REJECT"; break;
        }
        return s.str();
    }

};

void iotHubMapError(const IoTHubMapError& x)
{
    boost::python::object pythonExceptionInstance(x);
    PyErr_SetObject(iotHubMapErrorType, pythonExceptionInstance.ptr());
};

// callback function
boost::python::object mapFilterCallback;

extern "C"
int
MapFilterCallback(
    const char* mapProperty,
    const char* mapValue
    )
{
    boost::python::object returnObject;
    {
        ScopedGILAcquire acquire;
        try {
            returnObject = mapFilterCallback(mapProperty, mapValue);
        }
        catch (const boost::python::error_already_set)
        {
            // Catch and ignore exception that is thrown in Python callback.
            // There is nothing we can do about it here.
            PyErr_Print();
        }
    }
    return boost::python::extract<int>(returnObject);
}

class IoTHubMap
{

    bool filter;
    bool ownHandle;
    MAP_HANDLE mapHandle;

public:

    IoTHubMap(const IoTHubMap& map) :
        ownHandle(true),
        filter(false)
    {
        mapHandle = Map_Clone(map.mapHandle);
        if (mapHandle == NULL)
        {
            throw IoTHubMapError(__func__, MAP_ERROR);
        }
    }

    IoTHubMap() :
        ownHandle(true),
        filter(false)
    {
        mapHandle = Map_Create(NULL);
        if (mapHandle == NULL)
        {
            throw IoTHubMapError(__func__, MAP_ERROR);
        }
    }

    IoTHubMap(boost::python::object &_mapFilterCallback) :
        ownHandle(true),
        filter(false),
        mapHandle(NULL)
    {
        MAP_FILTER_CALLBACK mapFilterFunc = NULL;
        if (PyCallable_Check(_mapFilterCallback.ptr()))
        {
            if (PyCallable_Check(mapFilterCallback.ptr()))
            {
                PyErr_SetString(PyExc_TypeError, "Filter already in use");
                boost::python::throw_error_already_set();
                return;
            }
            else
            {
                mapFilterCallback = _mapFilterCallback;
                mapFilterFunc = &MapFilterCallback;
                filter = true;
            }
        }
        else
        {
            PyErr_SetString(PyExc_TypeError, "expected type callable");
            boost::python::throw_error_already_set();
            return;
        }
        mapHandle = Map_Create(mapFilterFunc);
        if (mapHandle == NULL)
        {
            throw IoTHubMapError(__func__, MAP_ERROR);
        }
    }

    IoTHubMap(MAP_HANDLE _mapHandle, bool _ownHandle = true) :
        ownHandle(_ownHandle),
        filter(false),
        mapHandle(_mapHandle)
    {
        if (mapHandle == NULL)
        {
            throw IoTHubMapError(__func__, MAP_ERROR);
        }
    }

    ~IoTHubMap()
    {
        Destroy();
        if (filter)
        {
            mapFilterCallback = boost::python::object();
        }
    }

    static IoTHubMap *Create(boost::python::object& _mapFilterCallback)
    {
        MAP_FILTER_CALLBACK mapFilterFunc = NULL;
        if (PyCallable_Check(_mapFilterCallback.ptr()))
        {
            mapFilterCallback = _mapFilterCallback;
            mapFilterFunc = &MapFilterCallback;
        }
        else if (Py_None != _mapFilterCallback.ptr())
        {
            PyErr_SetString(PyExc_TypeError, "Create expected type callable or None");
            boost::python::throw_error_already_set();
            return NULL;
        }
        return new IoTHubMap(Map_Create(mapFilterFunc));
    }

    void Destroy()
    {
        if (mapHandle != NULL)
        {
            if (ownHandle)
            {
                Map_Destroy(mapHandle);
            }
            mapHandle = NULL;
        }
    }

    IoTHubMap *Clone()
    {
        return new IoTHubMap(Map_Clone(mapHandle));
    }

    void Add(std::string key, std::string value)
    {
        MAP_RESULT result = Map_Add(mapHandle, key.c_str(), value.c_str());
        if (result != MAP_OK)
        {
            throw IoTHubMapError(__func__, result);
        }
    }

    void AddOrUpdate(std::string key, std::string value)
    {
        MAP_RESULT result = Map_AddOrUpdate(mapHandle, key.c_str(), value.c_str());
        if (result != MAP_OK)
        {
            throw IoTHubMapError(__func__, result);
        }
    }

    void Delete(std::string key)
    {
        MAP_RESULT result = Map_Delete(mapHandle, key.c_str());
        if (result != MAP_OK)
        {
            throw IoTHubMapError(__func__, result);
        }
    }

    bool ContainsKey(std::string key)
    {
        MAP_RESULT result;
        bool keyExists;
        result = Map_ContainsKey(mapHandle, key.c_str(), &keyExists);
        if (result != MAP_OK)
        {
            throw IoTHubMapError(__func__, result);
        }
        return keyExists;
    }

    bool ContainsValue(std::string value)
    {
        bool valueExists;
        MAP_RESULT result = Map_ContainsValue(mapHandle, value.c_str(), &valueExists);
        if (result != MAP_OK)
        {
            throw IoTHubMapError(__func__, result);
        }
        return valueExists;
    }

    const char *GetValueFromKey(std::string key)
    {
        const char *result = Map_GetValueFromKey(mapHandle, key.c_str());
        if (result == NULL)
        {
            throw IoTHubMapError(__func__, MAP_KEYNOTFOUND);
        }
        return result;
    }

    boost::python::dict GetInternals()
    {
        const char*const* keys;
        const char*const* values;
        boost::python::dict keyValuePair;
        size_t count;
        MAP_RESULT result = Map_GetInternals(mapHandle, &keys, &values, &count);
        if (result == MAP_OK)
        {
            for (unsigned int i = 0; i < count; i++)
            {
                keyValuePair[keys[i]] = values[i];
            }
        }
        else
        {
            throw IoTHubMapError(__func__, result);
        }
        return keyValuePair;
    }

#ifdef SUPPORT___STR__
    std::string str() const
    {
        std::stringstream s;
        // todo
        return s.str();
    }

    std::string repr() const
    {
        std::stringstream s;
        s << "IoTHubMap(" << str() << ")";
        return s.str();
    }
#endif
};

//
//  iothub_message.h
//

PyObject *iothubMessageErrorType = NULL;

class IoTHubMessageError : public IoTHubError
{
public:
    IoTHubMessageError(
        std::string _func,
        IOTHUB_MESSAGE_RESULT _result
        ) :
        IoTHubError(
            "IoTHubMessageError",
            "IoTHubMessage",
            _func
            )
    {
        result = _result;
    }

    IOTHUB_MESSAGE_RESULT result;

    std::string decode_error() const
    {
        std::stringstream s;
        s << "IoTHubMessageResult.";
        switch (result)
        {
        case IOTHUB_MESSAGE_OK: s << "OK"; break;
        case IOTHUB_MESSAGE_INVALID_ARG: s << "INVALID_ARG"; break;
        case IOTHUB_MESSAGE_INVALID_TYPE: s << "INVALID_TYPE"; break;
        case IOTHUB_MESSAGE_ERROR: s << "ERROR"; break;
        }
        return s.str();
    }

};

// class exposed to py used as parameter diagnostic data

class IoTHubMessageDiagnosticPropertyData
{
    std::string diagnosticId;
    std::string diagnosticCreationTimeUtc;
public:
    IoTHubMessageDiagnosticPropertyData(
        std::string _diagnosticId,
        std::string _diagnosticCreationTimeUtc
    ) :
        diagnosticId(_diagnosticId),
        diagnosticCreationTimeUtc(_diagnosticCreationTimeUtc)
    {
    }

    const char *GetDiagnosticId()
    {
        return diagnosticId.c_str();
    }

    const char *GetDiagnosticCreationTimeUtc()
    {
        return diagnosticCreationTimeUtc.c_str();
    }
};

void iothubMessageError(const IoTHubMessageError& x)
{
    boost::python::object pythonExceptionInstance(x);
    PyErr_SetObject(iothubMessageErrorType, pythonExceptionInstance.ptr());
};

class IoTHubMessage
{

    IOTHUB_MESSAGE_HANDLE iotHubMessageHandle;
    IoTHubMap *iotHubMapProperties;

public:

    IoTHubMessage(const IoTHubMessage& message) :
        iotHubMapProperties(NULL)
    {
        iotHubMessageHandle = IoTHubMessage_Clone(message.iotHubMessageHandle);
        if (iotHubMessageHandle == NULL)
        {
            throw IoTHubMessageError(__func__, IOTHUB_MESSAGE_ERROR);
        }
    }

    IoTHubMessage(IOTHUB_MESSAGE_HANDLE _iotHubMessageHandle) :
        iotHubMapProperties(NULL),
        iotHubMessageHandle(_iotHubMessageHandle)
    {
        if (_iotHubMessageHandle == NULL)
        {
            throw IoTHubMessageError(__func__, IOTHUB_MESSAGE_ERROR);
        }
    }

    IoTHubMessage(std::string source) :
        iotHubMapProperties(NULL)
    {
        iotHubMessageHandle = IoTHubMessage_CreateFromString(source.c_str());
        if (iotHubMessageHandle == NULL)
        {
            throw IoTHubMessageError(__func__, IOTHUB_MESSAGE_ERROR);
        }
    }

    IoTHubMessage(PyObject *pyObject) :
        iotHubMapProperties(NULL)
    {
        if (!PyByteArray_Check(pyObject)) {
            PyErr_SetString(PyExc_TypeError, "expected type bytearray");
            boost::python::throw_error_already_set();
            return;
        }
        PyByteArrayObject *pyByteArray = (PyByteArrayObject *)pyObject;
        const unsigned char* byteArray = (const unsigned char*)pyByteArray->ob_bytes;
        size_t size = Py_SIZE(pyByteArray);
        iotHubMessageHandle = IoTHubMessage_CreateFromByteArray(byteArray, size);
        if (iotHubMessageHandle == NULL)
        {
            throw IoTHubMessageError(__func__, IOTHUB_MESSAGE_ERROR);
        }
    }

    ~IoTHubMessage()
    {
        Destroy();
        if (iotHubMapProperties != NULL)
        {
            delete iotHubMapProperties;
        }
    }

    static IoTHubMessage *CreateFromByteArray(PyObject *pyObject)
    {
        if (!PyByteArray_Check(pyObject)) {
            PyErr_SetString(PyExc_TypeError, "CreateFromByteArray expected type bytearray");
            boost::python::throw_error_already_set();
            return NULL;
        }
        PyByteArrayObject *pyByteArray = (PyByteArrayObject *)pyObject;
        const unsigned char* byteArray = (const unsigned char*)pyByteArray->ob_bytes;
        size_t size = Py_SIZE(pyByteArray);
        return new IoTHubMessage(IoTHubMessage_CreateFromByteArray(byteArray, size));
    }

    static IoTHubMessage *CreateFromString(std::string source)
    {
        return new IoTHubMessage(IoTHubMessage_CreateFromString(source.c_str()));
    }

    IoTHubMessage *Clone()
    {
        return new IoTHubMessage(IoTHubMessage_Clone(iotHubMessageHandle));
    }

    PyObject* GetBytearray()
    {
        const unsigned char* buffer;
        size_t size;
        PyObject* pyObject = Py_None;
        IOTHUB_MESSAGE_RESULT result = IoTHubMessage_GetByteArray(iotHubMessageHandle, &buffer, &size);
        if (result == IOTHUB_MESSAGE_OK)
        {
            pyObject = PyByteArray_FromStringAndSize((char*)buffer, size);
        }
        else
        {
            throw IoTHubMessageError(__func__, result);
        }
        return pyObject;
    }

    const char *GetString()
    {
        return IoTHubMessage_GetString(iotHubMessageHandle);
    }

    IOTHUBMESSAGE_CONTENT_TYPE GetContentType()
    {
        return IoTHubMessage_GetContentType(iotHubMessageHandle);
    }

    const char *GetContentTypeSystemProperty()
    {
        return IoTHubMessage_GetContentTypeSystemProperty(iotHubMessageHandle);
    }

    IOTHUB_MESSAGE_RESULT SetContentTypeSystemProperty(std::string contentType)
    {
        return IoTHubMessage_SetContentTypeSystemProperty(iotHubMessageHandle, contentType.c_str());
    }

    const char *GetContentEncodingSystemProperty()
    {
        return IoTHubMessage_GetContentEncodingSystemProperty(iotHubMessageHandle);
    }

    IOTHUB_MESSAGE_RESULT SetContentEncodingSystemProperty(std::string contentEncoding)
    {
        return IoTHubMessage_SetContentEncodingSystemProperty(iotHubMessageHandle, contentEncoding.c_str());
    }

    IoTHubMessageDiagnosticPropertyData *GetDiagnosticPropertyData()
    {
        const IOTHUB_MESSAGE_DIAGNOSTIC_PROPERTY_DATA* data = IoTHubMessage_GetDiagnosticPropertyData(iotHubMessageHandle);
        if (data != NULL)
        {
            std::string diagnosticId(data->diagnosticId);
            std::string diagnosticCreationTimeUtc(data->diagnosticCreationTimeUtc);
            return new IoTHubMessageDiagnosticPropertyData(diagnosticId, diagnosticCreationTimeUtc);
        }
        return NULL;
    }

    IOTHUB_MESSAGE_RESULT SetDiagnosticPropertyData(IoTHubMessageDiagnosticPropertyData *ioTHubMessageDiagnosticPropertyData)
    {
        IOTHUB_MESSAGE_DIAGNOSTIC_PROPERTY_DATA data;
        data.diagnosticId = (char*)ioTHubMessageDiagnosticPropertyData->GetDiagnosticId();
        data.diagnosticCreationTimeUtc = (char*)ioTHubMessageDiagnosticPropertyData->GetDiagnosticCreationTimeUtc();

        return IoTHubMessage_SetDiagnosticPropertyData(iotHubMessageHandle, &data);
    }

    IoTHubMap *Properties()
    {
        if (iotHubMapProperties == NULL)
        {
            iotHubMapProperties = new IoTHubMap(IoTHubMessage_Properties(iotHubMessageHandle), false);
        }
        return iotHubMapProperties;
    }

    const char *GetMessageId()
    {
        return IoTHubMessage_GetMessageId(iotHubMessageHandle);
    }

    void SetMessageId(std::string messageId)
    {
        IOTHUB_MESSAGE_RESULT result = IoTHubMessage_SetMessageId(iotHubMessageHandle, messageId.c_str());
        if (result != IOTHUB_MESSAGE_OK)
        {
            throw IoTHubMessageError(__func__, result);
        }
    }

    const char *GetCorrelationId()
    {
        return IoTHubMessage_GetCorrelationId(iotHubMessageHandle);
    }

    void SetCorrelationId(std::string correlationId)
    {
        IOTHUB_MESSAGE_RESULT result = IoTHubMessage_SetCorrelationId(iotHubMessageHandle, correlationId.c_str());
        if (result != IOTHUB_MESSAGE_OK)
        {
            throw IoTHubMessageError(__func__, result);
        }
    }

    const char *GetInputName()
    {
        return IoTHubMessage_GetInputName(iotHubMessageHandle);
    }

    const char *GetOutputName()
    {
        return IoTHubMessage_GetOutputName(iotHubMessageHandle);
    }

    const char *GetConnectionModuleId()
    {
        return IoTHubMessage_GetConnectionModuleId(iotHubMessageHandle);
    }

    const char *GetConnectionDeviceId()
    {
        return IoTHubMessage_GetConnectionDeviceId(iotHubMessageHandle);
    }

    void Destroy()
    {
        if (iotHubMessageHandle != NULL)
        {
            IoTHubMessage_Destroy(iotHubMessageHandle);
            iotHubMessageHandle = NULL;
        }
    }

    IOTHUB_MESSAGE_HANDLE Handle()
    {
        return iotHubMessageHandle;
    }

#ifdef SUPPORT___STR__
    std::string str() const
    {
        std::stringstream s;
        return s.str();
    }

    std::string repr() const
    {
        std::stringstream s;
        s << "IoTHubMessage(" << str() << ")";
        return s.str();
    }
#endif
};

//
//  iothub_client.h
//

PyObject *iothubClientErrorType = NULL;

class IoTHubClientError : public IoTHubError
{
public:
    IoTHubClientError(
        std::string _func,
        IOTHUB_CLIENT_RESULT _result
        ) :
        IoTHubError(
            "IoTHubClientError",
            "IoTHubClient",
            _func
            )
    {
        result = _result;
    }

    IOTHUB_CLIENT_RESULT result;

    virtual std::string decode_error() const
    {
        std::stringstream s;
        s << "IoTHubClientResult.";
        switch (result)
        {
        case IOTHUB_CLIENT_OK: s << "OK"; break;
        case IOTHUB_CLIENT_INVALID_ARG: s << "INVALID_ARG"; break;
        case IOTHUB_CLIENT_ERROR: s << "ERROR"; break;
        case IOTHUB_CLIENT_INVALID_SIZE: s << "INVALID_SIZE"; break;
        case IOTHUB_CLIENT_INDEFINITE_TIME: s << "INDEFINITE_TIME"; break;
        }
        return s.str();
    }

};

void iothubClientError(const IoTHubClientError& x)
{
    boost::python::object pythonExceptionInstance(x);
    PyErr_SetObject(iothubClientErrorType, pythonExceptionInstance.ptr());
};


// class exposed to py used as parameter for Create

class IoTHubConfig
{
public:
    IoTHubConfig(
        IOTHUB_TRANSPORT_PROVIDER _protocol,
        std::string _deviceId,
        std::string _deviceKey,
        std::string _deviceSasToken,
        std::string _iotHubName,
        std::string _iotHubSuffix,
        std::string _protocolGatewayHostName
        ) :
        protocol(_protocol),
        deviceId(_deviceId),
        deviceKey(_deviceKey),
        deviceSasToken(_deviceSasToken),
        iotHubName(_iotHubName),
        iotHubSuffix(_iotHubSuffix),
        protocolGatewayHostName(_protocolGatewayHostName)
    {
    }

    IOTHUB_TRANSPORT_PROVIDER protocol;
    std::string deviceId;
    std::string deviceKey;
    std::string deviceSasToken;
    std::string iotHubName;
    std::string iotHubSuffix;
    std::string protocolGatewayHostName;
};

// callbacks

typedef struct
{
    boost::python::object messageCallback;
    boost::python::object userContext;
    IoTHubMessage *eventMessage;
} SendContext;

extern "C"
void
SendConfirmationCallback(
    IOTHUB_CLIENT_CONFIRMATION_RESULT result,
    void* sendContextCallback
    )
{
    SendContext *sendContext = (SendContext *)sendContextCallback;
    IoTHubMessage *eventMessage = sendContext->eventMessage;
    boost::python::object userContext = sendContext->userContext;
    boost::python::object messageCallback = sendContext->messageCallback;
    {
        ScopedGILAcquire acquire;
        try {
            messageCallback(eventMessage, result, userContext);
        }
        catch (const boost::python::error_already_set)
        {
            // Catch and ignore exception that is thrown in Python callback.
            // There is nothing we can do about it here.
            PyErr_Print();
        }
    }
    delete sendContext;
    delete eventMessage;
}

typedef struct
{
    boost::python::object messageCallback;
    boost::python::object userContext;
} ReceiveContext;

extern "C"
IOTHUBMESSAGE_DISPOSITION_RESULT
ReceiveMessageCallback(
    IOTHUB_MESSAGE_HANDLE messageHandle,
    void* receiveContextCallback
    )
{
    boost::python::object returnObject;
    ReceiveContext *receiveContext = (ReceiveContext *)receiveContextCallback;
    boost::python::object userContext = receiveContext->userContext;
    boost::python::object messageCallback = receiveContext->messageCallback;
    IoTHubMessage *message = new IoTHubMessage(IoTHubMessage_Clone(messageHandle));
    {
        ScopedGILAcquire acquire;
        try {
            returnObject = messageCallback(message, userContext);
        }
        catch (const boost::python::error_already_set)
        {
            // Catch and ignore exception that is thrown in Python callback.
            // There is nothing we can do about it here.
            PyErr_Print();
        }
    }
    delete message;
    return boost::python::extract<IOTHUBMESSAGE_DISPOSITION_RESULT>(returnObject);
}

typedef struct
{
    boost::python::object connectionStatusCallback;
    boost::python::object userContext;
} ConnectionStatusContext;

extern "C"
void
ConnectionStatusCallback(
    IOTHUB_CLIENT_CONNECTION_STATUS result,
    IOTHUB_CLIENT_CONNECTION_STATUS_REASON reason,
    void* userContextCallback
)
{
    ConnectionStatusContext *connectionStatusContext = (ConnectionStatusContext *)userContextCallback;
    boost::python::object userContext = connectionStatusContext->userContext;
    boost::python::object connectionStatusCallback = connectionStatusContext->connectionStatusCallback;

    ScopedGILAcquire acquire;
    try
    {
        connectionStatusCallback(result, reason, userContext);
    }
    catch (const boost::python::error_already_set)
    {
        // Catch and ignore exception that is thrown in Python callback.
        // There is nothing we can do about it here.
        PyErr_Print();
    }
}

typedef struct
{
    boost::python::object deviceTwinCallback;
    boost::python::object userContext;
} DeviceTwinContext;

extern "C"
void
DeviceTwinCallback(
    DEVICE_TWIN_UPDATE_STATE updateState,
    const unsigned char* payLoad,
    size_t size,
    void* userContextCallback
    )
{
    DeviceTwinContext *deviceTwinContext = (DeviceTwinContext *)userContextCallback;
    boost::python::object userContext = deviceTwinContext->userContext;
    boost::python::object deviceTwinCallback = deviceTwinContext->deviceTwinCallback;

    std::string payload_std_string(reinterpret_cast<const char *>(payLoad), size);

    ScopedGILAcquire acquire;
    try
    {
        deviceTwinCallback(updateState, payload_std_string, userContext);
    }
    catch (const boost::python::error_already_set)
    {
        // Catch and ignore exception that is thrown in Python callback.
        // There is nothing we can do about it here.
        PyErr_Print();
    }
}

typedef struct
{
    boost::python::object sendReportedStateCallback;
    boost::python::object userContext;
} SendReportedStateContext;

extern "C"
void
SendReportedStateCallback(
    int status_code,
    void* userContextCallback
    )
{
    (void)userContextCallback;

    SendReportedStateContext *sendReportedStateContext = (SendReportedStateContext *)userContextCallback;
    boost::python::object userContext = sendReportedStateContext->userContext;
    boost::python::object sendReportedStateCallback = sendReportedStateContext->sendReportedStateCallback;

    ScopedGILAcquire acquire;
    try
    {
        sendReportedStateCallback(status_code, userContext);
    }
    catch (const boost::python::error_already_set)
    {
        // Catch and ignore exception that is thrown in Python callback.
        // There is nothing we can do about it here.
        PyErr_Print();
    }
}

typedef struct
{
    boost::python::object deviceMethodCallback;
    boost::python::object userContext;
} DeviceMethodContext;

class DeviceMethodReturnValue
{
public:
    std::string response;
    int status;
};

extern "C"
int
DeviceMethodCallback(
    const char* method_name,
    const unsigned char* payLoad,
    size_t size,
    unsigned char** response,
    size_t* resp_size,
    void* userContextCallback
    )
{
    int retVal = -1;

    DeviceMethodContext *deviceMethodContext = (DeviceMethodContext *)userContextCallback;
    boost::python::object userContext = deviceMethodContext->userContext;
    boost::python::object deviceMethodCallback = deviceMethodContext->deviceMethodCallback;

    std::string method_name_std_string(method_name);
    std::string payload_std_string(reinterpret_cast<const char *>(payLoad), size);

    ScopedGILAcquire acquire;
    try
    {
        boost::python::object user_response_obj = deviceMethodCallback(method_name_std_string, payload_std_string, userContext);

        DeviceMethodReturnValue user_response_value = boost::python::extract<DeviceMethodReturnValue>(user_response_obj)();

        retVal = user_response_value.status;

        *resp_size = strlen(user_response_value.response.c_str());
        if ((*response = (unsigned char*)malloc(*resp_size)) == NULL)
        {
            *resp_size = 0;
        }
        else
        {
            memcpy(*response, user_response_value.response.c_str(), *resp_size);
        }
    }
    catch (const boost::python::error_already_set)
    {
        // Catch and ignore exception that is thrown in Python callback.
        // There is nothing we can do about it here.
        PyErr_Print();
    }

    return retVal;
}

extern "C"
int
InboundDeviceMethodCallback(
    const char* method_name,
    const unsigned char* payLoad,
    size_t size,
    METHOD_HANDLE method_id,
    void* userContextCallback
)
{
    int retVal = -1;

    DeviceMethodContext *deviceMethodContext = (DeviceMethodContext *)userContextCallback;
    boost::python::object userContext = deviceMethodContext->userContext;
    boost::python::object deviceMethodCallback = deviceMethodContext->deviceMethodCallback;

    std::string method_name_std_string(method_name);
    std::string payload_std_string(reinterpret_cast<const char *>(payLoad), size);

    ScopedGILAcquire acquire;
    try
    {
        boost::python::object user_response_obj = deviceMethodCallback(method_name_std_string, payload_std_string, method_id, userContext);

        DeviceMethodReturnValue user_response_value = boost::python::extract<DeviceMethodReturnValue>(user_response_obj)();

        retVal = user_response_value.status;
    }
    catch (const boost::python::error_already_set)
    {
        // Catch and ignore exception that is thrown in Python callback.
        // There is nothing we can do about it here.
        PyErr_Print();
    }

    return retVal;
}

#ifndef DONT_USE_UPLOADTOBLOB
typedef struct
{
    boost::python::object blobUploadCallback;
    boost::python::object userContext;
} BlobUploadContext;

extern "C"
void
BlobUploadConfirmationCallback(
    IOTHUB_CLIENT_FILE_UPLOAD_RESULT result,
    void* userContextCallback
    )
{
    BlobUploadContext *blobUploadContext = (BlobUploadContext *)userContextCallback;
    boost::python::object blobUploadCallback = blobUploadContext->blobUploadCallback;
    boost::python::object userContext = blobUploadContext->userContext;
    {
        ScopedGILAcquire acquire;
        try {
            blobUploadCallback(result, userContext);
        }
        catch (const boost::python::error_already_set)
        {
            // Catch and ignore exception that is thrown in Python callback.
            // There is nothing we can do about it here.
            PyErr_Print();
        }
    }
    delete blobUploadContext;
}
#endif

typedef struct
{
    IOTHUB_CLIENT_RETRY_POLICY retryPolicy;
    size_t retryTimeoutLimitInSeconds;
} GetRetryPolicyReturnValue;

class IoTHubTransport
{
    static IOTHUB_CLIENT_TRANSPORT_PROVIDER
        GetProtocol(IOTHUB_TRANSPORT_PROVIDER _protocol)
    {
        IOTHUB_CLIENT_TRANSPORT_PROVIDER protocol = NULL;
        switch (_protocol)
        {
#ifdef USE_HTTP
        case HTTP:
            protocol = HTTP_Protocol;
            break;
#endif
#ifdef USE_AMQP
        case AMQP:
            protocol = AMQP_Protocol;
            break;
#endif
#ifdef USE_MQTT
        case MQTT:
            protocol = MQTT_Protocol;
            break;
#endif
#ifdef USE_WEBSOCKETS
#ifdef USE_AMQP
        case AMQP_WS:
            protocol = AMQP_Protocol_over_WebSocketsTls;
            break;
#endif
#ifdef USE_MQTT
        case MQTT_WS:
            protocol = MQTT_WebSocket_Protocol;
            break;
#endif
#endif
        default:
            PyErr_SetString(PyExc_TypeError, "IoTHubTransportProvider set to unknown protocol");
            boost::python::throw_error_already_set();
            break;
        }
        return protocol;
    }

public:

    void* iotHubTransportHandle;
    IOTHUB_TRANSPORT_PROVIDER iotHubTransportProvider;

    IoTHubTransport(const IoTHubTransport& transport)
    {
        (void)transport;
        throw IoTHubClientError(__func__, IOTHUB_CLIENT_ERROR);
    }

    IoTHubTransport(
        IOTHUB_TRANSPORT_PROVIDER _iotHubTransportProvider,
        std::string iotHubNameString,
        std::string iotHUbSuffixString
    ) : iotHubTransportProvider(_iotHubTransportProvider)
    {
        {
            ScopedGILRelease release;
            PlatformCallHandler::Platform_Init();

            iotHubTransportHandle = (void*)IoTHubTransport_Create(GetProtocol(_iotHubTransportProvider), iotHubNameString.c_str(), iotHUbSuffixString.c_str());
        }
        if (iotHubTransportHandle == NULL)
        {
            throw IoTHubClientError(__func__, IOTHUB_CLIENT_ERROR);
        }
    }

    void Destroy()
    {
        if (iotHubTransportHandle != NULL)
        {
            {
                ScopedGILRelease release;
                IoTHubTransport_Destroy((TRANSPORT_HANDLE)iotHubTransportHandle);
            }
            iotHubTransportHandle = NULL;
        }
    }
};

class IoTHubMethodResponse
{
public:
    IoTHubMethodResponse()
    {
        ;
    }

    IoTHubMethodResponse(IOTHUB_CLIENT_RESULT _result, int _responseStatus, unsigned char* _responsePayload, size_t _responsePayloadSize)
    {
        result = _result;
        responseStatus = _responseStatus;
        std::string payload(&_responsePayload[0], &_responsePayload[0] + _responsePayloadSize);
        responsePayload = payload;
    }

    int result;
    int responseStatus;
    std::string responsePayload;
};


typedef enum CLIENT_INTERFACE_TYPE_TAG
{
    CLIENT_INTERFACE_DEVICE,
    CLIENT_INTERFACE_MODULE
} CLIENT_INTERFACE_TYPE;

template <class CLIENT_HANDLE_TYPE>
class IoTHubClient
{
protected:
    CLIENT_INTERFACE_TYPE client_interface_type;

    static IOTHUB_CLIENT_TRANSPORT_PROVIDER
        GetProtocol(IOTHUB_TRANSPORT_PROVIDER _protocol)
    {
        IOTHUB_CLIENT_TRANSPORT_PROVIDER protocol = NULL;
        switch (_protocol)
        {
#ifdef USE_HTTP
        case HTTP:
            protocol = HTTP_Protocol;
            break;
#endif
#ifdef USE_AMQP
        case AMQP:
            protocol = AMQP_Protocol;
            break;
#endif
#ifdef USE_MQTT
        case MQTT:
            protocol = MQTT_Protocol;
            break;
#endif
#ifdef USE_WEBSOCKETS
#ifdef USE_AMQP
        case AMQP_WS:
            protocol = AMQP_Protocol_over_WebSocketsTls;
            break;
#endif
#ifdef USE_MQTT
        case MQTT_WS:
            protocol = MQTT_WebSocket_Protocol;
            break;
#endif
#endif
        default:
            PyErr_SetString(PyExc_TypeError, "IoTHubTransportProvider set to unknown protocol");
            boost::python::throw_error_already_set();
            break;
        }
        return protocol;
    }

    CLIENT_HANDLE_TYPE iotHubClientHandle;

public:

    IOTHUB_TRANSPORT_PROVIDER protocol;

    IoTHubClient()
    {
        iotHubClientHandle = NULL;
    }

    IoTHubClient(const IoTHubClient& client)
    {
        (void)client;
        iotHubClientHandle = NULL;
        throw IoTHubClientError(__func__, IOTHUB_CLIENT_ERROR);
    }

    IoTHubClient(
        CLIENT_INTERFACE_TYPE _client_interface_type)
    {
        iotHubClientHandle = NULL;
        client_interface_type = _client_interface_type;
    }

    IoTHubClient(
        const IoTHubClient& client,
        CLIENT_INTERFACE_TYPE _client_interface_type)
    {
        (void)client;
        client_interface_type = _client_interface_type;
        iotHubClientHandle = NULL;
        throw IoTHubClientError(__func__, IOTHUB_CLIENT_ERROR);
    }

    IoTHubClient(
        CLIENT_HANDLE_TYPE _iotHubClientHandle,
        IOTHUB_TRANSPORT_PROVIDER _protocol,
        CLIENT_INTERFACE_TYPE _client_interface_type
    ) :
        iotHubClientHandle(_iotHubClientHandle),
        protocol(_protocol)
    {
        iotHubClientHandle = NULL;
        client_interface_type = _client_interface_type;
        if (_iotHubClientHandle == NULL)
        {
            throw IoTHubClientError(__func__, IOTHUB_CLIENT_ERROR);
        }
    }

    IoTHubClient(
        std::string connectionString,
        IOTHUB_TRANSPORT_PROVIDER _protocol,
        CLIENT_INTERFACE_TYPE _client_interface_type
    ) :
        protocol(_protocol)
    {
        iotHubClientHandle = NULL;

        {
            client_interface_type = _client_interface_type;

            ScopedGILRelease release;
            PlatformCallHandler::Platform_Init();

            iotHubClientHandle = (client_interface_type == CLIENT_INTERFACE_DEVICE) ?
                                    IoTHubDeviceClient_CreateFromConnectionString(connectionString.c_str(), GetProtocol(_protocol)) :
                                    IoTHubModuleClient_CreateFromConnectionString(connectionString.c_str(), GetProtocol(_protocol));
        }
        if (iotHubClientHandle == NULL)
        {
            throw IoTHubClientError(__func__, IOTHUB_CLIENT_ERROR);
        }
    }

    IoTHubClient(
        const IoTHubConfig &_config,
        CLIENT_INTERFACE_TYPE _client_interface_type
    )
    {
        client_interface_type = _client_interface_type;
        iotHubClientHandle = NULL;

        IOTHUB_CLIENT_CONFIG config;
        config.protocol = GetProtocol(_config.protocol);
        config.deviceId = _config.deviceId.c_str();
        config.deviceKey = _config.deviceKey.c_str();
        config.deviceSasToken = _config.deviceSasToken.c_str();
        config.iotHubName = _config.iotHubName.c_str();
        config.iotHubSuffix = _config.iotHubSuffix.c_str();
        config.protocolGatewayHostName = _config.protocolGatewayHostName.c_str();
        protocol = _config.protocol;
        {
            ScopedGILRelease release;
            PlatformCallHandler::Platform_Init();

            iotHubClientHandle = IoTHubDeviceClient_Create(&config);
        }
        if (iotHubClientHandle == NULL)
        {
            throw IoTHubClientError(__func__, IOTHUB_CLIENT_ERROR);
        }
    }

    IoTHubClient(
        IoTHubTransport* _iotHubTransport,
        IoTHubConfig* _iotHubConfig,
        CLIENT_INTERFACE_TYPE _client_interface_type
    )
    {
        client_interface_type = _client_interface_type;
        iotHubClientHandle = NULL;

        IOTHUB_CLIENT_CONFIG config;
        config.protocol = GetProtocol(_iotHubConfig->protocol);

        config.deviceId = _iotHubConfig->deviceId.c_str();
        if (_iotHubConfig->deviceId == "")
        {
            config.deviceId = NULL;
        }
        else
        {
            config.deviceId = _iotHubConfig->deviceId.c_str();
        }

        if (_iotHubConfig->deviceKey == "")
        {
            config.deviceKey = NULL;
        }
        else
        {
            config.deviceKey = _iotHubConfig->deviceKey.c_str();
        }

        if (_iotHubConfig->deviceSasToken == "")
        {
            config.deviceSasToken = NULL;
        }
        else
        {
            config.deviceSasToken = _iotHubConfig->deviceSasToken.c_str();
        }

        if (_iotHubConfig->iotHubName == "")
        {
            config.iotHubName = NULL;
        }
        else
        {
            config.iotHubName = _iotHubConfig->iotHubName.c_str();
        }

        if (_iotHubConfig->iotHubSuffix == "")
        {
            config.iotHubSuffix = NULL;
        }
        else
        {
            config.iotHubSuffix = _iotHubConfig->iotHubSuffix.c_str();
        }

        if (_iotHubConfig->protocolGatewayHostName == "")
        {
            config.protocolGatewayHostName = NULL;
        }
        else
        {
            config.protocolGatewayHostName = _iotHubConfig->protocolGatewayHostName.c_str();
        }

        protocol = _iotHubConfig->protocol;
        {
            ScopedGILRelease release;
            PlatformCallHandler::Platform_Init();

            iotHubClientHandle = IoTHubDeviceClient_CreateWithTransport((TRANSPORT_HANDLE)_iotHubTransport->iotHubTransportHandle, &config);
        }
        if (iotHubClientHandle == NULL)
        {
            throw IoTHubClientError(__func__, IOTHUB_CLIENT_ERROR);
        }
    }

#ifndef MACOSX
    static IOTHUB_SECURITY_TYPE
        GetSecurityType(SECURITY_TYPE _security_type)
    {
        IOTHUB_SECURITY_TYPE security_type = IOTHUB_SECURITY_TYPE_UNKNOWN;
        switch (_security_type)
        {
        case UNKNOWN:
            security_type = IOTHUB_SECURITY_TYPE_UNKNOWN;
            break;
        case SAS:
            security_type = IOTHUB_SECURITY_TYPE_SAS;
            break;
        case X509:
            security_type = IOTHUB_SECURITY_TYPE_X509;
            break;
        default:
            PyErr_SetString(PyExc_TypeError, "Provisioning Security Type set to unknown type");
            boost::python::throw_error_already_set();
            break;
        }
        return security_type;
    }
#endif

#ifndef MACOSX
    IoTHubClient(
        std::string iothub_uri,
        std::string device_id,
        SECURITY_TYPE security_type,
        IOTHUB_TRANSPORT_PROVIDER _protocol,
        CLIENT_INTERFACE_TYPE _client_interface_type
    ) :
        protocol(_protocol)
    {
        ScopedGILRelease release;
        PlatformCallHandler::Platform_Init();

        client_interface_type = _client_interface_type;
        iotHubClientHandle = NULL;

        if (iothub_security_init(GetSecurityType(security_type)) == 0)
        {
            iotHubClientHandle = IoTHubDeviceClient_CreateFromDeviceAuth(iothub_uri.c_str(), device_id.c_str(), GetProtocol(_protocol));
            if (iotHubClientHandle == NULL)
            {
                throw IoTHubClientError(__func__, IOTHUB_CLIENT_ERROR);
            }
        }
        else
        {
            throw IoTHubClientError(__func__, IOTHUB_CLIENT_ERROR);
        }
    }
#endif

    ~IoTHubClient()
    {
        if (iotHubClientHandle != NULL)
        {
            {
                ScopedGILRelease release;
                if (client_interface_type == CLIENT_INTERFACE_DEVICE)
                {
                    IoTHubDeviceClient_Destroy(iotHubClientHandle);
                }
                else
                {
                    IoTHubModuleClient_Destroy(iotHubClientHandle);
                }
            }
            iotHubClientHandle = NULL;
        }

#ifndef MACOSX
        iothub_security_deinit();
#endif

        PlatformCallHandler::Platform_DeInit();
    }

    void SendEventAsync(
        IoTHubMessage &eventMessage,
        boost::python::object& messageCallback,
        boost::python::object& userContext
        )
    {
        if (!PyCallable_Check(messageCallback.ptr()))
        {
            PyErr_SetString(PyExc_TypeError, "send_event_async expected type callable");
            boost::python::throw_error_already_set();
            return;
        }
        IOTHUB_CLIENT_RESULT result;
        SendContext *sendContext = new SendContext();
        sendContext->messageCallback = messageCallback;
        sendContext->userContext = userContext;
        sendContext->eventMessage = eventMessage.Clone();
        {
            ScopedGILRelease release;
            result = (client_interface_type == CLIENT_INTERFACE_DEVICE) ?
                        IoTHubDeviceClient_SendEventAsync(iotHubClientHandle, eventMessage.Handle(), SendConfirmationCallback, sendContext) :
                        IoTHubModuleClient_SendEventAsync(iotHubClientHandle, eventMessage.Handle(), SendConfirmationCallback, sendContext);
        }
        if (result != IOTHUB_CLIENT_OK)
        {
            throw IoTHubClientError(__func__, result);
        }
    }

    IOTHUB_CLIENT_STATUS GetSendStatus()
    {
        IOTHUB_CLIENT_STATUS iotHubClientStatus;
        IOTHUB_CLIENT_RESULT result = IOTHUB_CLIENT_OK;
        {
            ScopedGILRelease release;
            result = (client_interface_type == CLIENT_INTERFACE_DEVICE) ?
                        IoTHubDeviceClient_GetSendStatus(iotHubClientHandle, &iotHubClientStatus) :
                        IoTHubModuleClient_GetSendStatus(iotHubClientHandle, &iotHubClientStatus);
        }
        if (result != IOTHUB_CLIENT_OK)
        {
            throw IoTHubClientError(__func__, result);
        }
        return iotHubClientStatus;
    }

    void SetMessageCallback(
        boost::python::object& messageCallback,
        boost::python::object& userContext
        )
    {
        if (!PyCallable_Check(messageCallback.ptr()))
        {
            PyErr_SetString(PyExc_TypeError, "set_message_callback expected type callable");
            boost::python::throw_error_already_set();
            return;
        }
        ReceiveContext *receiveContext = new ReceiveContext();
        receiveContext->messageCallback = messageCallback;
        receiveContext->userContext = userContext;
        IOTHUB_CLIENT_RESULT result;
        {
            ScopedGILRelease release;
            result = (client_interface_type == CLIENT_INTERFACE_DEVICE) ?
                        IoTHubDeviceClient_SetMessageCallback(iotHubClientHandle, ReceiveMessageCallback, receiveContext) :
                        IoTHubModuleClient_SetMessageCallback(iotHubClientHandle, ReceiveMessageCallback, receiveContext);
        }
        if (result != IOTHUB_CLIENT_OK)
        {
            throw IoTHubClientError(__func__, result);
        }
    }

    void SetConnectionStatusCallback(
        boost::python::object& connectionStatusCallback,
        boost::python::object& userContext
    )
    {
        if (!PyCallable_Check(connectionStatusCallback.ptr()))
        {
            PyErr_SetString(PyExc_TypeError, "set_connection_status_callback expected type callable");
            boost::python::throw_error_already_set();
            return;
        }
        ReceiveContext *receiveContext = new ReceiveContext();
        receiveContext->messageCallback = connectionStatusCallback;
        receiveContext->userContext = userContext;
        IOTHUB_CLIENT_RESULT result;
        {
            ScopedGILRelease release;
            result = (client_interface_type == CLIENT_INTERFACE_DEVICE) ?
                        IoTHubDeviceClient_SetConnectionStatusCallback(iotHubClientHandle, ConnectionStatusCallback, receiveContext) :
                        IoTHubModuleClient_SetConnectionStatusCallback(iotHubClientHandle, ConnectionStatusCallback, receiveContext);
        }
        if (result != IOTHUB_CLIENT_OK)
        {
            throw IoTHubClientError(__func__, result);
        }
    }

    void SetRetryPolicy(
        IOTHUB_CLIENT_RETRY_POLICY retryPolicy,
        size_t retryTimeoutLimitInSeconds
    )
    {
        IOTHUB_CLIENT_RESULT result;
        {
            ScopedGILRelease release;
            result = (client_interface_type == CLIENT_INTERFACE_DEVICE) ?
                        IoTHubDeviceClient_SetRetryPolicy(iotHubClientHandle, retryPolicy, retryTimeoutLimitInSeconds) :
                        IoTHubModuleClient_SetRetryPolicy(iotHubClientHandle, retryPolicy, retryTimeoutLimitInSeconds);
        }
        if (result != IOTHUB_CLIENT_OK)
        {
            throw IoTHubClientError(__func__, result);
        }
    }

    GetRetryPolicyReturnValue GetRetryPolicy()
    {
        IOTHUB_CLIENT_RETRY_POLICY iotHubClientRetryPolicy;
        size_t retryTimeoutLimitInSeconds;
        IOTHUB_CLIENT_RESULT result = IOTHUB_CLIENT_OK;
        {
            ScopedGILRelease release;
            result = (client_interface_type == CLIENT_INTERFACE_DEVICE) ?
                        IoTHubDeviceClient_GetRetryPolicy(iotHubClientHandle, &iotHubClientRetryPolicy, &retryTimeoutLimitInSeconds) :
                        IoTHubModuleClient_GetRetryPolicy(iotHubClientHandle, &iotHubClientRetryPolicy, &retryTimeoutLimitInSeconds);
        }
        if (result != IOTHUB_CLIENT_OK)
        {
            throw IoTHubClientError(__func__, result);
        }

        GetRetryPolicyReturnValue returnValue;
        returnValue.retryPolicy = iotHubClientRetryPolicy;
        returnValue.retryTimeoutLimitInSeconds = retryTimeoutLimitInSeconds;

        return returnValue;
    }

    void SetTwinCallback(
        boost::python::object& deviceTwinCallback,
        boost::python::object& userContext
        )
    {
        if (!PyCallable_Check(deviceTwinCallback.ptr()))
        {
            PyErr_SetString(PyExc_TypeError, "set_device_twin_callback expected type callable");
            boost::python::throw_error_already_set();
            return;
        }
        DeviceTwinContext *deviceTwinContext = new DeviceTwinContext();
        deviceTwinContext->deviceTwinCallback = deviceTwinCallback;
        deviceTwinContext->userContext = userContext;
        IOTHUB_CLIENT_RESULT result;
        {
            ScopedGILRelease release;
            result = (client_interface_type == CLIENT_INTERFACE_DEVICE) ?
                        IoTHubDeviceClient_SetDeviceTwinCallback(iotHubClientHandle, DeviceTwinCallback, deviceTwinContext) :
                        IoTHubModuleClient_SetModuleTwinCallback(iotHubClientHandle, DeviceTwinCallback, deviceTwinContext);
        }
        if (result != IOTHUB_CLIENT_OK)
        {
            throw IoTHubClientError(__func__, result);
        }
    }

    void SendReportedState(
        std::string reportedState,
        size_t size,
        boost::python::object& reportedStateCallback,
        boost::python::object& userContext
        )
    {
        if (!PyCallable_Check(reportedStateCallback.ptr()))
        {
            PyErr_SetString(PyExc_TypeError, "send_reported_state expected type callable");
            boost::python::throw_error_already_set();
            return;
        }
        SendReportedStateContext *sendReportedStateContext = new SendReportedStateContext();
        sendReportedStateContext->sendReportedStateCallback = reportedStateCallback;
        sendReportedStateContext->userContext = userContext;

        IOTHUB_CLIENT_RESULT result;
        {
            ScopedGILRelease release;
            result = (client_interface_type == CLIENT_INTERFACE_DEVICE) ?
                        IoTHubDeviceClient_SendReportedState(iotHubClientHandle, (const unsigned char*)reportedState.c_str(), size, SendReportedStateCallback, sendReportedStateContext) :
                        IoTHubModuleClient_SendReportedState(iotHubClientHandle, (const unsigned char*)reportedState.c_str(), size, SendReportedStateCallback, sendReportedStateContext);
        }
        if (result != IOTHUB_CLIENT_OK)
        {
            throw IoTHubClientError(__func__, result);
        }
    }

    void SetMethodCallback(
        boost::python::object& deviceMethodCallback,
        boost::python::object& userContext
        )
    {
        if (!PyCallable_Check(deviceMethodCallback.ptr()))
        {
            PyErr_SetString(PyExc_TypeError, "set_device_method_callback expected type callable");
            boost::python::throw_error_already_set();
            return;
        }
        DeviceMethodContext *deviceMethodContext = new DeviceMethodContext();
        deviceMethodContext->deviceMethodCallback = deviceMethodCallback;
        deviceMethodContext->userContext = userContext;

        IOTHUB_CLIENT_RESULT result;
        {
            ScopedGILRelease release;
            result = IoTHubClient_SetDeviceMethodCallback((IOTHUB_CLIENT_HANDLE)iotHubClientHandle, DeviceMethodCallback, deviceMethodContext);
        }
        if (result != IOTHUB_CLIENT_OK)
        {
            throw IoTHubClientError(__func__, result);
        }
    }

    void SetDeviceMethodCallbackEx(
        boost::python::object& inboundDeviceMethodCallback,
        boost::python::object& userContext
    )
    {
        if (!PyCallable_Check(inboundDeviceMethodCallback.ptr()))
        {
            PyErr_SetString(PyExc_TypeError, "set_device_method_callback expected type callable");
            boost::python::throw_error_already_set();
            return;
        }
        DeviceMethodContext *deviceMethodContext = new DeviceMethodContext();
        deviceMethodContext->deviceMethodCallback = inboundDeviceMethodCallback;
        deviceMethodContext->userContext = userContext;
        IOTHUB_CLIENT_RESULT result;
        {
            ScopedGILRelease release;
            result = IoTHubClient_SetDeviceMethodCallback_Ex((IOTHUB_CLIENT_HANDLE)iotHubClientHandle, InboundDeviceMethodCallback, deviceMethodContext);
        }
        if (result != IOTHUB_CLIENT_OK)
        {
            throw IoTHubClientError(__func__, result);
        }
    }

    void DeviceMethodResponse(
        METHOD_HANDLE method_id,
        std::string response,
        size_t size,
        int statusCode
    )
    {
        IOTHUB_CLIENT_RESULT result;
        {
            ScopedGILRelease release;
            result = IoTHubDeviceClient_DeviceMethodResponse(iotHubClientHandle, method_id, (const unsigned char*)response.c_str(), size, statusCode);
        }
        if (result != IOTHUB_CLIENT_OK)
        {
            throw IoTHubClientError(__func__, result);
        }
    }

    time_t GetLastMessageReceiveTime()
    {
        time_t lastMessageReceiveTime;
        IOTHUB_CLIENT_RESULT result;
        {
            ScopedGILRelease release;
            result = (client_interface_type == CLIENT_INTERFACE_DEVICE) ?
                        IoTHubDeviceClient_GetLastMessageReceiveTime(iotHubClientHandle, &lastMessageReceiveTime) :
                        IoTHubModuleClient_GetLastMessageReceiveTime(iotHubClientHandle, &lastMessageReceiveTime);
        }
        if (result != IOTHUB_CLIENT_OK)
        {
            throw IoTHubClientError(__func__, result);
        }
        return lastMessageReceiveTime;
    }

    void SetOption(
        std::string optionName,
        boost::python::object& option
        )
    {
        IOTHUB_CLIENT_RESULT result = IOTHUB_CLIENT_OK;
#ifdef IS_PY3
        if (PyLong_Check(option.ptr()))
        {
            // Cast to 64 bit value, as SetOption expects 64 bit for some integer options
            uint64_t value = (uint64_t)boost::python::extract<long>(option);
            {
                ScopedGILRelease release;
                result = (client_interface_type == CLIENT_INTERFACE_DEVICE) ?
                            IoTHubDeviceClient_SetOption(iotHubClientHandle, optionName.c_str(), &value) :
                            IoTHubModuleClient_SetOption(iotHubClientHandle, optionName.c_str(), &value);
            }
        }
        else
        {
            std::string stringValue = boost::python::extract<std::string>(option);
            {
                ScopedGILRelease release;
                result = (client_interface_type == CLIENT_INTERFACE_DEVICE) ?
                            IoTHubDeviceClient_SetOption(iotHubClientHandle, optionName.c_str(), stringValue.c_str()) :
                            IoTHubModuleClient_SetOption(iotHubClientHandle, optionName.c_str(), stringValue.c_str());
            }
        }
#else
        if (PyString_Check(option.ptr()))
        {
            std::string stringValue = boost::python::extract<std::string>(option);
            {
                ScopedGILRelease release;
                result = (client_interface_type == CLIENT_INTERFACE_DEVICE) ?
                            IoTHubDeviceClient_SetOption(iotHubClientHandle, optionName.c_str(), stringValue.c_str()) :
                            IoTHubModuleClient_SetOption(iotHubClientHandle, optionName.c_str(), stringValue.c_str());
            }
        }
        else if (PyInt_Check(option.ptr()))
        {
            // Cast to 64 bit value, as SetOption expects 64 bit for some integer options
            uint64_t value = (uint64_t)boost::python::extract<int>(option);
            {
                ScopedGILRelease release;
                result = (client_interface_type == CLIENT_INTERFACE_DEVICE) ?
                            IoTHubDeviceClient_SetOption(iotHubClientHandle, optionName.c_str(), &value) :
                            IoTHubModuleClient_SetOption(iotHubClientHandle, optionName.c_str(), &value);
            }
        }
        else
        {
            PyErr_SetString(PyExc_TypeError, "set_option expected type int or string");
            boost::python::throw_error_already_set();
        }
#endif
        if (result != IOTHUB_CLIENT_OK)
        {
            printf("IoTHub Client SetOption failed with result: %d", result);
        }
    }

#ifndef DONT_USE_UPLOADTOBLOB
    void UploadToBlobAsync(
        std::string destinationFileName,
        std::string source,
        size_t size,
        boost::python::object& iotHubClientFileUploadCallback,
        boost::python::object& userContext
        )
    {
        if (!PyCallable_Check(iotHubClientFileUploadCallback.ptr()))
        {
            PyErr_SetString(PyExc_TypeError, "upload_to_blob expected type callable");
            boost::python::throw_error_already_set();
            return;
        }
        BlobUploadContext *blobUploadContext = new BlobUploadContext();
        blobUploadContext->blobUploadCallback = iotHubClientFileUploadCallback;
        blobUploadContext->userContext = userContext;

        IOTHUB_CLIENT_RESULT result;
        {
            ScopedGILRelease release;
            result = IoTHubDeviceClient_UploadToBlobAsync(iotHubClientHandle, destinationFileName.c_str(), (const unsigned char*)source.c_str(), size, BlobUploadConfirmationCallback, blobUploadContext);
        }
        if (result != IOTHUB_CLIENT_OK)
        {
            throw IoTHubClientError(__func__, result);
        }
    }
#endif

#ifdef SUPPORT___STR__
    std::string str() const
    {
        std::stringstream s;
        return s.str();
    }

    std::string repr() const
    {
        std::stringstream s;
        s << "IoTHubClient(" << str() << ")";
        return s.str();
    }
#endif
};

class IoTHubDeviceClient : public IoTHubClient<IOTHUB_DEVICE_CLIENT_HANDLE>
{
public:
    IoTHubDeviceClient(const IoTHubDeviceClient& client)
    {
        (void)client;
        throw IoTHubClientError(__func__, IOTHUB_CLIENT_ERROR);
    }

    IoTHubDeviceClient(
        IOTHUB_DEVICE_CLIENT_HANDLE _iotHubClientHandle,
        IOTHUB_TRANSPORT_PROVIDER _protocol
    ) :
         IoTHubClient(_iotHubClientHandle, _protocol, CLIENT_INTERFACE_DEVICE)
    {
        ;
    }

    IoTHubDeviceClient(
        std::string connectionString,
        IOTHUB_TRANSPORT_PROVIDER _protocol
    ) :
        IoTHubClient(connectionString, _protocol, CLIENT_INTERFACE_DEVICE)
    {
        ;
    }

    IoTHubDeviceClient(
        const IoTHubConfig &_config
    ) : IoTHubClient(_config, CLIENT_INTERFACE_DEVICE)
    {
        ;
    }

    IoTHubDeviceClient(
        IoTHubTransport* _iotHubTransport,
        IoTHubConfig* _iotHubConfig
    ) : IoTHubClient(_iotHubTransport, _iotHubConfig, CLIENT_INTERFACE_DEVICE)
    {
        ;
    }

#ifndef MACOSX
    IoTHubDeviceClient(
        std::string iothub_uri,
        std::string device_id,
        SECURITY_TYPE security_type,
        IOTHUB_TRANSPORT_PROVIDER _protocol
    ) : IoTHubClient(iothub_uri, device_id, security_type, _protocol, CLIENT_INTERFACE_DEVICE)
    {
        ;
    }
#endif
};

class InvokeModuleOrDeviceMethodContext
{
public:
    boost::python::object userCallback;
    boost::python::object userContext;

    InvokeModuleOrDeviceMethodContext(boost::python::object _userCallback, boost::python::object _userContext)
    {
        userCallback = _userCallback;
        userContext = _userContext;
    }
};

extern "C"
void
iotHubInvokeModuleOrDeviceMethodCallback(IOTHUB_CLIENT_RESULT result, int responseStatus, unsigned char* responsePayload, size_t responsePayloadSize, void* context)
{
    InvokeModuleOrDeviceMethodContext *invokeContext = (InvokeModuleOrDeviceMethodContext *)context;
    boost::python::object userCallback = invokeContext->userCallback;
    boost::python::object userContext = invokeContext->userContext;

    IoTHubMethodResponse methodResponse = IoTHubMethodResponse(result, responseStatus, responsePayload, responsePayloadSize);

    {
        ScopedGILAcquire acquire;
        try {
            userCallback(methodResponse, userContext);
        }
        catch (const boost::python::error_already_set)
        {
            // Catch and ignore exception that is thrown in Python callback.
            // There is nothing we can do about it here.
            PyErr_Print();
        }
    }
    delete invokeContext;
}


class IoTHubModuleClient : public IoTHubClient<IOTHUB_MODULE_CLIENT_HANDLE>
{
public:
    IoTHubModuleClient(const IoTHubModuleClient& client)
    {
        (void)client;
        throw IoTHubClientError(__func__, IOTHUB_CLIENT_ERROR);
    }


    IoTHubModuleClient() : IoTHubClient(CLIENT_INTERFACE_MODULE)
    {
        ;
    }

    IoTHubModuleClient(const IoTHubClient& client) : IoTHubClient(client, CLIENT_INTERFACE_MODULE)
    {
        ;
    }

    IoTHubModuleClient(
        IOTHUB_MODULE_CLIENT_HANDLE _iotHubClientHandle,
        IOTHUB_TRANSPORT_PROVIDER _protocol
    ) :
         IoTHubClient(_iotHubClientHandle, _protocol, CLIENT_INTERFACE_MODULE)
    {
        ;
    }

    IoTHubModuleClient(
        std::string connectionString,
        IOTHUB_TRANSPORT_PROVIDER _protocol
    ) :
        IoTHubClient(connectionString, _protocol, CLIENT_INTERFACE_MODULE)
    {
        ;
    }

    IoTHubModuleClient(
        const IoTHubConfig &_config
    ) : IoTHubClient(_config, CLIENT_INTERFACE_MODULE)
    {
        ;
    }

    IoTHubModuleClient(
        IoTHubTransport* _iotHubTransport,
        IoTHubConfig* _iotHubConfig
    ) : IoTHubClient(_iotHubTransport, _iotHubConfig, CLIENT_INTERFACE_MODULE)
    {
        ;
    }

#ifndef MACOSX
    IoTHubModuleClient(
        std::string iothub_uri,
        std::string device_id,
        SECURITY_TYPE security_type,
        IOTHUB_TRANSPORT_PROVIDER _protocol
    ) : IoTHubClient(iothub_uri, device_id, security_type, _protocol, CLIENT_INTERFACE_MODULE)
    {
        ;
    }
#endif

    void SendEventToOutputAsync(
        std::string outputName,
        IoTHubMessage &eventMessage,
        boost::python::object& messageCallback,
        boost::python::object& userContext
        )
    {
        if (!PyCallable_Check(messageCallback.ptr()))
        {
            PyErr_SetString(PyExc_TypeError, "send_event_async expected type callable");
            boost::python::throw_error_already_set();
            return;
        }
        IOTHUB_CLIENT_RESULT result;
        SendContext *sendContext = new SendContext();
        sendContext->messageCallback = messageCallback;
        sendContext->userContext = userContext;
        sendContext->eventMessage = eventMessage.Clone();
        {
            ScopedGILRelease release;
            result = IoTHubModuleClient_SendEventToOutputAsync(iotHubClientHandle, eventMessage.Handle(), outputName.c_str(), SendConfirmationCallback, sendContext);
        }
        if (result != IOTHUB_CLIENT_OK)
        {
            throw IoTHubClientError(__func__, result);
        }
    }

    void SetInputMessageCallback(
        std::string inputName,
        boost::python::object& messageCallback,
        boost::python::object& userContext
        )
    {
        if (!PyCallable_Check(messageCallback.ptr()))
        {
            PyErr_SetString(PyExc_TypeError, "set_message_callback expected type callable");
            boost::python::throw_error_already_set();
            return;
        }
        ReceiveContext *receiveContext = new ReceiveContext();
        receiveContext->messageCallback = messageCallback;
        receiveContext->userContext = userContext;
        IOTHUB_CLIENT_RESULT result;
        {
            ScopedGILRelease release;
            result = IoTHubModuleClient_SetInputMessageCallback(iotHubClientHandle, inputName.c_str(),  ReceiveMessageCallback, receiveContext);
        }
        if (result != IOTHUB_CLIENT_OK)
        {
            throw IoTHubClientError(__func__, result);
        }
    }

    void CreateFromEnvironment(IOTHUB_TRANSPORT_PROVIDER _protocol)
    {
        protocol = _protocol;

        {
            ScopedGILRelease release;
            iotHubClientHandle = IoTHubModuleClient_CreateFromEnvironment(GetProtocol(_protocol));
        }
        if (iotHubClientHandle == NULL)
        {
            throw IoTHubClientError(__func__, IOTHUB_CLIENT_ERROR);
        }
    }

    void InvokeMethodAsyncOnModule(
        const std::string deviceId,
        const std::string moduleId,
        const std::string methodName,
        const std::string methodPayload,
        unsigned int timeout,
        boost::python::object& userCallback,
        boost::python::object& userContext
    )
    {
        if (!PyCallable_Check(userCallback.ptr()))
        {
            PyErr_SetString(PyExc_TypeError, "InvokeMethodAsyncOnModule expected type callable");
            boost::python::throw_error_already_set();
            return;
        }

        InvokeModuleOrDeviceMethodContext *invokeContext = new InvokeModuleOrDeviceMethodContext(userCallback, userContext);
        IOTHUB_CLIENT_RESULT result;

        {
            ScopedGILRelease release;
            result = IoTHubModuleClient_ModuleMethodInvokeAsync(iotHubClientHandle, deviceId.c_str(), moduleId.c_str(), methodName.c_str(), methodPayload.c_str(), timeout, iotHubInvokeModuleOrDeviceMethodCallback, invokeContext);
        }

        if (result != IOTHUB_CLIENT_OK)
        {
            delete invokeContext;
            throw IoTHubClientError(__func__, result);
        }
    }

    void InvokeMethodAsyncOnDevice(
        const std::string deviceId,
        const std::string methodName,
        const std::string methodPayload,
        unsigned int timeout,
        boost::python::object& userCallback,
        boost::python::object& userContext
    )
    {
        if (!PyCallable_Check(userCallback.ptr()))
        {
            PyErr_SetString(PyExc_TypeError, "InvokeMethodAsyncOnModule expected type callable");
            boost::python::throw_error_already_set();
            return;
        }

        InvokeModuleOrDeviceMethodContext *invokeContext = new InvokeModuleOrDeviceMethodContext(userCallback, userContext);
        IOTHUB_CLIENT_RESULT result;

        {
            ScopedGILRelease release;
            result = IoTHubModuleClient_DeviceMethodInvokeAsync(iotHubClientHandle, deviceId.c_str(), methodName.c_str(), methodPayload.c_str(), timeout, iotHubInvokeModuleOrDeviceMethodCallback, invokeContext);
        }

        if (result != IOTHUB_CLIENT_OK)
        {
            delete invokeContext;
            throw IoTHubClientError(__func__, result);
        }

    }
};

using namespace boost::python;

static const char* iothub_client_docstring =
"iothub_client is a Python module for communicating with the Azure IoT Hub";


BOOST_PYTHON_MODULE(IMPORT_NAME)
{
    // init threads for callbacks
    PyEval_InitThreads();
    PlatformCallHandler::Platform_Init();

    // by default enable user, py docstring options, disable c++ signatures
    bool show_user_defined = true;
    bool show_py_signatures = true;
    bool show_cpp_signatures = false;
    docstring_options doc_options(show_user_defined, show_py_signatures, show_cpp_signatures);
    scope().attr("__doc__") = iothub_client_docstring;
    scope().attr("__version__") = VERSION_STRING;

    // exception handlers
    class_<IoTHubMapError>IoTHubMapErrorClass("IoTHubMapErrorArg", init<std::string, MAP_RESULT>());
    IoTHubMapErrorClass.def_readonly("result", &IoTHubMapError::result);
    IoTHubMapErrorClass.def_readonly("func", &IoTHubMapError::func);
    IoTHubMapErrorClass.def("__str__", &IoTHubMapError::str);
    IoTHubMapErrorClass.def("__repr__", &IoTHubMapError::repr);

    class_<IoTHubMessageError>IotHubMessageErrorClass("IoTHubMessageErrorArg", init<std::string, IOTHUB_MESSAGE_RESULT>());
    IotHubMessageErrorClass.def_readonly("result", &IoTHubMessageError::result);
    IotHubMessageErrorClass.def_readonly("func", &IoTHubMessageError::func);
    IotHubMessageErrorClass.def("__str__", &IoTHubMessageError::str);
    IotHubMessageErrorClass.def("__repr__", &IoTHubMessageError::repr);

    class_<IoTHubClientError>IotHubClientErrorClass("IoTHubClientErrorArg", init<std::string, IOTHUB_CLIENT_RESULT>());
    IotHubClientErrorClass.def_readonly("result", &IoTHubClientError::result);
    IotHubClientErrorClass.def_readonly("func", &IoTHubClientError::func);
    IotHubClientErrorClass.def("__str__", &IoTHubClientError::str);
    IotHubClientErrorClass.def("__repr__", &IoTHubClientError::repr);

    register_exception_translator<IoTHubMapError>(iotHubMapError);
    register_exception_translator<IoTHubMessageError>(iothubMessageError);
    register_exception_translator<IoTHubClientError>(iothubClientError);

    // iothub errors derived from BaseException --> IoTHubError --> IoTHubXXXError
    iotHubErrorType = createExceptionClass("IoTHubError");
    iotHubMapErrorType = createExceptionClass("IoTHubMapError", iotHubErrorType);
    iothubMessageErrorType = createExceptionClass("IoTHubMessageError", iotHubErrorType);
    iothubClientErrorType = createExceptionClass("IoTHubClientError", iotHubErrorType);

    // iothub return codes
    enum_<MAP_RESULT>("IoTHubMapResult")
        .value("OK", MAP_OK)
        .value("ERROR", MAP_ERROR)
        .value("INVALIDARG", MAP_INVALIDARG)
        .value("KEYEXISTS", MAP_KEYEXISTS)
        .value("KEYNOTFOUND", MAP_KEYNOTFOUND)
        .value("FILTER_REJECT", MAP_FILTER_REJECT)
        ;

    enum_<IOTHUB_MESSAGE_RESULT>("IoTHubMessageResult")
        .value("OK", IOTHUB_MESSAGE_OK)
        .value("INVALID_ARG", IOTHUB_MESSAGE_INVALID_ARG)
        .value("INVALID_TYPE", IOTHUB_MESSAGE_INVALID_TYPE)
        .value("ERROR", IOTHUB_MESSAGE_ERROR)
        ;

    enum_<IOTHUB_CLIENT_RESULT>("IoTHubClientResult")
        .value("OK", IOTHUB_CLIENT_OK)
        .value("INVALID_ARG", IOTHUB_CLIENT_INVALID_ARG)
        .value("ERROR", IOTHUB_CLIENT_ERROR)
        .value("INVALID_SIZE", IOTHUB_CLIENT_INVALID_SIZE)
        .value("INDEFINITE_TIME", IOTHUB_CLIENT_INDEFINITE_TIME)
        ;

    enum_<IOTHUB_CLIENT_STATUS>("IoTHubClientStatus")
        .value("IDLE", IOTHUB_CLIENT_SEND_STATUS_IDLE)
        .value("BUSY", IOTHUB_CLIENT_SEND_STATUS_BUSY)
        ;

    enum_<IOTHUB_CLIENT_CONFIRMATION_RESULT>("IoTHubClientConfirmationResult")
        .value("OK", IOTHUB_CLIENT_CONFIRMATION_OK)
        .value("BECAUSE_DESTROY", IOTHUB_CLIENT_CONFIRMATION_BECAUSE_DESTROY)
        .value("MESSAGE_TIMEOUT", IOTHUB_CLIENT_CONFIRMATION_MESSAGE_TIMEOUT)
        .value("ERROR", IOTHUB_CLIENT_CONFIRMATION_ERROR)
        ;

    enum_<IOTHUBMESSAGE_DISPOSITION_RESULT>("IoTHubMessageDispositionResult")
        .value("ACCEPTED", IOTHUBMESSAGE_ACCEPTED)
        .value("REJECTED", IOTHUBMESSAGE_REJECTED)
        .value("ABANDONED", IOTHUBMESSAGE_ABANDONED)
        ;

    enum_<IOTHUBMESSAGE_CONTENT_TYPE>("IoTHubMessageContent")
        .value("BYTEARRAY", IOTHUBMESSAGE_BYTEARRAY)
        .value("STRING", IOTHUBMESSAGE_STRING)
        .value("UNKNOWN", IOTHUBMESSAGE_UNKNOWN)
        ;

    enum_<IOTHUB_CLIENT_CONNECTION_STATUS>("IoTHubConnectionStatus")
        .value("AUTHENTICATED", IOTHUB_CLIENT_CONNECTION_AUTHENTICATED)
        .value("UNAUTHENTICATED", IOTHUB_CLIENT_CONNECTION_UNAUTHENTICATED)
        ;

    enum_<IOTHUB_CLIENT_CONNECTION_STATUS_REASON>("IoTHubClientConnectionStatusReason")
        .value("EXPIRED_SAS_TOKEN", IOTHUB_CLIENT_CONNECTION_EXPIRED_SAS_TOKEN)
        .value("DEVICE_DISABLED", IOTHUB_CLIENT_CONNECTION_DEVICE_DISABLED)
        .value("BAD_CREDENTIAL", IOTHUB_CLIENT_CONNECTION_BAD_CREDENTIAL)
        .value("RETRY_EXPIRED", IOTHUB_CLIENT_CONNECTION_RETRY_EXPIRED)
        .value("NO_NETWORK", IOTHUB_CLIENT_CONNECTION_NO_NETWORK)
        .value("COMMUNICATION_ERROR", IOTHUB_CLIENT_CONNECTION_COMMUNICATION_ERROR)
        .value("CONNECTION_OK", IOTHUB_CLIENT_CONNECTION_OK)
        ;

    enum_<IOTHUB_CLIENT_RETRY_POLICY>("IoTHubClientRetryPolicy")
        .value("RETRY_NONE", IOTHUB_CLIENT_RETRY_NONE)
        .value("RETRY_IMMEDIATE", IOTHUB_CLIENT_RETRY_IMMEDIATE)
        .value("RETRY_INTERVAL", IOTHUB_CLIENT_RETRY_INTERVAL)
        .value("RETRY_LINEAR_BACKOFF", IOTHUB_CLIENT_RETRY_LINEAR_BACKOFF)
        .value("RETRY_EXPONENTIAL_BACKOFF", IOTHUB_CLIENT_RETRY_EXPONENTIAL_BACKOFF)
        .value("RETRY_EXPONENTIAL_BACKOFF_WITH_JITTER", IOTHUB_CLIENT_RETRY_EXPONENTIAL_BACKOFF_WITH_JITTER)
        .value("RETRY_RANDOM", IOTHUB_CLIENT_RETRY_RANDOM)
        ;

    enum_<DEVICE_TWIN_UPDATE_STATE>("IoTHubTwinUpdateState")
        .value("COMPLETE", DEVICE_TWIN_UPDATE_COMPLETE)
        .value("PARTIAL", DEVICE_TWIN_UPDATE_PARTIAL)
        ;

    enum_<IOTHUB_TRANSPORT_PROVIDER>("IoTHubTransportProvider")
#ifdef USE_HTTP
        .value("HTTP", HTTP)
#endif
#ifdef USE_AMQP
        .value("AMQP", AMQP)
#endif
#ifdef USE_MQTT
        .value("MQTT", MQTT)
#endif
#ifdef USE_WEBSOCKETS
#ifdef USE_AMQP
        .value("AMQP_WS", AMQP_WS)
#endif
#ifdef USE_MQTT
        .value("MQTT_WS", MQTT_WS)
#endif
#endif
        ;

    enum_<IOTHUB_CLIENT_FILE_UPLOAD_RESULT>("IoTHubClientFileUploadResult")
        .value("OK", FILE_UPLOAD_OK)
        .value("ERROR", FILE_UPLOAD_ERROR)
        ;

    enum_<SECURITY_TYPE>("IoTHubSecurityType")
        .value("UNKNOWN", UNKNOWN)
        .value("SAS", SAS)
        .value("X509", X509)
        ;

    class_<GetRetryPolicyReturnValue>("GetRetryPolicyReturnValue")
        .def_readonly("retryPolicy", &GetRetryPolicyReturnValue::retryPolicy)
        .def_readonly("retryTimeoutLimitInSeconds", &GetRetryPolicyReturnValue::retryTimeoutLimitInSeconds)
        // Python helpers
#ifdef SUPPORT___STR__
        .def("__str__", &IoTHubMap::str)
        .def("__repr__", &IoTHubMap::repr)
#endif
        ;

    // classes
    class_<IoTHubMap>("IoTHubMap")
        .def(init<>())
        .def(init<object &>())
        .def("add", &IoTHubMap::Add)
        .def("add_or_update", &IoTHubMap::AddOrUpdate)
        .def("delete", &IoTHubMap::Delete)
        .def("contains_key", &IoTHubMap::ContainsKey)
        .def("contains_value", &IoTHubMap::ContainsValue)
        .def("get_value_from_key", &IoTHubMap::GetValueFromKey)
        .def("get_internals", &IoTHubMap::GetInternals)
        // Python helpers
#ifdef SUPPORT___STR__
        .def("__str__", &IoTHubMap::str)
        .def("__repr__", &IoTHubMap::repr)
#endif
        ;

    class_<IoTHubMessageDiagnosticPropertyData, boost::noncopyable>("IoTHubMessageDiagnosticPropertyData", no_init)
        .def(init<std::string, std::string>())
        .def("get_diagnostic_id", &IoTHubMessageDiagnosticPropertyData::GetDiagnosticId)
        .def("get_diagnostic_time_utc", &IoTHubMessageDiagnosticPropertyData::GetDiagnosticCreationTimeUtc)
        // Python helpers
#ifdef SUPPORT___STR__
        .def("__str__", &IoTHubMessageDiagnosticPropertyData::str)
        .def("__repr__", &IoTHubMessageDiagnosticPropertyData::repr)
#endif
        ;

    class_<IoTHubMessage>("IoTHubMessage", no_init)
        .def(init<PyObject *>())
        .def(init<std::string>())
        .def("get_bytearray", &IoTHubMessage::GetBytearray)
        .def("get_string", &IoTHubMessage::GetString)
        .def("get_content_type", &IoTHubMessage::GetContentType)
        .def("get_content_type_system_property", &IoTHubMessage::GetContentTypeSystemProperty)
        .def("set_content_type_system_property", &IoTHubMessage::SetContentTypeSystemProperty)
        .def("get_content_encoding_system_property", &IoTHubMessage::GetContentEncodingSystemProperty)
        .def("set_content_encoding_system_property", &IoTHubMessage::SetContentEncodingSystemProperty)
        .def("get_diagnostic_property_data", &IoTHubMessage::GetDiagnosticPropertyData, return_internal_reference<1>())
        .def("set_diagnostic_property_data", &IoTHubMessage::SetDiagnosticPropertyData)
        .def("properties", &IoTHubMessage::Properties, return_internal_reference<1>())
        .add_property("message_id", &IoTHubMessage::GetMessageId, &IoTHubMessage::SetMessageId)
        .add_property("correlation_id", &IoTHubMessage::GetCorrelationId, &IoTHubMessage::SetCorrelationId)
        .add_property("input_name", &IoTHubMessage::GetInputName)
        .add_property("output_name", &IoTHubMessage::GetOutputName)
        .add_property("connection_device_id", &IoTHubMessage::GetConnectionDeviceId)
        .add_property("connection_module_id", &IoTHubMessage::GetConnectionModuleId)
        // Python helpers
#ifdef SUPPORT___STR__
        .def("__str__", &IoTHubMessage::str)
        .def("__repr__", &IoTHubMessage::repr)
#endif
        ;

    class_<DeviceMethodReturnValue, boost::noncopyable>("DeviceMethodReturnValue")
        .def_readwrite("response", &DeviceMethodReturnValue::response)
        .def_readwrite("status", &DeviceMethodReturnValue::status)
#ifdef SUPPORT___STR__
        .def("__str__", &DeviceMethodReturnValue::str)
        .def("__repr__", &DeviceMethodReturnValue::repr)
#endif
        ;

    class_<IoTHubConfig, boost::noncopyable>("IoTHubConfig", no_init)
        .def(init<IOTHUB_TRANSPORT_PROVIDER, std::string, std::string, std::string, std::string, std::string, std::string>())
        // Python helpers
#ifdef SUPPORT___STR__
        .def("__str__", &IoTHubConfig::str)
        .def("__repr__", &IoTHubConfig::repr)
#endif
        ;

    class_<IoTHubTransport, boost::noncopyable>("IoTHubTransport", no_init)
        .def(init<IOTHUB_TRANSPORT_PROVIDER, std::string, std::string>())
        // Python helpers
#ifdef SUPPORT___STR__
        .def("__str__", &IoTHubTransport::str)
        .def("__repr__", &IoTHubTransport::repr)
#endif
        ;

    class_<IoTHubDeviceClient, boost::noncopyable>("IoTHubClient", no_init)
        .def(init<std::string, IOTHUB_TRANSPORT_PROVIDER>())
        .def(init<IoTHubTransport*, IoTHubConfig*>())
#ifndef MACOSX
        .def(init<std::string, std::string, SECURITY_TYPE, IOTHUB_TRANSPORT_PROVIDER>())
#endif
        .def("send_event_async", &IoTHubDeviceClient::SendEventAsync)
        .def("set_message_callback", &IoTHubDeviceClient::SetMessageCallback)
        .def("set_connection_status_callback", &IoTHubDeviceClient::SetConnectionStatusCallback)
        .def("set_retry_policy", &IoTHubDeviceClient::SetRetryPolicy)
        .def("get_retry_policy", &IoTHubDeviceClient::GetRetryPolicy)
        .def("set_device_twin_callback", &IoTHubDeviceClient::SetTwinCallback)
        .def("send_reported_state", &IoTHubDeviceClient::SendReportedState)
        .def("set_device_method_callback", &IoTHubDeviceClient::SetMethodCallback)
        .def("set_device_method_callback_ex", &IoTHubDeviceClient::SetDeviceMethodCallbackEx)
        .def("device_method_response", &IoTHubDeviceClient::DeviceMethodResponse)
        .def("set_option", &IoTHubDeviceClient::SetOption)
        .def("get_send_status", &IoTHubDeviceClient::GetSendStatus)
        .def("get_last_message_receive_time", &IoTHubDeviceClient::GetLastMessageReceiveTime)
#ifndef DONT_USE_UPLOADTOBLOB
        .def("upload_blob_async", &IoTHubDeviceClient::UploadToBlobAsync)
#endif
        // attributes
        .def_readonly("protocol", &IoTHubDeviceClient::protocol)
        // Python helpers
#ifdef SUPPORT___STR__
        .def("__str__", &IoTHubDeviceClient::str)
        .def("__repr__", &IoTHubDeviceClient::repr)
#endif
        ;

    class_<IoTHubDeviceClient, boost::noncopyable>("IoTHubDeviceClient", no_init)
        .def(init<std::string, IOTHUB_TRANSPORT_PROVIDER>())
        .def(init<IoTHubTransport*, IoTHubConfig*>())
#ifndef MACOSX
        .def(init<std::string, std::string, SECURITY_TYPE, IOTHUB_TRANSPORT_PROVIDER>())
#endif
        .def("send_event_async", &IoTHubDeviceClient::SendEventAsync)
        .def("set_message_callback", &IoTHubDeviceClient::SetMessageCallback)
        .def("set_connection_status_callback", &IoTHubDeviceClient::SetConnectionStatusCallback)
        .def("set_retry_policy", &IoTHubDeviceClient::SetRetryPolicy)
        .def("get_retry_policy", &IoTHubDeviceClient::GetRetryPolicy)
        .def("set_device_twin_callback", &IoTHubDeviceClient::SetTwinCallback)
        .def("send_reported_state", &IoTHubDeviceClient::SendReportedState)
        .def("set_device_method_callback", &IoTHubDeviceClient::SetMethodCallback)
        .def("device_method_response", &IoTHubDeviceClient::DeviceMethodResponse)
        .def("set_option", &IoTHubDeviceClient::SetOption)
        .def("get_send_status", &IoTHubDeviceClient::GetSendStatus)
        .def("get_last_message_receive_time", &IoTHubDeviceClient::GetLastMessageReceiveTime)
#ifndef DONT_USE_UPLOADTOBLOB
        .def("upload_blob_async", &IoTHubDeviceClient::UploadToBlobAsync)
#endif
        // attributes
        .def_readonly("protocol", &IoTHubDeviceClient::protocol)
        // Python helpers
#ifdef SUPPORT___STR__
        .def("__str__", &IoTHubDeviceClient::str)
        .def("__repr__", &IoTHubDeviceClient::repr)
#endif
            ;

    class_<IoTHubMethodResponse>("IoTHubMethodResponse")
        .def(init<>())
        .add_property("result", &IoTHubMethodResponse::result)
        .add_property("responseStatus", &IoTHubMethodResponse::responseStatus)
        .add_property("responsePayload", &IoTHubMethodResponse::responsePayload)
        ;

    class_<IoTHubModuleClient, boost::noncopyable>("IoTHubModuleClient", no_init)
        .def(init<std::string, IOTHUB_TRANSPORT_PROVIDER>())
        .def(init<IoTHubTransport*, IoTHubConfig*>())
#ifndef MACOSX
        .def(init<std::string, std::string, SECURITY_TYPE, IOTHUB_TRANSPORT_PROVIDER>())
#endif
        .def(init<>())
        .def("send_event_async", &IoTHubModuleClient::SendEventAsync)
        .def("set_message_callback", &IoTHubModuleClient::SetMessageCallback)
        .def("set_connection_status_callback", &IoTHubModuleClient::SetConnectionStatusCallback)
        .def("set_retry_policy", &IoTHubModuleClient::SetRetryPolicy)
        .def("get_retry_policy", &IoTHubModuleClient::GetRetryPolicy)
        .def("set_module_twin_callback", &IoTHubModuleClient::SetTwinCallback)
        .def("send_reported_state", &IoTHubModuleClient::SendReportedState)
        .def("set_module_method_callback", &IoTHubModuleClient::SetMethodCallback)
        .def("device_method_response", &IoTHubModuleClient::DeviceMethodResponse)
        .def("set_option", &IoTHubModuleClient::SetOption)
        .def("get_send_status", &IoTHubModuleClient::GetSendStatus)
        .def("get_last_message_receive_time", &IoTHubModuleClient::GetLastMessageReceiveTime)
        .def("send_event_async", &IoTHubModuleClient::SendEventToOutputAsync)
        .def("set_message_callback", &IoTHubModuleClient::SetInputMessageCallback)
        .def("create_from_environment", &IoTHubModuleClient::CreateFromEnvironment)
        .def("invoke_method_async", &IoTHubModuleClient::InvokeMethodAsyncOnModule)
        .def("invoke_method_async", &IoTHubModuleClient::InvokeMethodAsyncOnDevice)
        // attributes
        .def_readonly("protocol", &IoTHubModuleClient::protocol)
        // Python helpers
#ifdef SUPPORT___STR__
        .def("__str__", &IoTHubModuleClient::str)
        .def("__repr__", &IoTHubModuleClient::repr)
#endif
            ;

};
