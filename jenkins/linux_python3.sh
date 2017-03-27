#!/bin/bash
# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

build_root=$(cd "$(dirname "$0")/.." && pwd)
cd $build_root

# -- Python C wrapper --
./build_all/linux/build.sh --build-python 3.4 $*
[ $? -eq 0 ] || exit $?

python3 ./service/tests/iothub_service_client_e2e.py
[ $? -eq 0 ] || exit $?

python3 ./device/tests/iothub_client_e2e.py
[ $? -eq 0 ] || exit $?

