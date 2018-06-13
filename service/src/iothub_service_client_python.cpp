
// Copyright(c) Microsoft.All rights reserved.
// Licensed under the MIT license.See LICENSE file in the project root for full license information.

#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable:4459 4100 4121 4244) /* This is because boost python has a self variable that hides a global */
#endif

#include <boost/python.hpp>
#include <boost/python/suite/indexing/vector_indexing_suite.hpp>

#ifdef _MSC_VER
#pragma warning(pop)
#endif

#include <string>
#include <vector>
#include <list>

#include "azure_c_shared_utility/platform.h"
#include "azure_c_shared_utility/map.h"
#include "iothub_sc_version.h"
#include "iothub_service_client_auth.h"
#include "iothub_registrymanager.h"
#include "iothub_messaging.h"
#include "iothub_devicemethod.h"
#include "iothub_devicetwin.h"
#include "iothubtransporthttp.h"
#include "iothubtransportamqp.h"
#include "iothub_client_core_common.h"

#ifndef IMPORT_NAME
#define IMPORT_NAME iothub_service_client
#endif

#define VERSION_STRING "1.4.0.0b2"

#if PY_MAJOR_VERSION >= 3
#define IS_PY3
#endif

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

typedef struct LIST_ITEM_INSTANCE_TAG
{
    const void* item;
    void* next;
} LIST_ITEM_INSTANCE;

typedef struct SINGLYLINKEDLIST_INSTANCE_TAG
{
    LIST_ITEM_INSTANCE* head;
} LIST_INSTANCE;

//
// note: all new allocations throw a std::bad_alloc exception which trigger a MemoryError in Python
//

// helper classes for transitions between Python and C++ layer

class ScopedGILAcquire : boost::noncopyable
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

class ScopedGILRelease : boost::noncopyable
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

//
//  IotHubError exception handler base class
//

static PyObject* iotHubErrorType = NULL;

class IoTHubError : public std::exception
{
public:
    std::string exc;
    std::string cls;
    std::string func;

    IoTHubError(
        std::string _exc,
        std::string _cls,
        std::string _func
        ) :
        exc(_exc),
        cls(_cls)
    {
        // only display class names in camel case
        func = (_func[0] != 'I') ? CamelToPy(_func) : _func;
    }

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

static PyObject *iotHubMapErrorType = NULL;

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
        filter(false)
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
        IoTHubMap* retVal;
        MAP_FILTER_CALLBACK mapFilterFunc = NULL;
        if (PyCallable_Check(_mapFilterCallback.ptr()))
        {
            mapFilterCallback = _mapFilterCallback;
            mapFilterFunc = &MapFilterCallback;
            retVal = new IoTHubMap(Map_Create(mapFilterFunc));
        }
        else if (Py_None != _mapFilterCallback.ptr())
        {
            PyErr_SetString(PyExc_TypeError, "Create expected type callable or None");
            boost::python::throw_error_already_set();
            retVal = NULL;
        }
        return retVal;
    }

    void Destroy()
    {
        if (mapHandle != NULL)
        {
            if (ownHandle)
            {
                Map_Destroy(mapHandle);
            }
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
            for (size_t i = 0; i < count; i++)
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
};

//
//  iothub_message.h
//

static PyObject *iothubMessageErrorType = NULL;

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
};

//
//  iothub_sc_version.h
//  iothub_service_client_auth.h
//
static PyObject *iothubServiceClientAuthErrorType = NULL;

class IoTHubServiceClientAuthError : public IoTHubError
{
public:
    IoTHubServiceClientAuthError(
        std::string _func
        ) :
        IoTHubError(
            "IoTHubServiceClientAuthError",
            "IoTHubServiceClientAuth",
            _func
            )
    {
    }

    virtual std::string decode_error() const
    {
        std::stringstream s;
        s << "IoTHubServiceClientAuthError: Service Client Authentication Handle is NULL.";
        return s.str();
    }
};

void iothubServiceClientAuthError(const IoTHubServiceClientAuthError& x)
{
    boost::python::object pythonExceptionInstance(x);
    PyErr_SetObject(iothubServiceClientAuthErrorType, pythonExceptionInstance.ptr());
};

class IoTHubServiceClientAuth
{
    IOTHUB_SERVICE_CLIENT_AUTH_HANDLE _iothubServiceClientAuthHandle;
public:

    IoTHubServiceClientAuth(
        std::string connectionString
        ) : _iothubServiceClientAuthHandle(NULL)
    {
        ScopedGILRelease release;
        _iothubServiceClientAuthHandle = IoTHubServiceClientAuth_CreateFromConnectionString(connectionString.c_str());

        if (_iothubServiceClientAuthHandle == NULL)
        {
            throw IoTHubServiceClientAuthError(__func__);
        }
    }

    ~IoTHubServiceClientAuth()
    {
        Destroy();
    }

    void Destroy()
    {
        ScopedGILRelease release;

        if (_iothubServiceClientAuthHandle != NULL)
        {
            IoTHubServiceClientAuth_Destroy(_iothubServiceClientAuthHandle);
            _iothubServiceClientAuthHandle = NULL;
        }
    }

    IOTHUB_SERVICE_CLIENT_AUTH_HANDLE GetHandle()
    {
        return _iothubServiceClientAuthHandle;
    }
};

//
//  iothub_registrymanager.h
//

static PyObject *iothubRegistryManagerErrorType = NULL;

class IoTHubRegistryManagerError : public IoTHubError
{
public:
    IoTHubRegistryManagerError(
        std::string _func,
        IOTHUB_REGISTRYMANAGER_RESULT _result
        ) :
        IoTHubError(
            "IoTHubRegistryManagerError",
            "IoTHubRegistryManager",
            _func
            )
    {
        result = _result;
    }

    IOTHUB_REGISTRYMANAGER_RESULT result;

    virtual std::string decode_error() const
    {
        std::stringstream s;
        s << "IoTHubRegistryManagerResult.";
        switch (result)
        {
        case IOTHUB_REGISTRYMANAGER_OK: s << "OK"; break;
        case IOTHUB_REGISTRYMANAGER_INVALID_ARG: s << "INVALID_ARG"; break;
        case IOTHUB_REGISTRYMANAGER_ERROR: s << "ERROR"; break;
        case IOTHUB_REGISTRYMANAGER_JSON_ERROR: s << "JSON_ERROR"; break;
        case IOTHUB_REGISTRYMANAGER_HTTPAPI_ERROR: s << "HTTPAPI_ERROR"; break;
        case IOTHUB_REGISTRYMANAGER_HTTP_STATUS_ERROR: s << "HTTP_STATUS_ERROR"; break;
        case IOTHUB_REGISTRYMANAGER_DEVICE_EXIST: s << "DEVICE_EXIST"; break;
        case IOTHUB_REGISTRYMANAGER_DEVICE_NOT_EXIST: s << "DEVICE_NOT_EXIST"; break;
        case IOTHUB_REGISTRYMANAGER_CALLBACK_NOT_SET: s << "CALLBACK_NOT_SET"; break;
        case IOTHUB_REGISTRYMANAGER_INVALID_VERSION: s << "INVALID_VERSION"; break;
        }
        return s.str();
    }
};

void iothubRegistryManagerError(const IoTHubRegistryManagerError& x)
{
    boost::python::object pythonExceptionInstance(x);
    PyErr_SetObject(iothubRegistryManagerErrorType, pythonExceptionInstance.ptr());
};

// class exposed to py used as parameter for CreateDevice
struct DEVICE_CREATE
{
    std::string deviceId;
    std::string primaryKey;
    std::string secondaryKey;
};

class IoTHubDeviceCapabilities
{
    bool iotEdge;

public:
    IoTHubDeviceCapabilities() : 
        iotEdge(false)
    {
        ;
    }

    bool GetIotEdge()
    {
        return iotEdge;
    }

    void SetIotEdge(bool _iotEdge)
    {
        iotEdge = _iotEdge;
    }
};


class IoTHubRegistryManager
{
    IOTHUB_SERVICE_CLIENT_AUTH_HANDLE _iothubServiceClientAuthHandle;
    IOTHUB_REGISTRYMANAGER_HANDLE _iothubRegistryManagerHandle;
private:

