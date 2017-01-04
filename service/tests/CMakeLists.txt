#Copyright (c) Microsoft. All rights reserved.
#Licensed under the MIT license. See LICENSE file in the project root for full license information.

#this is CMakeLists.txt for iothub_service_client_python test

compileAsC99()

add_definitions( -DIMPORT_NAME=iothub_service_client_mock )

set(iothub_service_client_mock_c_files
    ./iothub_service_client_mock.cpp
    ../src/iothub_service_client_python.cpp
)

if(WIN32)
    set(iothub_service_client_mock_c_files ${iothub_service_client_mock_c_files} ../src/dllmain.c )
endif()

include_directories(../src)

add_library( iothub_service_client_mock SHARED
    ${iothub_service_client_mock_c_files} 
)

# output name of python module is iothub_client
SET_TARGET_PROPERTIES(iothub_service_client_mock PROPERTIES PREFIX "")
IF(WIN32)
    SET_TARGET_PROPERTIES(iothub_service_client_mock PROPERTIES SUFFIX ".pyd")
ENDIF(WIN32)

target_link_libraries(  
    iothub_service_client_mock
    ${Boost_LIBRARIES}
    ${PYTHON_LIBRARIES}
)
