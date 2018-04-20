#!/bin/bash
# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

build_root=$(cd "$(dirname "$0")/../.." && pwd)
build_folder=$build_root"/c/cmake/iotsdk_mac"

cd $build_root

PYTHON_VERSION=2.7

process_args()
{
    save_next_arg=0
    
    for arg in $*
    do
      if [ $save_next_arg == 1 ]
      then
        PYTHON_VERSION="$arg"
        if [ $PYTHON_VERSION != "2.7" ] && [ $PYTHON_VERSION != "3.4" ] && [ $PYTHON_VERSION != "3.5" ] && [ $PYTHON_VERSION != "3.6" ]
        then
          echo "Supported python versions are 2.7, 3.4, 3.5 or 3.6"
          exit 1
        fi
        save_next_arg=0
      else
        case "$arg" in
          "--build-python" ) save_next_arg=1;;
          * ) ;;
        esac
      fi
    done
}

process_args $*

########################################################
#build azure-iot-sdk-c
export OPENSSL_ROOT_DIR=/usr/local/opt/openssl
c_build_root=${build_root}"/c"

# brew installes python 3.x to $prefix/include/python3.xm
if [ $PYTHON_VERSION != "3.4" ] && [ $PYTHON_VERSION != "3.5" ] && [ $PYTHON_VERSION != "3.6" ]
then
	python_prefix=$(python-config --prefix)
	python_include=$python_prefix/include/python$PYTHON_VERSION
	python_lib=$python_prefix/lib/libpython$PYTHON_VERSION.dylib
else
	python_prefix=$(python3-config --prefix)
	python_include=$python_prefix/include/python${PYTHON_VERSION}m
	python_lib=$python_prefix/lib/libpython${PYTHON_VERSION}m.dylib
fi


rm -r -f $build_folder
mkdir -p $build_folder
pushd $build_folder
cmake -Drun_valgrind:BOOL=OFF -DcompileOption_CXX:STRING="-Wno-unused-value" -DcompileOption_C:STRING="-Wno-unused-value" -Drun_e2e_tests:BOOL=OFF -Drun_longhaul_tests=OFF -Duse_amqp:BOOL=ON -Duse_http:BOOL=ON -Duse_mqtt:BOOL=ON -Ddont_use_uploadtoblob:BOOL=OFF -Duse_wsio:BOOL=ON -Drun_unittests:BOOL=OFF -Dbuild_python:STRING=$PYTHON_VERSION -Dbuild_javawrapper:BOOL=OFF -Dno_logging:BOOL=OFF $c_build_root -Dwip_use_c2d_amqp_methods:BOOL=OFF -DPYTHON_LIBRARY=$python_lib -DPYTHON_INCLUDE_DIR=$python_include -Duse_prov_client:BOOL=ON

# Set the default cores
CORES=$(sysctl -n hw.ncpu)

make --jobs=$CORES
ctest -j $CORES -C "Debug" --output-on-failure

popd
########################################################


[ $? -eq 0 ] || exit $?
cd $build_root

echo copy iothub_client library to samples folder
cp $build_folder/python/src/iothub_client.dylib ./device/samples/iothub_client.so
echo copy iothub_client_mock library to tests folder
cp $build_folder/python/test/iothub_client_mock.dylib ./device/tests/iothub_client_mock.so
cp $build_folder/python/src/iothub_client.dylib ./device/tests/iothub_client.so
cp $build_folder/python_service_client/src/iothub_service_client.dylib ./device/tests/iothub_service_client.so

echo copy iothub_service_client library to samples folder
cp $build_folder/python_service_client/src/iothub_service_client.dylib ./service/samples/iothub_service_client.so
echo copy iothub_service_client_mock library to tests folder
cp $build_folder/python_service_client/tests/iothub_service_client_mock.dylib ./service/tests/iothub_service_client_mock.so
cp $build_folder/python_service_client/src/iothub_service_client.dylib ./service/tests/iothub_service_client.so
cp $build_folder/python/src/iothub_client.dylib ./service/tests/iothub_client.so

echo copy provisioning_device_client library to samples folder
cp $build_folder/provisioning_device_client_python/src/provisioning_device_client.dylib ./provisioning_device_client/samples/provisioning_device_client.so
echo copy provisioning_device_client_mock library to tests folder
cp $build_folder/provisioning_device_client_python/tests/provisioning_device_client_mock.dylib ./provisioning_device_client/tests/provisioning_device_client_mock.so
cp $build_folder/provisioning_device_client_python/src/provisioning_device_client.dylib ./provisioning_device_client/tests/provisioning_device_client.so

cd $build_root/device/tests/
echo "python${PYTHON_VERSION}" iothub_client_ut.py
"python${PYTHON_VERSION}" iothub_client_ut.py
[ $? -eq 0 ] || exit $?
echo "python${PYTHON_VERSION}" iothub_client_map_test.py
"python${PYTHON_VERSION}" iothub_client_map_test.py
[ $? -eq 0 ] || exit $?
cd $build_root

cd $build_root/service/tests/
echo "python${PYTHON_VERSION}" iothub_service_client_ut.py
"python${PYTHON_VERSION}" iothub_service_client_ut.py
[ $? -eq 0 ] || exit $?
echo "python${PYTHON_VERSION}" iothub_service_client_map_test.py
"python${PYTHON_VERSION}" iothub_service_client_map_test.py
[ $? -eq 0 ] || exit $?
cd $build_root

cd $build_root/provisioning_device_client/tests/
echo "python${PYTHON_VERSION}" provisioning_device_client_ut.py
"python${PYTHON_VERSION}" provisioning_device_client_ut.py
[ $? -eq 0 ] || exit $?
cd $build_root