    void CopyDeviceToDeviceEx(IOTHUB_DEVICE *source, IOTHUB_DEVICE_EX *dest)
    {
        dest->version = 1;
        dest->deviceId = source->deviceId;
        dest->primaryKey = source->primaryKey;
        dest->secondaryKey = source->secondaryKey;
        dest->generationId = source->generationId;
        dest->eTag = source->eTag;
        dest->connectionState = source->connectionState;
        dest->connectionStateUpdatedTime = source->connectionStateUpdatedTime;
        dest->status = source->status;
        dest->statusReason = source->statusReason;
        dest->statusUpdatedTime = source->statusUpdatedTime;
        dest->lastActivityTime = source->lastActivityTime;
        dest->cloudToDeviceMessageCount = source->cloudToDeviceMessageCount;
        dest->isManaged = source->isManaged;
        dest->configuration = source->configuration;
        dest->deviceProperties = source->deviceProperties;
        dest->serviceProperties = source->serviceProperties;
        dest->authMethod = source->authMethod;
        // Legacy devices don't have concept of edge capability.
        dest->iotEdge_capable = false;
    }
    
public:

    IoTHubRegistryManager(
        std::string connectionString
        ) : _iothubServiceClientAuthHandle(NULL), 
			_iothubRegistryManagerHandle(NULL)
    {
        ScopedGILRelease release;
        PlatformCallHandler::Platform_Init();

        _iothubServiceClientAuthHandle = IoTHubServiceClientAuth_CreateFromConnectionString(connectionString.c_str());
        if (_iothubServiceClientAuthHandle == NULL)
        {
            throw IoTHubRegistryManagerError(__func__, IOTHUB_REGISTRYMANAGER_ERROR);
        }

        _iothubRegistryManagerHandle = IoTHubRegistryManager_Create(_iothubServiceClientAuthHandle);
        if (_iothubRegistryManagerHandle == NULL)
        {
            throw IoTHubRegistryManagerError(__func__, IOTHUB_REGISTRYMANAGER_ERROR);
        }
    }

    IoTHubRegistryManager(
        IoTHubServiceClientAuth iothubAuth
        ) : _iothubServiceClientAuthHandle(NULL), _iothubRegistryManagerHandle(NULL)
    {
        ScopedGILRelease release;
        PlatformCallHandler::Platform_Init();

        _iothubServiceClientAuthHandle = iothubAuth.GetHandle();
        if (_iothubServiceClientAuthHandle == NULL)
        {
            throw IoTHubRegistryManagerError(__func__, IOTHUB_REGISTRYMANAGER_ERROR);
        }

        _iothubRegistryManagerHandle = IoTHubRegistryManager_Create(_iothubServiceClientAuthHandle);
        if (_iothubRegistryManagerHandle == NULL)
        {
            throw IoTHubRegistryManagerError(__func__, IOTHUB_REGISTRYMANAGER_ERROR);
        }
    }

    ~IoTHubRegistryManager()
    {
        PlatformCallHandler::Platform_DeInit();
        Destroy();
    }

    void Destroy()
    {
        ScopedGILRelease release;

        if (_iothubRegistryManagerHandle != NULL)
        {
            IoTHubRegistryManager_Destroy(_iothubRegistryManagerHandle);
            _iothubRegistryManagerHandle = NULL;
        }

        if (_iothubServiceClientAuthHandle != NULL)
        {
            {
                IoTHubServiceClientAuth_Destroy(_iothubServiceClientAuthHandle);
                _iothubServiceClientAuthHandle = NULL;
            }
        }
    }

    IOTHUB_DEVICE_EX CreateDevice(
        std::string deviceId,
        std::string primaryKey,
        std::string secondaryKey,
        IOTHUB_REGISTRYMANAGER_AUTH_METHOD authMethod,
        IoTHubDeviceCapabilities *deviceCapabilities=NULL
        )
    {
        IOTHUB_REGISTRYMANAGER_RESULT result = IOTHUB_REGISTRYMANAGER_OK;

        IOTHUB_REGISTRY_DEVICE_CREATE_EX deviceCreateEx;
        memset(&deviceCreateEx, 0, sizeof(deviceCreateEx));

        IOTHUB_DEVICE_EX iothubDevice;
        memset(&iothubDevice, 0, sizeof(iothubDevice));
        iothubDevice.version = 1;

        deviceCreateEx.version = 1;
        deviceCreateEx.deviceId = deviceId.c_str();
        deviceCreateEx.primaryKey = primaryKey.c_str();
        deviceCreateEx.secondaryKey = secondaryKey.c_str();
        deviceCreateEx.authMethod = authMethod;
        if (deviceCapabilities != NULL)
        {
            deviceCreateEx.iotEdge_capable = deviceCapabilities->GetIotEdge();
        }
        else
        {
            deviceCreateEx.iotEdge_capable = false;
        }

        ScopedGILRelease release;
        result = IoTHubRegistryManager_CreateDevice_Ex(_iothubRegistryManagerHandle, &deviceCreateEx, &iothubDevice);

        if (result != IOTHUB_REGISTRYMANAGER_OK)
        {
            throw IoTHubRegistryManagerError(__func__, result);
        }
        return iothubDevice;
    }

    IOTHUB_DEVICE_EX GetDevice(
        std::string deviceId
        )
    {
        IOTHUB_DEVICE_EX iothubDeviceEx;
        IOTHUB_REGISTRYMANAGER_RESULT result = IOTHUB_REGISTRYMANAGER_OK;

        memset(&iothubDeviceEx, 0, sizeof(iothubDeviceEx));
        iothubDeviceEx.version = 1;

        ScopedGILRelease release;
        result = IoTHubRegistryManager_GetDevice_Ex(_iothubRegistryManagerHandle, deviceId.c_str(), &iothubDeviceEx);

        if (result != IOTHUB_REGISTRYMANAGER_OK)
        {
            throw IoTHubRegistryManagerError(__func__, result);
        }
        return iothubDeviceEx;
    }

    void UpdateDevice(
        std::string deviceId,
        std::string primaryKey,
        std::string secondaryKey,
        IOTHUB_DEVICE_STATUS status,
        IOTHUB_REGISTRYMANAGER_AUTH_METHOD authMethod,
        IoTHubDeviceCapabilities *deviceCapabilities=NULL
        )
    {
        IOTHUB_REGISTRYMANAGER_RESULT result = IOTHUB_REGISTRYMANAGER_OK;

        ScopedGILRelease release;
        
        if (deviceCapabilities != NULL)
        {
            IOTHUB_REGISTRY_DEVICE_UPDATE_EX deviceUpdate;
            memset(&deviceUpdate, 0, sizeof(deviceUpdate));
            deviceUpdate.version = 1;
            
            deviceUpdate.deviceId = deviceId.c_str();
            deviceUpdate.primaryKey = primaryKey.c_str();
            deviceUpdate.secondaryKey = secondaryKey.c_str();
            deviceUpdate.status = status;
            deviceUpdate.authMethod = authMethod;
            deviceUpdate.iotEdge_capable = deviceCapabilities->GetIotEdge();

            result = IoTHubRegistryManager_UpdateDevice_Ex(_iothubRegistryManagerHandle, &deviceUpdate);
        }
        else
        {
            IOTHUB_REGISTRY_DEVICE_UPDATE deviceUpdate;
            memset(&deviceUpdate, 0, sizeof(deviceUpdate));
            
            deviceUpdate.deviceId = deviceId.c_str();
            deviceUpdate.primaryKey = primaryKey.c_str();
            deviceUpdate.secondaryKey = secondaryKey.c_str();
            deviceUpdate.status = status;
            deviceUpdate.authMethod = authMethod;
        
            // If deviceCapabilities were not set, we need to use the legacy (non-Ex) Update function.
            // This will never set the edge field to the server which will leave its original value in place.
            result = IoTHubRegistryManager_UpdateDevice(_iothubRegistryManagerHandle, &deviceUpdate);
        }

        if (result != IOTHUB_REGISTRYMANAGER_OK)
        {
            throw IoTHubRegistryManagerError(__func__, result);
        }
    }

    void DeleteDevice(
        std::string deviceId
        )
    {
        IOTHUB_REGISTRYMANAGER_RESULT result = IOTHUB_REGISTRYMANAGER_OK;

        ScopedGILRelease release;
        result = IoTHubRegistryManager_DeleteDevice(_iothubRegistryManagerHandle, deviceId.c_str());

        if (result != IOTHUB_REGISTRYMANAGER_OK)
        {
            throw IoTHubRegistryManagerError(__func__, result);
        }
    }

