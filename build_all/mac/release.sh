#!/bin/bash
# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

build_root=$(cd "$(dirname "$0")/../.." && pwd)

# run build script
./build.sh $*

# copy lib to release folder
cp $build_root/device/samples/iothub_client.so iothub_client/iothub_client.so
cp $build_root/service/samples/iothub_service_client.so iothub_service_client/iothub_service_client.so
