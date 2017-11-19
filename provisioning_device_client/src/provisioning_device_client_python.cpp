
// Copyright(c) Microsoft.All rights reserved.
// Licensed under the MIT license.See LICENSE file in the project root for full license information.

#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable:4459 4100 4121 4244) /* This is because boost python has a self variable that hides a global */
#endif

#include <boost/python.hpp>
//#include <boost/python/suite/indexing/vector_indexing_suite.hpp>

#ifdef _MSC_VER
#pragma warning(pop)
#endif

#include <string>

#include "azure_c_shared_utility/platform.h"
#include "azure_prov_client/prov_device_client.h"
#include "azure_prov_client/prov_transport.h"
#include "azure_prov_client/prov_client_const.h"
#include "azure_prov_client/prov_security_factory.h"
#if USE_HTTP
#include "azure_prov_client/prov_transport_http_client.h"
#endif
#if USE_AMQP
#include "azure_prov_client/prov_transport_amqp_client.h"
#ifdef USE_WEBSOCKETS
#include "azure_prov_client/prov_transport_amqp_ws_client.h"
#endif
#endif
#if USE_MQTT
#include "azure_prov_client/prov_transport_mqtt_client.h"
#ifdef USE_WEBSOCKETS
#include "azure_prov_client/prov_transport_mqtt_ws_client.h"
#endif
#endif

#ifndef IMPORT_NAME
#define IMPORT_NAME provisioning_device_client
#endif

#define PYTHON_PROVISIONING_DEVICE_CLIENT_SDK_VERSION "0"
#define VERSION_STRING PROV_DEVICE_CLIENT_VERSION "." PYTHON_PROVISIONING_DEVICE_CLIENT_SDK_VERSION

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

enum PROV_SECURE_DEVICE_TYPE
{
    UNKNOWN,
    TPM,
    X509
};

//
// iothubtransportxxxx.h
//

#ifdef USE_WEBSOCKETS
enum PROV_TRANSPORT_PROVIDER
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
enum PROV_TRANSPORT_PROVIDER
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

PyObject* provisioningErrorType = NULL;

class ProvisioningError : public std::exception
{
public:
    std::string exc;
    std::string cls;
    std::string func;