    boost::python::list GetDeviceList(
        size_t numberOfDevices
        )
    {
        boost::python::list retVal;
        SINGLYLINKEDLIST_HANDLE deviceList = singlylinkedlist_create();
        IOTHUB_REGISTRYMANAGER_RESULT result = IOTHUB_REGISTRYMANAGER_OK;

        ScopedGILRelease release;
        result = IoTHubRegistryManager_GetDeviceList(_iothubRegistryManagerHandle, numberOfDevices, deviceList);

        if (result != IOTHUB_REGISTRYMANAGER_OK)
        {
            throw IoTHubRegistryManagerError(__func__, result);
        }

        if (deviceList != NULL)
        {
            LIST_ITEM_HANDLE next_device = singlylinkedlist_get_head_item(deviceList);
            while (next_device != NULL)
            {
                IOTHUB_DEVICE* device = (IOTHUB_DEVICE*)singlylinkedlist_item_get_value(next_device);
                IOTHUB_DEVICE_EX deviceEx;

                // IoTHubRegistryManager_GetDeviceList has been deprecated and is NOT moving to the 
                // newer model of IOTHUB_DEVICE_EX but just keeping with IOTHUB_DEVICE.  Since rest of Python
                // layer deals with IOTHUB_DEVICE_EX, however, translate this object to IOTHUB_DEVICE_EX.
                CopyDeviceToDeviceEx(device,&deviceEx);
                    
                retVal.append(deviceEx);
                singlylinkedlist_remove(deviceList, next_device);
                next_device = singlylinkedlist_get_head_item(deviceList);
            }
            singlylinkedlist_destroy(deviceList);
        }
        return retVal;
    }

    IOTHUB_REGISTRY_STATISTICS GetStatistics(
        )
    {
        IOTHUB_REGISTRY_STATISTICS registryStatistics;
        IOTHUB_REGISTRYMANAGER_RESULT result = IOTHUB_REGISTRYMANAGER_OK;

        ScopedGILRelease release;
        result = IoTHubRegistryManager_GetStatistics(_iothubRegistryManagerHandle, &registryStatistics);

        if (result != IOTHUB_REGISTRYMANAGER_OK)
        {
            throw IoTHubRegistryManagerError(__func__, result);
        }
        return registryStatistics;
    }

    IOTHUB_MODULE CreateModule(
        std::string deviceId,
        std::string primaryKey,
        std::string secondaryKey,
        std::string moduleId,
        IOTHUB_REGISTRYMANAGER_AUTH_METHOD authMethod
        )
    {
        IOTHUB_REGISTRYMANAGER_RESULT result = IOTHUB_REGISTRYMANAGER_OK;

        IOTHUB_REGISTRY_MODULE_CREATE moduleCreate;
        memset(&moduleCreate, 0, sizeof(moduleCreate));
        moduleCreate.version = 1;

        IOTHUB_MODULE iothubModule;
        memset(&iothubModule, 0, sizeof(iothubModule));
        iothubModule.version = 1;

        moduleCreate.deviceId = deviceId.c_str();
        moduleCreate.primaryKey = primaryKey.c_str();
        moduleCreate.secondaryKey = secondaryKey.c_str();
        moduleCreate.moduleId = moduleId.c_str();
        moduleCreate.authMethod = authMethod;

        ScopedGILRelease release;
        result = IoTHubRegistryManager_CreateModule(_iothubRegistryManagerHandle, &moduleCreate, &iothubModule);

        if (result != IOTHUB_REGISTRYMANAGER_OK)
        {
            throw IoTHubRegistryManagerError(__func__, result);
        }
        return iothubModule;
    }

    void UpdateModule(
        std::string deviceId,
        std::string primaryKey,
        std::string secondaryKey,
        std::string moduleId,
        IOTHUB_REGISTRYMANAGER_AUTH_METHOD authMethod
        )
    {
        IOTHUB_REGISTRYMANAGER_RESULT result = IOTHUB_REGISTRYMANAGER_OK;

        IOTHUB_REGISTRY_MODULE_UPDATE moduleUpdate;
        memset(&moduleUpdate, 0, sizeof(moduleUpdate));
        moduleUpdate.version = 1;

        moduleUpdate.deviceId = deviceId.c_str();
        moduleUpdate.primaryKey = primaryKey.c_str();
        moduleUpdate.secondaryKey = secondaryKey.c_str();
        moduleUpdate.moduleId = moduleId.c_str();
        moduleUpdate.authMethod = authMethod;

        ScopedGILRelease release;
        result = IoTHubRegistryManager_UpdateModule(_iothubRegistryManagerHandle, &moduleUpdate);

        if (result != IOTHUB_REGISTRYMANAGER_OK)
        {
            throw IoTHubRegistryManagerError(__func__, result);
        }
    }

    IOTHUB_MODULE GetModule(
        std::string deviceId,
        std::string moduleId
        )
    {
        IOTHUB_MODULE iothubModule;
        IOTHUB_REGISTRYMANAGER_RESULT result = IOTHUB_REGISTRYMANAGER_OK;

        ScopedGILRelease release;
        iothubModule.version = 1;
        result = IoTHubRegistryManager_GetModule(_iothubRegistryManagerHandle, deviceId.c_str(), moduleId.c_str(), &iothubModule);

        if (result != IOTHUB_REGISTRYMANAGER_OK)
        {
            throw IoTHubRegistryManagerError(__func__, result);
        }
        return iothubModule;
    }

    boost::python::list GetModuleList(
        std::string deviceId
        )
    {
        boost::python::list retVal;
        SINGLYLINKEDLIST_HANDLE moduleList = singlylinkedlist_create();
        IOTHUB_REGISTRYMANAGER_RESULT result = IOTHUB_REGISTRYMANAGER_OK;

        ScopedGILRelease release;
        result = IoTHubRegistryManager_GetModuleList(_iothubRegistryManagerHandle, deviceId.c_str(), moduleList, 1);

        if (result != IOTHUB_REGISTRYMANAGER_OK)
        {
            throw IoTHubRegistryManagerError(__func__, result);
        }

        if (moduleList != NULL)
        {
            LIST_ITEM_HANDLE next_module = singlylinkedlist_get_head_item(moduleList);
            while (next_module != NULL)
            {
                IOTHUB_MODULE* module = (IOTHUB_MODULE*)singlylinkedlist_item_get_value(next_module);
                next_module = singlylinkedlist_get_next_item(next_module);
                retVal.append(*module);
            }
            singlylinkedlist_destroy(moduleList);
        }
        return retVal;
    }

    void DeleteModule(
        std::string deviceId,
        std::string moduleId
        )
    {
        IOTHUB_REGISTRYMANAGER_RESULT result = IOTHUB_REGISTRYMANAGER_OK;

        ScopedGILRelease release;
        result = IoTHubRegistryManager_DeleteModule(_iothubRegistryManagerHandle, deviceId.c_str(), moduleId.c_str());

        if (result != IOTHUB_REGISTRYMANAGER_OK)
        {
            throw IoTHubRegistryManagerError(__func__, result);
        }
    }
};

BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(IoTHubRegistryManager_overloads, CreateDevice, 4, 5)
BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(IoTHubRegistryManager_overloads2, UpdateDevice, 5, 6)

//
//  iothub_messaging.h
//

static PyObject *iothubMessagingErrorType = NULL;

class IoTHubMessagingError : public IoTHubError
{
public:
    IoTHubMessagingError(
        std::string _func,
        IOTHUB_MESSAGING_RESULT _result
        ) :
        IoTHubError(
            "IoTHubMessagingError",
            "IoTHubMessaging",
            _func
            )
    {
        result = _result;
    }

    IOTHUB_MESSAGING_RESULT result;

    virtual std::string decode_error() const
    {
        std::stringstream s;
        s << "IoTHubMessagingResult.";
        switch (result)
        {
        case IOTHUB_MESSAGING_OK: s << "OK"; break;
        case IOTHUB_MESSAGING_INVALID_ARG: s << "INVALID_ARG"; break;
        case IOTHUB_MESSAGING_ERROR: s << "ERROR"; break;
        case IOTHUB_MESSAGING_INVALID_JSON: s << "INVALID_ERROR"; break;
        case IOTHUB_MESSAGING_DEVICE_EXIST: s << "DEVICE_EXIST"; break;
        case IOTHUB_MESSAGING_CALLBACK_NOT_SET: s << "CALLBACK_NOT_SET"; break;
        }
        return s.str();
    }

};

void iothubMessagingError(const IoTHubMessagingError& x)
{
    boost::python::object pythonExceptionInstance(x);
    PyErr_SetObject(iothubMessagingErrorType, pythonExceptionInstance.ptr());
};

