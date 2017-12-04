#Copyright (c) Microsoft. All rights reserved.
#Licensed under the MIT license. See LICENSE file in the project root for full license information.

#this is CMakeLists.txt for provisioning_device_client_python test

compileAsC99()

add_definitions( -DIMPORT_NAME=provisioning_device_client_mock )

set(provisioning_device_client_mock_c_files
    ./provisioning_device_client_mock.cpp
    ../src/provisioning_device_client_python.cpp
)

if(WIN32)
    set(provisioning_device_client_mock_c_files ${provisioning_device_client_mock_c_files} ../src/dllmain.c )
endif()

include_directories(../src)
include_directories(${DEV_AUTH_MODULES_CLIENT_INC_FOLDER})

add_library( provisioning_device_client_mock SHARED
    ${provisioning_device_client_mock_c_files} 
)

# output name of python module is provisioning_device_client
SET_TARGET_PROPERTIES(provisioning_device_client_mock PROPERTIES PREFIX "")
IF(WIN32)
    SET_TARGET_PROPERTIES(provisioning_device_client_mock PROPERTIES SUFFIX ".pyd")
ENDIF(WIN32)

target_link_libraries(  
    provisioning_device_client_mock
    ${Boost_LIBRARIES}
    ${PYTHON_LIBRARIES}
)
