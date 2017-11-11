#!/bin/bash
# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

build_root=$(cd "$(dirname "$0")/../.." && pwd)
build_folder=$build_root"/c/cmake/iotsdk_linux"

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

./c/build_all/linux/build.sh --build-python $PYTHON_VERSION $* --provisioning
[ $? -eq 0 ] || exit $?
cd $build_root

echo copy iothub_client library to samples folder
cp $build_folder/python/src/iothub_client.so ./device/samples/iothub_client.so
echo copy iothub_client_mock library to tests folder
cp $build_folder/python/test/iothub_client_mock.so ./device/tests/iothub_client_mock.so
cp $build_folder/python/src/iothub_client.so ./device/tests/iothub_client.so
cp $build_folder/python_service_client/src/iothub_service_client.so ./device/tests/iothub_service_client.so

echo copy iothub_service_client library to samples folder
cp $build_folder/python_service_client/src/iothub_service_client.so ./service/samples/iothub_service_client.so
echo copy iothub_service_client_mock library to tests folder
cp $build_folder/python_service_client/tests/iothub_service_client_mock.so ./service/tests/iothub_service_client_mock.so
cp $build_folder/python_service_client/src/iothub_service_client.so ./service/tests/iothub_service_client.so
cp $build_folder/python/src/iothub_client.so ./service/tests/iothub_client.so

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
