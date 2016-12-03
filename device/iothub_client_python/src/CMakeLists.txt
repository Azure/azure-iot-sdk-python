#Copyright (c) Microsoft. All rights reserved.
#Licensed under the MIT license. See LICENSE file in the project root for full license information.

set(iothub_client_python_c_files
    ./iothub_client_python.cpp
)

if(WIN32)
    if(${use_wsio})
        set(iothub_client_python_c_files ${iothub_client_python_c_files} ../windows/dllmain.c ../windows/iothub_client_ws.def)
    else()
        set(iothub_client_python_c_files ${iothub_client_python_c_files} ../windows/dllmain.c ../windows/iothub_client.def)
    endif()
endif()

include_directories(.)

add_library( iothub_client_python SHARED
    ${iothub_client_python_c_files} 
)

# output name of python module is iothub_client
SET_TARGET_PROPERTIES(iothub_client_python PROPERTIES OUTPUT_NAME "iothub_client")
SET_TARGET_PROPERTIES(iothub_client_python PROPERTIES PREFIX "")
IF(WIN32)
    SET_TARGET_PROPERTIES(iothub_client_python PROPERTIES SUFFIX ".pyd")
ENDIF(WIN32)

target_link_libraries(  
    iothub_client_python
    iothub_client 
)

if(${use_mqtt})
	target_link_libraries(  
		iothub_client_python
		iothub_client_mqtt_transport
	)
    if(${use_wsio})
	    target_link_libraries(  
		    iothub_client_python
		    iothub_client_mqtt_ws_transport
	    )
    endif()
endif()
if(${use_amqp})
	target_link_libraries(  
		iothub_client_python
		iothub_client_amqp_transport
	)
    if(${use_wsio})
	    target_link_libraries(  
		    iothub_client_python
		    iothub_client_amqp_ws_transport
	    )
    endif()
	linkUAMQP(iothub_client_python)
endif()
if(${use_http})
	target_link_libraries(  
		iothub_client_python
		iothub_client_http_transport
	)
endif()

target_link_libraries(  
	iothub_client_python
	${Boost_LIBRARIES}
    ${PYTHON_LIBRARIES}
)

if(${use_wsio} AND WIN32)
    file(COPY $ENV{OpenSSLDir}/bin/libeay32.dll DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/../../samples)
    file(COPY $ENV{OpenSSLDir}/bin/ssleay32.dll DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/../../samples)
endif()


linkSharedUtil(iothub_client_python)