typedef struct
{
    boost::python::object openCompleteCallback;
    boost::python::object userContext;
} OpenCompleteContext;

extern "C"
void 
OpenCompleteCallback(
    void* openCompleteCallbackContext
    )
{
    if (openCompleteCallbackContext != NULL)
    {
        OpenCompleteContext *openCompleteContext = (OpenCompleteContext *)openCompleteCallbackContext;
        boost::python::object openCompleteCallback = openCompleteContext->openCompleteCallback;
        boost::python::object userContext = openCompleteContext->userContext;

        if (openCompleteCallback.ptr() != NULL)
        {
            ScopedGILAcquire acquire;
            try {
                openCompleteCallback(userContext);
            }
            catch (const boost::python::error_already_set)
            {
                // Catch and ignore exception that is thrown in Python callback.
                // There is nothing we can do about it here.
                PyErr_Print();
            }
        }
    }
};

typedef struct
{
    boost::python::object sendCompleteCallback;
    boost::python::object userContext;
} SendCompleteContext;

extern "C"
void
SendCompleteCallback(
    void* sendCompleteCallbackContext,
    IOTHUB_MESSAGING_RESULT messageResult
)
{
    if (sendCompleteCallbackContext != NULL)
    {
        messageResult = IOTHUB_MESSAGING_OK;
        SendCompleteContext *sendCompleteContext = (SendCompleteContext *)sendCompleteCallbackContext;
        boost::python::object sendCompleteCallback = sendCompleteContext->sendCompleteCallback;
        boost::python::object userContext = sendCompleteContext->userContext;
        if (sendCompleteCallback.ptr() != NULL)
        {
            ScopedGILAcquire acquire;
            try {
                sendCompleteCallback(userContext, messageResult);
            }
            catch (const boost::python::error_already_set)
            {
                // Catch and ignore exception that is thrown in Python callback.
                // There is nothing we can do about it here.
                PyErr_Print();
            }
        }
    }
};

typedef struct
{
    boost::python::object feedbackMessageReceivedCallback;
    boost::python::object userContext;
} FeedbackMessageReceivedContext;

extern "C"
void 
FeedbackMessageReceivedCallback(
    void* feedbackMessageReceivedCallbackContext,
    IOTHUB_SERVICE_FEEDBACK_BATCH* feedbackBatch
    )
{

    if (feedbackMessageReceivedCallbackContext != NULL)
    {
        FeedbackMessageReceivedContext *feedbackMessageReceivedContext = (FeedbackMessageReceivedContext *)feedbackMessageReceivedCallbackContext;
        boost::python::object feedbackMessageReceivedCallback = feedbackMessageReceivedContext->feedbackMessageReceivedCallback;
        boost::python::object userContext = feedbackMessageReceivedContext->userContext;

        (void)feedbackBatch;
        if (feedbackMessageReceivedCallback.ptr() != NULL)
        {
            const char* batchUserId = "";
            const char* batchLockToken = "";
            //std::vector<const char*> feedbackVector;
            boost::python::list pyList;

            if (feedbackBatch != NULL)
            {
                batchUserId = feedbackBatch->userId;
                batchLockToken = feedbackBatch->lockToken;

                if (feedbackBatch->feedbackRecordList != NULL)
                {
                    LIST_ITEM_HANDLE next_record = singlylinkedlist_get_head_item(feedbackBatch->feedbackRecordList);
                    while (next_record != NULL)
                    {
                        boost::python::dict pyFeedBackRecord;
                        IOTHUB_SERVICE_FEEDBACK_RECORD* feedbackRecord = (IOTHUB_SERVICE_FEEDBACK_RECORD*)singlylinkedlist_item_get_value(next_record);
                        next_record = singlylinkedlist_get_next_item(next_record);

                        pyFeedBackRecord["description"] = (const char*)feedbackRecord->description;
                        pyFeedBackRecord["deviceId"] = feedbackRecord->deviceId;
                        pyFeedBackRecord["correlationId"] = feedbackRecord->correlationId;
                        pyFeedBackRecord["generationId"] = feedbackRecord->generationId;
                        pyFeedBackRecord["enqueuedTimeUtc"] = feedbackRecord->enqueuedTimeUtc;
                        pyFeedBackRecord["statusCode"] = (int)feedbackRecord->statusCode;
                        pyFeedBackRecord["originalMessageId"] = feedbackRecord->originalMessageId;
                        pyList.append(pyFeedBackRecord);
                    }
                }
            }

            ScopedGILAcquire acquire;
            try {
                feedbackMessageReceivedCallback(userContext, batchUserId, batchLockToken, pyList);
            }
            catch (const boost::python::error_already_set)
            {
                // Catch and ignore exception that is thrown in Python callback.
                // There is nothing we can do about it here.
                PyErr_Print();
            }
        }
    }
};

class IoTHubMessaging
{
    IOTHUB_SERVICE_CLIENT_AUTH_HANDLE _iothubServiceClientAuthHandle;
    IOTHUB_MESSAGING_CLIENT_HANDLE _iothubMessagingHandle;
    OpenCompleteContext *openCompleteContext;
    SendCompleteContext *sendCompleteContext;
    FeedbackMessageReceivedContext *feedbackMessageContext;

    void CreateContexts()
    {
        if (openCompleteContext == NULL)
            openCompleteContext = new OpenCompleteContext();
        if (sendCompleteContext == NULL)
            sendCompleteContext = new SendCompleteContext();
        if (feedbackMessageContext == NULL)
            feedbackMessageContext = new FeedbackMessageReceivedContext();
    }

    void DestroyContexts()
    {
        if (openCompleteContext != NULL)
        {
            delete(openCompleteContext);
        }
        if (sendCompleteContext != NULL)
        {
            delete(sendCompleteContext);
        }
        if (feedbackMessageContext != NULL)
        {
            delete(feedbackMessageContext);
        }
    }
public:
    IoTHubMessaging(
        std::string connectionString
        ) : _iothubServiceClientAuthHandle(NULL),
			_iothubMessagingHandle(NULL),
			openCompleteContext(NULL),
			sendCompleteContext(NULL),
			feedbackMessageContext(NULL)
    {
        ScopedGILRelease release;
        PlatformCallHandler::Platform_Init();

        _iothubServiceClientAuthHandle = IoTHubServiceClientAuth_CreateFromConnectionString(connectionString.c_str());
        if (_iothubServiceClientAuthHandle == NULL)
        {
            throw IoTHubMessagingError(__func__, IOTHUB_MESSAGING_ERROR);
        }

        _iothubMessagingHandle = IoTHubMessaging_Create(_iothubServiceClientAuthHandle);
        if (_iothubMessagingHandle == NULL)
        {
            throw IoTHubMessagingError(__func__, IOTHUB_MESSAGING_ERROR);
        }
        CreateContexts();
    }

    IoTHubMessaging(
        IoTHubServiceClientAuth iothubAuth
        ) : _iothubServiceClientAuthHandle(NULL),
			_iothubMessagingHandle(NULL),
			openCompleteContext(NULL),
			sendCompleteContext(NULL),
			feedbackMessageContext(NULL)
    {
        ScopedGILRelease release;
        PlatformCallHandler::Platform_Init();

        _iothubServiceClientAuthHandle = iothubAuth.GetHandle();
        if (_iothubServiceClientAuthHandle == NULL)
        {
            throw IoTHubMessagingError(__func__, IOTHUB_MESSAGING_ERROR);
        }

        _iothubMessagingHandle = IoTHubMessaging_Create(_iothubServiceClientAuthHandle);
        if (_iothubMessagingHandle == NULL)
        {
            throw IoTHubMessagingError(__func__, IOTHUB_MESSAGING_ERROR);
        }
        CreateContexts();
    }

    ~IoTHubMessaging()
    {
        PlatformCallHandler::Platform_DeInit();
        Destroy();
    }

    void Destroy()
    {
        ScopedGILRelease release;

        if (_iothubMessagingHandle != NULL)
        {
            IoTHubMessaging_Destroy(_iothubMessagingHandle);
            _iothubMessagingHandle = NULL;
        }

        if (_iothubServiceClientAuthHandle != NULL)
        {
            IoTHubServiceClientAuth_Destroy(_iothubServiceClientAuthHandle);
            _iothubServiceClientAuthHandle = NULL;
        }
        DestroyContexts();
    }