    ProvisioningError(
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

PyObject *provisioningDeviceClientErrorType = NULL;

class ProvisioningDeviceClientError : public ProvisioningError
{
public:
    ProvisioningDeviceClientError(
        std::string _func,
        PROV_DEVICE_RESULT _result
    ) :
        ProvisioningError(
            "ProvisioningDeviceClientError",
            "ProvisioningDeviceClient",
            _func
        )
    {
        result = _result;
    }

    PROV_DEVICE_RESULT result;

    virtual std::string decode_error() const
    {
        std::stringstream s;
        s << "ProvisioningDeviceClientResult.";
        switch (result)
        {
        case PROV_DEVICE_RESULT_OK: s << "OK"; break;
        case PROV_DEVICE_RESULT_INVALID_ARG: s << "INVALID_ARG"; break;
        case PROV_DEVICE_RESULT_SUCCESS: s << "SUCCESS"; break;
        case PROV_DEVICE_RESULT_MEMORY: s << "MEMORY_ERROR"; break;
        case PROV_DEVICE_RESULT_PARSING: s << "PARSING_ERROR"; break;
        case PROV_DEVICE_RESULT_TRANSPORT: s << "TRANSPORT_ERROR"; break;
        case PROV_DEVICE_RESULT_INVALID_STATE: s << "INVALID_STATE"; break;
        case PROV_DEVICE_RESULT_DEV_AUTH_ERROR: s << "DEVICE_AUTHENTICATION_ERROR"; break;
        case PROV_DEVICE_RESULT_TIMEOUT: s << "TIMEOUT"; break;
        case PROV_DEVICE_RESULT_KEY_ERROR: s << "KEY_ERROR"; break;
        case PROV_DEVICE_RESULT_ERROR: s << "ERROR"; break;
        }
        return s.str();
    }
};

void provisioningDeviceClientError(const ProvisioningDeviceClientError& x)
{
    boost::python::object pythonExceptionInstance(x);
    PyErr_SetObject(provisioningDeviceClientErrorType, pythonExceptionInstance.ptr());
};

typedef struct
{
    boost::python::object register_callback;
    boost::python::object userContext;
} RegisterDeviceContext;

typedef struct
{
    boost::python::object register_status_callback;
    boost::python::object status_user_context;
} RegisterDeviceStatusContext;

extern "C"
void
RegisterDeviceCallback(
    PROV_DEVICE_RESULT register_result,
    const char* iothub_uri, 
    const char* device_id,
    void* user_context
)
{
    RegisterDeviceContext *registerDeviceContext = (RegisterDeviceContext *)user_context;
    boost::python::object register_callback = registerDeviceContext->register_callback;
    boost::python::object userContext = registerDeviceContext->userContext;
    {
        ScopedGILAcquire acquire;
        try 
        {
            register_callback(register_result, iothub_uri, device_id, userContext);
        }
        catch (const boost::python::error_already_set)
        {
            // Catch and ignore exception that is thrown in Python callback.
            // There is nothing we can do about it here.
            PyErr_Print();
        }
    }
}

extern "C"
void
RegisterDeviceStatusCallback(
    PROV_DEVICE_REG_STATUS reg_status,
    void* user_context
)
{
    RegisterDeviceStatusContext *registerDeviceStatusContext = (RegisterDeviceStatusContext *)user_context;
    boost::python::object register_status_callback = registerDeviceStatusContext->register_status_callback;
    boost::python::object status_user_context = registerDeviceStatusContext->status_user_context;
    {
        ScopedGILAcquire acquire;
        try 
        {
            register_status_callback(reg_status, status_user_context);
        }
        catch (const boost::python::error_already_set)
        {
            // Catch and ignore exception that is thrown in Python callback.
            // There is nothing we can do about it here.
            PyErr_Print();
        }
    }
}

class HttpProxyOptions
{
public:
    HttpProxyOptions(
        std::string _host_address,
        int _port,
        std::string _username,
        std::string _password
    ) :
        host_address(_host_address),
        port(_port),
        username(_username),
        password(_password)
    {
    }
    std::string host_address;
    int port;
    std::string username;
    std::string password;
};

class ProvisioningDeviceClient
{
    static PROV_DEVICE_TRANSPORT_PROVIDER_FUNCTION
        GetProtocol(PROV_TRANSPORT_PROVIDER _protocol)
    {
        PROV_DEVICE_TRANSPORT_PROVIDER_FUNCTION protocol = NULL;
        switch (_protocol)
        {
#ifdef USE_HTTP
        case HTTP:
            protocol = Prov_Device_HTTP_Protocol;
            break;
#endif
#ifdef USE_AMQP
        case AMQP:
            protocol = Prov_Device_AMQP_Protocol;
            break;
#endif
#ifdef USE_MQTT
        case MQTT:
            protocol = Prov_Device_MQTT_Protocol;
            break;
#endif
#ifdef USE_WEBSOCKETS
#ifdef USE_AMQP
        case AMQP_WS:
            protocol = Prov_Device_AMQP_WS_Protocol;
            break;
#endif
#ifdef USE_MQTT
        case MQTT_WS:
            protocol = Prov_Device_MQTT_WS_Protocol;
            break;
#endif
#endif
        default:
            PyErr_SetString(PyExc_TypeError, "Provisioning Transport Provider set to unknown protocol");
            boost::python::throw_error_already_set();
            break;
        }
        return protocol;
    }

    static SECURE_DEVICE_TYPE
        GetSecurityDeviceType(PROV_SECURE_DEVICE_TYPE _prov_security_device_type)
    {
        SECURE_DEVICE_TYPE security_device_type = SECURE_DEVICE_TYPE_UNKNOWN;
        switch (_prov_security_device_type)
        {
        case UNKNOWN:
            security_device_type = SECURE_DEVICE_TYPE_UNKNOWN;
            break;
        case TPM:
            security_device_type = SECURE_DEVICE_TYPE_TPM;
            break;
        case X509:
            security_device_type = SECURE_DEVICE_TYPE_X509;
            break;
        default:
            PyErr_SetString(PyExc_TypeError, "Provisioning Security Device Type set to unknown type");
            boost::python::throw_error_already_set();
            break;
        }
        return security_device_type;
    }

    PROV_DEVICE_HANDLE _prov_device_handle;
public:
    PROV_TRANSPORT_PROVIDER _protocol;

    ProvisioningDeviceClient(
        std::string uri,
        std::string id_scope,
        PROV_SECURE_DEVICE_TYPE security_device_type,
        PROV_TRANSPORT_PROVIDER protocol
    ) :
        _prov_device_handle(NULL),
        _protocol(protocol)
    {
        ScopedGILRelease release;
        PlatformCallHandler::Platform_Init();

        if (prov_dev_security_init(GetSecurityDeviceType(security_device_type)) == 0)
        {
            _prov_device_handle = Prov_Device_Create(uri.c_str(), id_scope.c_str(), GetProtocol(protocol));
            if (_prov_device_handle == NULL)
            {
                throw ProvisioningDeviceClientError(__func__, PROV_DEVICE_RESULT_ERROR);
            }
        }
        else
        {
            throw ProvisioningDeviceClientError(__func__, PROV_DEVICE_RESULT_ERROR);
        }
    }

    ~ProvisioningDeviceClient()
    {
        if (_prov_device_handle != NULL)
        {
            {
                ScopedGILRelease release;
                Prov_Device_Destroy(_prov_device_handle);
            }
            _prov_device_handle = NULL;
        }

        prov_dev_security_deinit();

        PlatformCallHandler::Platform_DeInit();
    }

    PROV_DEVICE_RESULT Register_Device(
        boost::python::object& register_callback,
        boost::python::object& user_context,
        boost::python::object& register_status_callback,
        boost::python::object& status_user_context
    )
    {
        if (!PyCallable_Check(register_callback.ptr()))
        {
            PyErr_SetString(PyExc_TypeError, "register_device expected register_callback callable a callable type");
            boost::python::throw_error_already_set();
            return PROV_DEVICE_RESULT_INVALID_ARG;
        }
        if (!PyCallable_Check(register_status_callback.ptr()))
        {
            PyErr_SetString(PyExc_TypeError, "register_device expected register_status_callback callable a callable type");
            boost::python::throw_error_already_set();
            return PROV_DEVICE_RESULT_INVALID_ARG;
        }

        PROV_DEVICE_RESULT result;

        RegisterDeviceContext* registerDeviceContext = new RegisterDeviceContext();
        registerDeviceContext->register_callback = register_callback;
        registerDeviceContext->userContext = user_context;

        RegisterDeviceStatusContext* registerDeviceStatusContext = new RegisterDeviceStatusContext();
        registerDeviceStatusContext->register_status_callback = register_status_callback;
        registerDeviceStatusContext->status_user_context = status_user_context;

        {
            ScopedGILRelease release;
            result = Prov_Device_Register_Device(_prov_device_handle, RegisterDeviceCallback, registerDeviceContext, RegisterDeviceStatusCallback, registerDeviceStatusContext);
        }
        if (result != PROV_DEVICE_RESULT_OK)
        {
            throw ProvisioningDeviceClientError(__func__, result);
        }

        return result;
    }

    void SetOption(
        std::string option_name,
        boost::python::object& option_value
    )
    {
        static const char* OPTION_LOG_TRACE = "logtrace";

        PROV_DEVICE_RESULT result;

        ScopedGILRelease release;

        if (option_name == OPTION_TRUSTED_CERT)
        {
            if (PyString_Check(option_value.ptr()))
            {
                std::string value = (std::string)boost::python::extract<std::string>(option_value);

                result = Prov_Device_SetOption(_prov_device_handle, option_name.c_str(), value.c_str());
            }
            else
            {
                result = PROV_DEVICE_RESULT_ERROR;
            }
        }
        else if (option_name == OPTION_LOG_TRACE)
        {
            if (PyBool_Check(option_value.ptr()))
            {
                bool value = (bool)boost::python::extract<bool>(option_value);

                result = Prov_Device_SetOption(_prov_device_handle, option_name.c_str(), &value);
            }
            else
            {
                result = PROV_DEVICE_RESULT_ERROR;
            }
        }
        else if (option_name == OPTION_HTTP_PROXY)
        {
            HttpProxyOptions http_proxy_options = (HttpProxyOptions)boost::python::extract<HttpProxyOptions>(option_value);

            HTTP_PROXY_OPTIONS value;
            value.host_address = http_proxy_options.host_address.c_str();
            value.port = http_proxy_options.port;
            value.username = http_proxy_options.username.c_str();
            value.password = http_proxy_options.password.c_str();

            result = Prov_Device_SetOption(_prov_device_handle, option_name.c_str(), &value);
        }
        else
        {
            result = PROV_DEVICE_RESULT_ERROR;
            throw ProvisioningDeviceClientError(__func__, PROV_DEVICE_RESULT_INVALID_ARG);
        }

        if (result != PROV_DEVICE_RESULT_OK)
        {
            printf("SetOption failed with result: %d", result);
        }
    }

    const char* GetVersionString()
    {
        ScopedGILRelease release;
        return Prov_Device_GetVersionString();
    }
};

using namespace boost::python;

static const char* provisioning_device_client_docstring =
"provisioning_device_client is a Python module for communicating with Azure Device Provisioning Service";

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
    scope().attr("__doc__") = provisioning_device_client_docstring;
    scope().attr("__version__") = VERSION_STRING;

    // exception handlers
    class_<ProvisioningDeviceClientError>ProvisioningDeviceClientErrorClass("ProvisioningDeviceClientErrorArg", init<std::string, PROV_DEVICE_RESULT>());
    ProvisioningDeviceClientErrorClass.def_readonly("result", &ProvisioningDeviceClientError::result);
    ProvisioningDeviceClientErrorClass.def_readonly("func", &ProvisioningDeviceClientError::func);
    ProvisioningDeviceClientErrorClass.def("__str__", &ProvisioningDeviceClientError::str);
    ProvisioningDeviceClientErrorClass.def("__repr__", &ProvisioningDeviceClientError::repr);

    register_exception_translator<ProvisioningDeviceClientError>(provisioningDeviceClientError);

    provisioningErrorType = createExceptionClass("ProvisioningError");
    provisioningDeviceClientErrorType = createExceptionClass("ProvisioningDeviceClientError", provisioningErrorType);
    
    enum_<PROV_DEVICE_REG_STATUS>("ProvisioningDeviceRegistrationStatus")
        .value("CONNECTED", PROV_DEVICE_REG_STATUS_CONNECTED)
        .value("REGISTERING", PROV_DEVICE_REG_STATUS_REGISTERING)
        .value("ASSIGNING", PROV_DEVICE_REG_STATUS_ASSIGNING)
        .value("ASSIGNED", PROV_DEVICE_REG_STATUS_ASSIGNED)
        .value("ERROR", PROV_DEVICE_REG_STATUS_ERROR)
        ;

    enum_<PROV_SECURE_DEVICE_TYPE>("ProvisioningSecurityDeviceType")
        .value("UNKNOWN", UNKNOWN)
        .value("TPM", TPM)
        .value("X509", X509)
        ;

    enum_<PROV_DEVICE_RESULT>("ProvisioningDeviceResult")
        .value("OK", PROV_DEVICE_RESULT_OK)
        .value("INVALID_ARG", PROV_DEVICE_RESULT_INVALID_ARG)
        .value("SUCCESS", PROV_DEVICE_RESULT_SUCCESS)
        .value("MEMORY", PROV_DEVICE_RESULT_MEMORY)
        .value("PARSING", PROV_DEVICE_RESULT_PARSING)
        .value("TRANSPORT", PROV_DEVICE_RESULT_TRANSPORT)
        .value("INVALID_STATE", PROV_DEVICE_RESULT_INVALID_STATE)
        .value("DEV_AUTH_ERROR", PROV_DEVICE_RESULT_DEV_AUTH_ERROR)
        .value("TIMEOUT", PROV_DEVICE_RESULT_TIMEOUT)
        .value("KEY_ERROR", PROV_DEVICE_RESULT_KEY_ERROR)
        .value("ERROR", PROV_DEVICE_RESULT_ERROR)
        ;

    enum_<PROV_TRANSPORT_PROVIDER>("ProvisioningTransportProvider")
#ifdef USE_HTTP
        .value("HTTP", HTTP)
#endif
#ifdef USE_AMQP
        .value("AMQP", AMQP)
#endif
#ifdef USE_MQTT
        .value("MQTT", MQTT)
#endif
#ifdef USE_AMQP
        .value("AMQP_WS", AMQP_WS)
#endif
#ifdef USE_MQTT
        .value("MQTT_WS", MQTT_WS)
#endif
        ;

    // classes
    class_<HttpProxyOptions, boost::noncopyable>("ProvisioningHttpProxyOptions", no_init)
        .def(init<std::string, int, std::string, std::string>())
#ifdef SUPPORT___STR__
        .def("__str__", &HttpProxyOptions::str)
        .def("__repr__", &HttpProxyOptions::repr)
#endif
        ;

    class_<ProvisioningDeviceClient, boost::noncopyable>("ProvisioningDeviceClient", no_init)
        .def(init<std::string, std::string, PROV_SECURE_DEVICE_TYPE, PROV_TRANSPORT_PROVIDER>())
        .def("register_device", &ProvisioningDeviceClient::Register_Device)
        .def("set_option", &ProvisioningDeviceClient::SetOption)
        .def("get_version_string", &ProvisioningDeviceClient::GetVersionString)
        // attributes
        .def_readonly("protocol", &ProvisioningDeviceClient::_protocol)
        // Python helpers
#ifdef SUPPORT___STR__
        .def("__str__", &ProvisioningDeviceClient::str)
        .def("__repr__", &ProvisioningDeviceClient::repr)
#endif
        ;
};
