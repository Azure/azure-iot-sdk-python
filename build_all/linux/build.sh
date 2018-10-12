#!/bin/bash
# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

build_root=$(cd "$(dirname "$0")/../.." && pwd)
build_folder=$build_root"/c/cmake/iotsdk_linux"

cd $build_root

PYTHON_VERSION=2.7
USE_TPM_SIM=
make=true

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
        case "$arg" in
          "--use-tpm-simulator" ) USE_TPM_SIM="--use-tpm-simulator";;
          "--no-make" ) make=false;;
          * ) ;;
        esac
      fi
    done
}

process_args $*

# instruct C builder to include python library and to skip tests

if [ "$make" = false ]; then
  $NO_MAKE="--no-make"
fi

./c/build_all/linux/build.sh --build-python $PYTHON_VERSION $* --provisioning $USE_TPM_SIM --use-edge-modules $NO_MAKE
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

echo copy provisioning_device_client library to samples folder
cp $build_folder/provisioning_device_client_python/src/provisioning_device_client.so ./provisioning_device_client/samples/provisioning_device_client.so
echo copy provisioning_device_client_mock library to tests folder
cp $build_folder/provisioning_device_client_python/tests/provisioning_device_client_mock.so ./provisioning_device_client/tests/provisioning_device_client_mock.so
cp $build_folder/provisioning_device_client_python/src/provisioning_device_client.so ./provisioning_device_client/tests/provisioning_device_client.so

cd $build_root/device/tests/
echo "python${PYTHON_VERSION}" iothub_client_ut.py
"python${PYTHON_VERSION}" -u iothub_client_ut.py
[ $? -eq 0 ] || exit $?
echo "python${PYTHON_VERSION}" iothub_client_map_test.py
"python${PYTHON_VERSION}" -u iothub_client_map_test.py
[ $? -eq 0 ] || exit $?
cd $build_root

cd $build_root/service/tests/
echo "python${PYTHON_VERSION}" iothub_service_client_ut.py
"python${PYTHON_VERSION}" -u iothub_service_client_ut.py
[ $? -eq 0 ] || exit $?
echo "python${PYTHON_VERSION}" iothub_service_client_map_test.py
"python${PYTHON_VERSION}" -u iothub_service_client_map_test.py
[ $? -eq 0 ] || exit $?
cd $build_root

cd $build_root/provisioning_device_client/tests/
echo "python${PYTHON_VERSION}" provisioning_device_client_ut.py
"python${PYTHON_VERSION}" -u provisioning_device_client_ut.py
[ $? -eq 0 ] || exit $?
cd $build_root