    void Open(
        boost::python::object& openCompleteCallback, 
        boost::python::object& userContextCallback
        )
    {
        IOTHUB_MESSAGING_RESULT result = IOTHUB_MESSAGING_OK;
        if (openCompleteContext != NULL)
        {
            openCompleteContext->openCompleteCallback = openCompleteCallback;
            openCompleteContext->userContext = userContextCallback;
        }

        ScopedGILRelease release;
        result = IoTHubMessaging_Open(_iothubMessagingHandle, OpenCompleteCallback, openCompleteContext);

        if (result != IOTHUB_MESSAGING_OK)
        {
            throw IoTHubMessagingError(__func__, result);
        }
    }

    void Close(
        )
    {
        ScopedGILRelease release;
        IoTHubMessaging_Close(_iothubMessagingHandle);
    }

    void SendAsync(
        std::string deviceId,
        IoTHubMessage &message,
        boost::python::object& sendCompleteCallback, 
        boost::python::object& userContextCallback
        )
    {
        IOTHUB_MESSAGING_RESULT result = IOTHUB_MESSAGING_OK;
        if (sendCompleteContext != NULL)
        {
            sendCompleteContext->sendCompleteCallback = sendCompleteCallback;
            sendCompleteContext->userContext = userContextCallback;
        }

        ScopedGILRelease release;
        result = IoTHubMessaging_SendAsync(_iothubMessagingHandle, deviceId.c_str(), message.Handle(), SendCompleteCallback, sendCompleteContext);

        if (result != IOTHUB_MESSAGING_OK)
        {
            throw IoTHubMessagingError(__func__, result);
        }
    }

    void SendModuleAsync(
        std::string deviceId,
        std::string moduleId,
        IoTHubMessage &message,
        boost::python::object& sendCompleteCallback, 
        boost::python::object& userContextCallback
        )
    {
        IOTHUB_MESSAGING_RESULT result = IOTHUB_MESSAGING_OK;
        if (sendCompleteContext != NULL)
        {
            sendCompleteContext->sendCompleteCallback = sendCompleteCallback;
            sendCompleteContext->userContext = userContextCallback;
        }

        ScopedGILRelease release;
        result = IoTHubMessaging_SendAsyncModule(_iothubMessagingHandle, deviceId.c_str(), moduleId.c_str(), message.Handle(), SendCompleteCallback, sendCompleteContext);

        if (result != IOTHUB_MESSAGING_OK)
        {
            throw IoTHubMessagingError(__func__, result);
        }
    }

    void SetFeedbackMessageCallback(
        boost::python::object& feedbackMessageReceivedCallback, 
        boost::python::object& userContextCallback
        )
    {
        IOTHUB_MESSAGING_RESULT result = IOTHUB_MESSAGING_OK;
        if (feedbackMessageContext)
        {
            feedbackMessageContext->feedbackMessageReceivedCallback = feedbackMessageReceivedCallback;
            feedbackMessageContext->userContext = userContextCallback;
        }

        ScopedGILRelease release;
        result = IoTHubMessaging_SetFeedbackMessageCallback(_iothubMessagingHandle, FeedbackMessageReceivedCallback, feedbackMessageContext);

        if (result != IOTHUB_MESSAGING_OK)
        {
            throw IoTHubMessagingError(__func__, result);
        }
    }
};

//
//  iothub_devicemethod.h
//

static PyObject *iothubDeviceMethodErrorType = NULL;

class IoTHubDeviceMethodError : public IoTHubError
{
public:
    IoTHubDeviceMethodError(
        std::string _func,
        IOTHUB_DEVICE_METHOD_RESULT _result
        ) :
        IoTHubError(
            "IoTHubDeviceMethodError",
            "IoTHubDeviceMethod",
            _func
            )
    {
        result = _result;
    }

    IOTHUB_DEVICE_METHOD_RESULT result;

    virtual std::string decode_error() const
    {
        std::stringstream s;
        s << "IoTHubDeviceMethodResult.";
        switch (result)
        {
        case IOTHUB_DEVICE_METHOD_OK: s << "OK"; break;
        case IOTHUB_DEVICE_METHOD_INVALID_ARG: s << "INVALID_ARG"; break;
        case IOTHUB_DEVICE_METHOD_ERROR: s << "ERROR"; break;
        case IOTHUB_DEVICE_METHOD_HTTPAPI_ERROR: s << "HTTPAPI_ERROR"; break;
        }
        return s.str();
    }

};

void iothubDeviceMethodError(const IoTHubDeviceMethodError& x)
{
    boost::python::object pythonExceptionInstance(x);
    PyErr_SetObject(iothubDeviceMethodErrorType, pythonExceptionInstance.ptr());
};

struct IoTHubDeviceMethodResponse
{
    int status;
    std::string payload;
};

class IoTHubDeviceMethod
{
    IOTHUB_SERVICE_CLIENT_AUTH_HANDLE _iothubServiceClientAuthHandle; 
    IOTHUB_SERVICE_CLIENT_DEVICE_METHOD_HANDLE _iothubDeviceMethodHandle;
public:
    IoTHubDeviceMethod(
        std::string connectionString
        ) : _iothubServiceClientAuthHandle(NULL),
			_iothubDeviceMethodHandle(NULL)
    {
        ScopedGILRelease release;
        PlatformCallHandler::Platform_Init();

        _iothubServiceClientAuthHandle = IoTHubServiceClientAuth_CreateFromConnectionString(connectionString.c_str());
        if (_iothubServiceClientAuthHandle == NULL)
        {
            throw IoTHubDeviceMethodError(__func__, IOTHUB_DEVICE_METHOD_ERROR);
        }

        _iothubDeviceMethodHandle = IoTHubDeviceMethod_Create(_iothubServiceClientAuthHandle);
        if (_iothubDeviceMethodHandle == NULL)
        {
            throw IoTHubDeviceMethodError(__func__, IOTHUB_DEVICE_METHOD_ERROR);
        }
    }

    IoTHubDeviceMethod(
        IoTHubServiceClientAuth iothubAuth
        ) : _iothubServiceClientAuthHandle(NULL),
			_iothubDeviceMethodHandle(NULL)
    {
        ScopedGILRelease release;
        PlatformCallHandler::Platform_Init();

        _iothubServiceClientAuthHandle = iothubAuth.GetHandle();
        if (_iothubServiceClientAuthHandle == NULL)
        {
            throw IoTHubDeviceMethodError(__func__, IOTHUB_DEVICE_METHOD_ERROR);
        }

        _iothubDeviceMethodHandle = IoTHubDeviceMethod_Create(_iothubServiceClientAuthHandle);
        if (_iothubDeviceMethodHandle == NULL)
        {
            throw IoTHubDeviceMethodError(__func__, IOTHUB_DEVICE_METHOD_ERROR);
        }
    }

    ~IoTHubDeviceMethod()
    {
        PlatformCallHandler::Platform_DeInit();
        Destroy();
    }

    void Destroy()
    {
        ScopedGILRelease release;

        if (_iothubDeviceMethodHandle != NULL)
        {
            IoTHubDeviceMethod_Destroy(_iothubDeviceMethodHandle);
            _iothubDeviceMethodHandle = NULL;
        }

        if (_iothubServiceClientAuthHandle != NULL)
        {
            IoTHubServiceClientAuth_Destroy(_iothubServiceClientAuthHandle);
            _iothubServiceClientAuthHandle = NULL;
        }
    }

    IoTHubDeviceMethodResponse Invoke(
        std::string deviceId,
        std::string methodName,
        std::string methodPayload,
        unsigned int timeout
    )
    {
        IOTHUB_DEVICE_METHOD_RESULT result = IOTHUB_DEVICE_METHOD_OK;
        IoTHubDeviceMethodResponse response = IoTHubDeviceMethodResponse();

        ScopedGILRelease release;
        int responseStatus;
        unsigned char* responsePayload;
        size_t responsePayloadSize;
        result = IoTHubDeviceMethod_Invoke(_iothubDeviceMethodHandle, deviceId.c_str(), methodName.c_str(), methodPayload.c_str(), timeout, &responseStatus, &responsePayload, &responsePayloadSize);

        if (result == IOTHUB_DEVICE_METHOD_OK)
        {
            response.status = responseStatus;
            std::string payload(&responsePayload[0], &responsePayload[0] + responsePayloadSize);
            response.payload = payload;
        }

        if (result != IOTHUB_DEVICE_METHOD_OK)
        {
            throw IoTHubDeviceMethodError(__func__, result);
        }
        return response;
    }

