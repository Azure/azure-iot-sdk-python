# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

script_dir=$(cd "$(dirname "$0")" && pwd)

$script_dir/install-azure-cli.sh
[ $? -eq 0 ] || { echo "install-azure-cli.sh failed"; exit 1; }

$script_dir/install-moby.sh
[ $? -eq 0 ] || { echo "install-moby.sh failed"; exit 1; }

$script_dir/install-iotedge.sh
[ $? -eq 0 ] || { echo "install-moby.sh failed"; exit 1; }
