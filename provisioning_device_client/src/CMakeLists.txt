#Copyright (c) Microsoft. All rights reserved.
#Licensed under the MIT license. See LICENSE file in the project root for full license information.

set(provisioning_device_client_python_c_files
    ./provisioning_device_client_python.cpp
)

if(WIN32)
    set(provisioning_device_client_python_c_files ${provisioning_device_client_python_c_files} ./dllmain.c ./provisioning_device_client_python.def)
endif()

include_directories(.)
include_directories(${DEV_AUTH_MODULES_CLIENT_INC_FOLDER})

add_library( provisioning_device_client_python SHARED
    ${provisioning_device_client_python_c_files} 
)

# output name of python module is iothub_client
SET_TARGET_PROPERTIES(provisioning_device_client_python PROPERTIES OUTPUT_NAME "provisioning_device_client")
SET_TARGET_PROPERTIES(provisioning_device_client_python PROPERTIES PREFIX "")
IF(WIN32)
    SET_TARGET_PROPERTIES(provisioning_device_client_python PROPERTIES SUFFIX ".pyd")
ENDIF(WIN32)

target_link_libraries(
    provisioning_device_client_python
    prov_device_client
    ${Boost_LIBRARIES}
    ${PYTHON_LIBRARIES}
)

if(${use_mqtt})
	target_link_libraries(  
		provisioning_device_client_python
		prov_mqtt_transport
	)
    if(${use_wsio})
	    target_link_libraries(  
		    provisioning_device_client_python
		    prov_mqtt_ws_transport
	    )
    endif()
endif()
if(${use_amqp})
	target_link_libraries(  
		provisioning_device_client_python
		prov_amqp_transport
	)
    if(${use_wsio})
	    target_link_libraries(  
		    provisioning_device_client_python
		    prov_amqp_ws_transport
	    )
    endif()
	linkUAMQP(provisioning_device_client_python)
endif()
if(${use_http})
	target_link_libraries(  
		provisioning_device_client_python
		prov_http_transport
	)
endif()

if(${use_wsio} AND WIN32)
    file(COPY $ENV{OpenSSLDir}/bin/libeay32.dll DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/../tests)
    file(COPY $ENV{OpenSSLDir}/bin/ssleay32.dll DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/../tests)
endif()

linkSharedUtil(provisioning_device_client_python)

set(install_libs
	provisioning_device_client_python
)

install(TARGETS ${install_libs} 
	LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
	ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)