    IoTHubDeviceMethodResponse InvokeModule(
        std::string deviceId,
        std::string moduleId,
        std::string methodName,
        std::string methodPayload,
        unsigned int timeout
    )
    {
        IOTHUB_DEVICE_METHOD_RESULT result = IOTHUB_DEVICE_METHOD_OK;
        IoTHubDeviceMethodResponse response = IoTHubDeviceMethodResponse();

        ScopedGILRelease release;
        int responseStatus;
        unsigned char* responsePayload;
        size_t responsePayloadSize;
       
        result = IoTHubDeviceMethod_InvokeModule(_iothubDeviceMethodHandle, deviceId.c_str(), moduleId.c_str(), methodName.c_str(), methodPayload.c_str(), timeout, &responseStatus, &responsePayload, &responsePayloadSize);

        if (result == IOTHUB_DEVICE_METHOD_OK)
        {
            response.status = responseStatus;
            std::string payload(&responsePayload[0], &responsePayload[0] + responsePayloadSize);
            response.payload = payload;
        }

        if (result != IOTHUB_DEVICE_METHOD_OK)
        {
            throw IoTHubDeviceMethodError(__func__, result);
        }
        return response;
    }

};

//
//  iothub_devicetwin.h
//

static PyObject *iothubDeviceTwinErrorType = NULL;

class IoTHubDeviceTwinError : public IoTHubError
{
public:
    IoTHubDeviceTwinError(
        std::string _func,
        IOTHUB_DEVICE_TWIN_RESULT _result
        ) :
        IoTHubError(
            "IoTHubDeviceTwinError",
            "IoTHubTwin",
            _func
            )
    {
        result = _result;
    }

    IOTHUB_DEVICE_TWIN_RESULT result;

    virtual std::string decode_error() const
    {
        std::stringstream s;
        s << "IoTHubDeviceTwinResult.";
        switch (result)
        {
        case IOTHUB_DEVICE_TWIN_OK: s << "OK"; break;
        case IOTHUB_DEVICE_TWIN_INVALID_ARG: s << "INVALID_ARG"; break;
        case IOTHUB_DEVICE_TWIN_ERROR: s << "ERROR"; break;
        case IOTHUB_DEVICE_TWIN_HTTPAPI_ERROR: s << "HTTPAPI_ERROR"; break;
        }
        return s.str();
    }

};

void iothubDeviceTwinError(const IoTHubDeviceTwinError& x)
{
    boost::python::object pythonExceptionInstance(x);
    PyErr_SetObject(iothubDeviceTwinErrorType, pythonExceptionInstance.ptr());
};

class IoTHubDeviceTwin
{
    IOTHUB_SERVICE_CLIENT_AUTH_HANDLE _iothubServiceClientAuthHandle;
    IOTHUB_SERVICE_CLIENT_DEVICE_TWIN_HANDLE _iothubDeviceTwinHandle;
public:
    IoTHubDeviceTwin(
        std::string connectionString
        ) : _iothubServiceClientAuthHandle(NULL),
			_iothubDeviceTwinHandle(NULL)
    {
        ScopedGILRelease release;
        PlatformCallHandler::Platform_Init();

        _iothubServiceClientAuthHandle = IoTHubServiceClientAuth_CreateFromConnectionString(connectionString.c_str());
        if (_iothubServiceClientAuthHandle == NULL)
        {
            throw IoTHubDeviceTwinError(__func__, IOTHUB_DEVICE_TWIN_ERROR);
        }

        _iothubDeviceTwinHandle = IoTHubDeviceTwin_Create(_iothubServiceClientAuthHandle);
        if (_iothubDeviceTwinHandle == NULL)
        {
            throw IoTHubDeviceTwinError(__func__, IOTHUB_DEVICE_TWIN_ERROR);
        }
    }

    IoTHubDeviceTwin(
        IoTHubServiceClientAuth iothubAuth
        ) : _iothubServiceClientAuthHandle(NULL),
			_iothubDeviceTwinHandle(NULL)
    {
        ScopedGILRelease release;
        PlatformCallHandler::Platform_Init();

        _iothubServiceClientAuthHandle = iothubAuth.GetHandle();
        if (_iothubServiceClientAuthHandle == NULL)
        {
            throw IoTHubDeviceTwinError(__func__, IOTHUB_DEVICE_TWIN_ERROR);
        }

        _iothubDeviceTwinHandle = IoTHubDeviceTwin_Create(_iothubServiceClientAuthHandle);
        if (_iothubDeviceTwinHandle == NULL)
        {
            throw IoTHubDeviceTwinError(__func__, IOTHUB_DEVICE_TWIN_ERROR);
        }
    }

    ~IoTHubDeviceTwin()
    {
        PlatformCallHandler::Platform_DeInit();
        Destroy();
    }

    void Destroy()
    {
        ScopedGILRelease release;

        if (_iothubDeviceTwinHandle != NULL)
        {
            IoTHubDeviceTwin_Destroy(_iothubDeviceTwinHandle);
            _iothubDeviceTwinHandle = NULL;
        }

        if (_iothubServiceClientAuthHandle != NULL)
        {
            IoTHubServiceClientAuth_Destroy(_iothubServiceClientAuthHandle);
            _iothubServiceClientAuthHandle = NULL;
        }
    }

    std::string GetTwin(
        std::string deviceId
    )
    {
        std::string result;
        char* twinInfo = NULL;

        ScopedGILRelease release;
        twinInfo = IoTHubDeviceTwin_GetTwin(_iothubDeviceTwinHandle, deviceId.c_str());

        if (twinInfo != NULL)
        {
            result.append(twinInfo);
        }

        if (twinInfo == NULL)
        {
            throw IoTHubDeviceTwinError(__func__, IOTHUB_DEVICE_TWIN_ERROR);
        }
        return result;
    }

    std::string UpdateTwin(
        std::string deviceId,
        std::string deviceTwinJson
    )
    {
        std::string result;
        char* twinInfo = NULL;

        ScopedGILRelease release;
        twinInfo = IoTHubDeviceTwin_UpdateTwin(_iothubDeviceTwinHandle, deviceId.c_str(), deviceTwinJson.c_str());

        if (twinInfo != NULL)
        {
            result.append(twinInfo);
        }

        if (twinInfo == NULL)
        {
            throw IoTHubDeviceTwinError(__func__, IOTHUB_DEVICE_TWIN_ERROR);
        }
        return result;
    }

    std::string GetModuleTwin(
        std::string deviceId,
        std::string moduleId
    )
    {
        std::string result;
        char* moduleTwinInfo = NULL;

        ScopedGILRelease release;
        moduleTwinInfo = IoTHubDeviceTwin_GetModuleTwin(_iothubDeviceTwinHandle, deviceId.c_str(), moduleId.c_str());

        if (moduleTwinInfo != NULL)
        {
            result.append(moduleTwinInfo);
        }

        if (moduleTwinInfo == NULL)
        {
            throw IoTHubDeviceTwinError(__func__, IOTHUB_DEVICE_TWIN_ERROR);
        }
        return result;
    }

    std::string UpdateModuleTwin(
        std::string deviceId,
        std::string moduleId,
        std::string moduleTwinJson
    )
    {
        std::string result;
        char* moduleTwinInfo = NULL;

        ScopedGILRelease release;
        moduleTwinInfo = IoTHubDeviceTwin_UpdateModuleTwin(_iothubDeviceTwinHandle, deviceId.c_str(), moduleId.c_str(), moduleTwinJson.c_str());

        if (moduleTwinInfo != NULL)
        {
            result.append(moduleTwinInfo);
        }

        if (moduleTwinInfo == NULL)
        {
            throw IoTHubDeviceTwinError(__func__, IOTHUB_DEVICE_TWIN_ERROR);
        }
        return result;
    }
};

using namespace boost::python;

