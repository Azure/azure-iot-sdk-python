#Copyright (c) Microsoft. All rights reserved.
#Licensed under the MIT license. See LICENSE file in the project root for full license information.

#this is CMakeLists.txt for provisioning_device_client_python

#These defines exist so that code that depends on a specific transport can be enabled/disabled with #ifdef
if(${use_amqp})
add_definitions(-DUSE_AMQP)
endif()

if(${use_mqtt})
    add_definitions(-DUSE_MQTT)
endif()

if(${use_http})
    add_definitions(-DUSE_HTTP)
endif()

compileAsC99()

# get boost
set(Boost_USE_MULTITHREADED      ON)
set(Boost_USE_STATIC_RUNTIME     OFF)

if(WIN32)
    set(Boost_INCLUDE_DIR $ENV{BOOST_ROOT})
    set(Boost_USE_STATIC_LIBS    ON) # only find static libs
    find_package(Boost COMPONENTS python REQUIRED)
    IF (NOT Boost_FOUND)
        message("FATAL ERROR: Boost Python library not found")
        message("On windows, get boost from http://www.boost.org/users/history/version_1_60_0.html")
        message("Extract zip to a folder, then perform bootstrap and build libs with b2 command")
        message("The BOOST_ROOT environment variable should point to the root folder")
        message("of the extracted boost package with headers and libraries")
        message(FATAL_ERROR "iothub_client_python needs Boost library")
    endif()
elseif(APPLE)
    if (${build_python} STREQUAL "2.7")
        find_package(Boost COMPONENTS python27)
    else()
        string(REPLACE "." "" boost_python ${build_python})
        find_package(Boost COMPONENTS python${boost_python})
        # mac boost-python libs don't support versions
        string(REPLACE "libboost_python-mt.dylib" "libboost_python3-mt.dylib" Boost_LIBRARIES ${Boost_LIBRARIES})
    endif()
else()
    # older boost-python libs didn't support versions
    if (${build_python} STREQUAL "2.7")
        find_package(Boost 1.58 EXACT COMPONENTS python)
    else()
        # Remove the period from python version for boost component
        string(REPLACE "." "" boost_python ${build_python})
        find_package(Boost 1.58 EXACT COMPONENTS "python-py${boost_python}")
    endif()
endif()

include_directories(${Boost_INCLUDE_DIRS})
link_directories(${Boost_LIBRARY_DIRS})

if (WIN32)
  # disable autolinking in boost
  add_definitions( -DBOOST_ALL_NO_LIB )
  # force all boost libraries to static link
  add_definitions( -DBOOST_ALL_STATIC_LINK )
  add_definitions( -DBOOST_PYTHON_STATIC_LIB )
endif()


# get python
# some versions of cmake shipped with Linux
# can't find the Python version unless given a hint
set(Python_ADDITIONAL_VERSIONS ${build_python})
find_package(PythonLibs ${build_python})
include_directories(${PYTHON_INCLUDE_DIRS})
link_directories(${PYTHON_LIBRARIES})

# get iothub_service_client and protocols
include_directories(${SHARED_UTIL_INC_FOLDER})
include_directories(${DEV_AUTH_MODULES_CLIENT_INC_FOLDER})
if(${use_http})
    include_directories(${IOTHUB_CLIENT_HTTP_TRANSPORT_INC_FOLDER})
endif()
if(${use_amqp})
    include_directories(${IOTHUB_CLIENT_AMQP_TRANSPORT_INC_FOLDER} ${UAMQP_INC_FOLDER})
endif()
if(${use_mqtt})
    include_directories(${IOTHUB_CLIENT_MQTT_TRANSPORT_INC_FOLDER} ${MQTT_INC_FOLDER})
endif()

if(${use_wsio})
    add_definitions(-DUSE_WEBSOCKETS)
endif()

add_subdirectory(src)
add_subdirectory(tests)
