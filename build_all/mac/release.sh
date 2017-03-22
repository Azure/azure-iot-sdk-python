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

# instruct C builder to include python library and to skip tests
./c/build_all/mac/build.sh --build-python $PYTHON_VERSION $*
[ $? -eq 0 ] || exit $?
cd $build_root

echo copy iothub_client library to samples folder
cp $build_folder/python/src/iothub_client.dylib ./device/samples/iothub_client.dylib
echo copy iothub_client_mock library to tests folder
cp $build_folder/python/test/iothub_client_mock.dylib ./device/tests/iothub_client_mock.dylib

echo copy iothub_service_client library to samples folder
cp $build_folder/python_service_client/src/iothub_service_client.dylib ./service/samples/iothub_service_client.dylib
echo copy iothub_service_client_mock library to tests folder
cp $build_folder/python_service_client/tests/iothub_service_client_mock.dylib ./service/tests/iothub_service_client_mock.dylib

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

cd ./build_all/mac/release_device_client
cp $build_folder/python/src/iothub_client.dylib iothub_client/iothub_client.dylib
"python${PYTHON_VERSION}" setup_device_client.py bdist_wheel
cd $build_root

cd ./build_all/mac/release_service_client
cp $build_folder/python_service_client/src/iothub_service_client.dylib iothub_service_client/iothub_service_client.dylib
"python${PYTHON_VERSION}" setup_service_client.py bdist_wheel

cd $build_root