static const char* iothub_service_client_docstring =
"iothub_service_client is a Python module for communicating with the Azure IoT Hub";

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
    scope().attr("__doc__") = iothub_service_client_docstring;
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

    class_<IoTHubServiceClientAuthError>IoTHubServiceClientAuthErrorClass("IoTHubServiceClientAuthErrorArg", init<std::string>());
    IoTHubServiceClientAuthErrorClass.def_readonly("func", &IoTHubServiceClientAuthError::func);
    IoTHubServiceClientAuthErrorClass.def("__str__", &IoTHubServiceClientAuthError::str);
    IoTHubServiceClientAuthErrorClass.def("__repr__", &IoTHubServiceClientAuthError::repr);

    class_<IoTHubRegistryManagerError>IoTHubRegistryManagerErrorClass("IoTHubRegistryManagerErrorArg", init<std::string, IOTHUB_REGISTRYMANAGER_RESULT>());
    IoTHubRegistryManagerErrorClass.def_readonly("result", &IoTHubRegistryManagerError::result);
    IoTHubRegistryManagerErrorClass.def_readonly("func", &IoTHubRegistryManagerError::func);
    IoTHubRegistryManagerErrorClass.def("__str__", &IoTHubRegistryManagerError::str);
    IoTHubRegistryManagerErrorClass.def("__repr__", &IoTHubRegistryManagerError::repr);

    class_<IoTHubMessagingError>IoTHubMessagingErrorClass("IoTHubMessagingErrorArg", init<std::string, IOTHUB_MESSAGING_RESULT>());
    IoTHubMessagingErrorClass.def_readonly("result", &IoTHubMessagingError::result);
    IoTHubMessagingErrorClass.def_readonly("func", &IoTHubMessagingError::func);
    IoTHubMessagingErrorClass.def("__str__", &IoTHubMessagingError::str);
    IoTHubMessagingErrorClass.def("__repr__", &IoTHubMessagingError::repr);

    class_<IoTHubDeviceMethodError>IoTHubDeviceMethodErrorClass("IoTHubDeviceMethodErrorArg", init<std::string, IOTHUB_DEVICE_METHOD_RESULT>());
    IoTHubDeviceMethodErrorClass.def_readonly("result", &IoTHubDeviceMethodError::result);
    IoTHubDeviceMethodErrorClass.def_readonly("func", &IoTHubDeviceMethodError::func);
    IoTHubDeviceMethodErrorClass.def("__str__", &IoTHubDeviceMethodError::str);
    IoTHubDeviceMethodErrorClass.def("__repr__", &IoTHubDeviceMethodError::repr);

    class_<IoTHubDeviceTwinError>IoTHubDeviceTwinErrorClass("IoTHubDeviceTwinErrorArg", init<std::string, IOTHUB_DEVICE_TWIN_RESULT>());
    IoTHubDeviceTwinErrorClass.def_readonly("result", &IoTHubDeviceTwinError::result);
    IoTHubDeviceTwinErrorClass.def_readonly("func", &IoTHubDeviceTwinError::func);
    IoTHubDeviceTwinErrorClass.def("__str__", &IoTHubDeviceTwinError::str);
    IoTHubDeviceTwinErrorClass.def("__repr__", &IoTHubDeviceTwinError::repr);

    register_exception_translator<IoTHubMapError>(iotHubMapError);
    register_exception_translator<IoTHubRegistryManagerError>(iothubRegistryManagerError);
    register_exception_translator<IoTHubMessagingError>(iothubMessagingError);
    register_exception_translator<IoTHubDeviceMethodError>(iothubDeviceMethodError);
    register_exception_translator<IoTHubDeviceTwinError>(iothubDeviceTwinError);

    // iothub errors derived from BaseException --> IoTHubError --> IoTHubXXXError
    iotHubErrorType = createExceptionClass("IoTHubError");
    iotHubMapErrorType = createExceptionClass("IoTHubMapError", iotHubErrorType);
    iothubMessageErrorType = createExceptionClass("IoTHubMessageError", iotHubErrorType);
    iothubServiceClientAuthErrorType = createExceptionClass("IoTHubServiceClientAuthError", iotHubErrorType);
    iothubRegistryManagerErrorType = createExceptionClass("IoTHubRegistryManagerError", iotHubErrorType);
    iothubMessagingErrorType = createExceptionClass("IoTHubMessagingError", iotHubErrorType);
    iothubDeviceMethodErrorType = createExceptionClass("IoTHubDeviceMethodError", iotHubErrorType);
    iothubDeviceTwinErrorType = createExceptionClass("IoTHubDeviceTwinError", iotHubErrorType);

    // iothub service client return codes
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

    enum_<IOTHUB_REGISTRYMANAGER_RESULT>("IoTHubRegistryManagerResult")
        .value("OK", IOTHUB_REGISTRYMANAGER_OK)
        .value("INVALID_ARG", IOTHUB_REGISTRYMANAGER_INVALID_ARG)
        .value("ERROR", IOTHUB_REGISTRYMANAGER_ERROR)
        .value("JSON_ERROR", IOTHUB_REGISTRYMANAGER_JSON_ERROR)
        .value("HTTPAPI_ERROR", IOTHUB_REGISTRYMANAGER_HTTPAPI_ERROR)
        .value("HTTP_STATUS_ERROR", IOTHUB_REGISTRYMANAGER_HTTP_STATUS_ERROR)
        .value("DEVICE_EXIST", IOTHUB_REGISTRYMANAGER_DEVICE_EXIST)
        .value("DEVICE_NOT_EXIST", IOTHUB_REGISTRYMANAGER_DEVICE_NOT_EXIST)
        .value("CALLBACK_NOT_SET", IOTHUB_REGISTRYMANAGER_CALLBACK_NOT_SET)
        ;

    enum_<IOTHUB_REGISTRYMANAGER_AUTH_METHOD>("IoTHubRegistryManagerAuthMethod")
        .value("SHARED_PRIVATE_KEY", IOTHUB_REGISTRYMANAGER_AUTH_SPK)
        .value("X509_THUMBPRINT", IOTHUB_REGISTRYMANAGER_AUTH_X509_THUMBPRINT)
        .value("X509_CERTIFICATE_AUTHORITY", IOTHUB_REGISTRYMANAGER_AUTH_X509_CERTIFICATE_AUTHORITY)
        ;

    enum_<IOTHUB_MESSAGING_RESULT>("IoTHubMessagingResult")
        .value("OK", IOTHUB_MESSAGING_OK)
        .value("INVALID_ARG", IOTHUB_MESSAGING_INVALID_ARG)
        .value("ERROR", IOTHUB_MESSAGING_ERROR)
        .value("INVALID_JSON", IOTHUB_MESSAGING_INVALID_JSON)
        .value("DEVICE_EXIST", IOTHUB_MESSAGING_DEVICE_EXIST)
        .value("CALLBACK_NOT_SET", IOTHUB_MESSAGING_CALLBACK_NOT_SET)
        ;

    enum_<IOTHUB_DEVICE_CONNECTION_STATE>("IoTHubDeviceConnectionState")
        .value("CONNECTED", IOTHUB_DEVICE_CONNECTION_STATE_CONNECTED)
        .value("DISCONNECTED", IOTHUB_DEVICE_CONNECTION_STATE_DISCONNECTED)
        ;

    enum_<IOTHUB_DEVICE_STATUS>("IoTHubDeviceStatus")
        .value("ENABLED", IOTHUB_DEVICE_STATUS_ENABLED)
        .value("DISABLED", IOTHUB_DEVICE_STATUS_DISABLED)
        ;

    enum_<IOTHUB_FEEDBACK_STATUS_CODE>("IoTHubFeedbackStatusCode")
        .value("SUCCESS", IOTHUB_FEEDBACK_STATUS_CODE_SUCCESS)
        .value("EXPIRED", IOTHUB_FEEDBACK_STATUS_CODE_EXPIRED)
        .value("DELIVER_COUNT_EXCEEDED", IOTHUB_FEEDBACK_STATUS_CODE_DELIVER_COUNT_EXCEEDED)
        .value("REJECTED", IOTHUB_FEEDBACK_STATUS_CODE_REJECTED)
        .value("UNKNOWN", IOTHUB_FEEDBACK_STATUS_CODE_UNKNOWN)
        ;

    enum_<IOTHUB_DEVICE_METHOD_RESULT>("IoTHubDeviceMethodResult")
        .value("OK", IOTHUB_DEVICE_METHOD_OK)
        .value("INVALID_ARG", IOTHUB_DEVICE_METHOD_INVALID_ARG)
        .value("ERROR", IOTHUB_DEVICE_METHOD_ERROR)
        .value("HTTPAPI_ERROR", IOTHUB_DEVICE_METHOD_HTTPAPI_ERROR)
        ;

    enum_<IOTHUB_DEVICE_TWIN_RESULT>("IoTHubDeviceTwinResult")
        .value("OK", IOTHUB_DEVICE_TWIN_OK)
        .value("INVALID_ARG", IOTHUB_DEVICE_TWIN_INVALID_ARG)
        .value("ERROR", IOTHUB_DEVICE_TWIN_ERROR)
        .value("HTTPAPI_ERROR", IOTHUB_DEVICE_TWIN_HTTPAPI_ERROR)
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
        ;

    class_<IoTHubMessage>("IoTHubMessage", no_init)
        .def(init<PyObject *>())
        .def(init<std::string>())
        .def("get_bytearray", &IoTHubMessage::GetBytearray)
        .def("get_string", &IoTHubMessage::GetString)
        .def("get_content_type", &IoTHubMessage::GetContentType)
        .def("properties", &IoTHubMessage::Properties, return_internal_reference<1>())
        .add_property("message_id", &IoTHubMessage::GetMessageId, &IoTHubMessage::SetMessageId)
        .add_property("correlation_id", &IoTHubMessage::GetCorrelationId, &IoTHubMessage::SetCorrelationId)
        ;

    class_<IoTHubDeviceCapabilities>("IoTHubDeviceCapabilities", no_init)
        .def(init<>())
        .add_property("iot_edge", &IoTHubDeviceCapabilities::GetIotEdge, &IoTHubDeviceCapabilities::SetIotEdge)
        ;

    class_<IOTHUB_DEVICE_EX>("IoTHubDevice", no_init)
        .add_property("deviceId", &IOTHUB_DEVICE_EX::deviceId)
        .add_property("primaryKey", &IOTHUB_DEVICE_EX::primaryKey)
        .add_property("secondaryKey", &IOTHUB_DEVICE_EX::secondaryKey)
        .add_property("generationId", &IOTHUB_DEVICE_EX::generationId)
        .add_property("eTag", &IOTHUB_DEVICE_EX::eTag)
        .add_property("connectionState", &IOTHUB_DEVICE_EX::connectionState)
        .add_property("connectionStateUpdatedTime", &IOTHUB_DEVICE_EX::connectionStateUpdatedTime)
        .add_property("status", &IOTHUB_DEVICE_EX::status)
        .add_property("statusReason", &IOTHUB_DEVICE_EX::statusReason)
        .add_property("statusUpdatedTime", &IOTHUB_DEVICE_EX::statusUpdatedTime)
        .add_property("lastActivityTime", &IOTHUB_DEVICE_EX::lastActivityTime)
        .add_property("cloudToDeviceMessageCount", &IOTHUB_DEVICE_EX::cloudToDeviceMessageCount)
        .add_property("isManaged", &IOTHUB_DEVICE_EX::isManaged)
        .add_property("configuration", &IOTHUB_DEVICE_EX::configuration)
        .add_property("deviceProperties", &IOTHUB_DEVICE_EX::deviceProperties)
        .add_property("serviceProperties", &IOTHUB_DEVICE_EX::serviceProperties)
        .add_property("authMethod", &IOTHUB_DEVICE_EX::authMethod)
        ;

    class_<IOTHUB_MODULE>("IoTHubModule", no_init)
        .add_property("moduleId", &IOTHUB_MODULE::moduleId)
        .add_property("deviceId", &IOTHUB_MODULE::deviceId)
        .add_property("primaryKey", &IOTHUB_MODULE::primaryKey)
        .add_property("secondaryKey", &IOTHUB_MODULE::secondaryKey)
        .add_property("generationId", &IOTHUB_MODULE::generationId)
        .add_property("eTag", &IOTHUB_MODULE::eTag)
        .add_property("connectionState", &IOTHUB_MODULE::connectionState)
        .add_property("connectionStateUpdatedTime", &IOTHUB_MODULE::connectionStateUpdatedTime)
        .add_property("lastActivityTime", &IOTHUB_MODULE::lastActivityTime)
        .add_property("cloudToDeviceMessageCount", &IOTHUB_MODULE::cloudToDeviceMessageCount)
        .add_property("authMethod", &IOTHUB_MODULE::authMethod)
        ;

    class_<IOTHUB_REGISTRY_STATISTICS>("IoTHubRegistryStatistics", no_init)
        .add_property("totalDeviceCount", &IOTHUB_REGISTRY_STATISTICS::totalDeviceCount)
        .add_property("enabledDeviceCount", &IOTHUB_REGISTRY_STATISTICS::enabledDeviceCount)
        .add_property("disabledDeviceCount", &IOTHUB_REGISTRY_STATISTICS::disabledDeviceCount)
        ;

    class_<IOTHUB_SERVICE_FEEDBACK_BATCH>("IoTHubServiceFeedbackBatch", no_init)
        .add_property("userId", &IOTHUB_SERVICE_FEEDBACK_BATCH::userId)
        .add_property("lockToken", &IOTHUB_SERVICE_FEEDBACK_BATCH::lockToken)
        .add_property("feedbackRecordList", &IOTHUB_SERVICE_FEEDBACK_BATCH::feedbackRecordList)
        ;

    class_<IOTHUB_SERVICE_FEEDBACK_RECORD>("IoTHubServiceFeedbackRecord", no_init)
        .add_property("description", &IOTHUB_SERVICE_FEEDBACK_RECORD::description)
        .add_property("deviceId", &IOTHUB_SERVICE_FEEDBACK_RECORD::deviceId)
        .add_property("correlationId", &IOTHUB_SERVICE_FEEDBACK_RECORD::correlationId)
        .add_property("generationId", &IOTHUB_SERVICE_FEEDBACK_RECORD::generationId)
        .add_property("enqueuedTimeUtc", &IOTHUB_SERVICE_FEEDBACK_RECORD::enqueuedTimeUtc)
        .add_property("statusCode", &IOTHUB_SERVICE_FEEDBACK_RECORD::statusCode)
        .add_property("originalMessageId", &IOTHUB_SERVICE_FEEDBACK_RECORD::originalMessageId)
        ;

    class_<IoTHubDeviceMethodResponse>("IoTHubDeviceMethodResponse")
        .add_property("status", &IoTHubDeviceMethodResponse::status)
        .add_property("payload", &IoTHubDeviceMethodResponse::payload)
        ;

    class_<IoTHubServiceClientAuth, boost::noncopyable>("IoTHubServiceClientAuth", no_init)
        .def(init<std::string>())
        ;

    class_<IoTHubRegistryManager, boost::noncopyable>("IoTHubRegistryManager", no_init)
        .def(init<std::string>())
        .def(init<IoTHubServiceClientAuth>())
        .def("create_device", &IoTHubRegistryManager::CreateDevice, IoTHubRegistryManager_overloads())
        .def("get_device", &IoTHubRegistryManager::GetDevice)
        .def("update_device", &IoTHubRegistryManager::UpdateDevice, IoTHubRegistryManager_overloads2())
        .def("delete_device", &IoTHubRegistryManager::DeleteDevice)
        .def("get_device_list", &IoTHubRegistryManager::GetDeviceList)
        .def("get_statistics", &IoTHubRegistryManager::GetStatistics)
        .def("create_module", &IoTHubRegistryManager::CreateModule)
        .def("update_module", &IoTHubRegistryManager::UpdateModule)
        .def("get_module", &IoTHubRegistryManager::GetModule)
        .def("get_module_list", &IoTHubRegistryManager::GetModuleList)
        .def("delete_module", &IoTHubRegistryManager::DeleteModule)
        ;

    class_<IoTHubMessaging, boost::noncopyable>("IoTHubMessaging", no_init)
        .def(init<std::string>())
        .def(init<IoTHubServiceClientAuth>())
        .def("open", &IoTHubMessaging::Open)
        .def("close", &IoTHubMessaging::Close)
        .def("send_async", &IoTHubMessaging::SendAsync)
        .def("send_async", &IoTHubMessaging::SendModuleAsync)
        .def("set_feedback_message_callback", &IoTHubMessaging::SetFeedbackMessageCallback)
        ;

    class_<IoTHubDeviceMethod, boost::noncopyable>("IoTHubDeviceMethod", no_init)
        .def(init<std::string>())
        .def(init<IoTHubServiceClientAuth>())
        .def("invoke", &IoTHubDeviceMethod::Invoke)
        .def("invoke", &IoTHubDeviceMethod::InvokeModule)
        ;

    class_<IoTHubDeviceTwin, boost::noncopyable>("IoTHubDeviceTwin", no_init)
        .def(init<std::string>())
        .def(init<IoTHubServiceClientAuth>())
        .def("get_twin", &IoTHubDeviceTwin::GetTwin)
        .def("get_twin", &IoTHubDeviceTwin::GetModuleTwin)
        .def("update_twin", &IoTHubDeviceTwin::UpdateTwin)
        .def("update_twin", &IoTHubDeviceTwin::UpdateModuleTwin)
        ;
};
