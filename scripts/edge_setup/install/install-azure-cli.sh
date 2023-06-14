# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

script_dir=$(cd "$(dirname "$0")" && pwd)
set -o pipefail

echo "Checking for azure CLI"
which az
if [ $? -eq 0 ]; then
    echo "Azure CLI installed"
else
    echo "Installing Azure CLI"

    curl -L https://aka.ms/InstallAzureCli | bash
    [ $? -eq 0 ] || { echo "install-microsoft-apt-repo failed"; exit 1; }
fi

az --version
[ $? -eq 0 ] || { echo "az --version failed"; exit 1; }

az extension add --name azure-iot
[ $? -eq 0 ] || { echo "az extension add failed"; exit 1; }

