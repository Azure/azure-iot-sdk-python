# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

script_dir=$(cd "$(dirname "$0")" && pwd)

DEVICE_ID=$1
HUB_NAME=$2

if [ "${DEVICE_ID}" == "" ] || [ "${HUB_NAME}" == "" ];  then
    echo Usage: $0 deviceId hubName
    echo    hubName is without '.azure-devices.net' suffix
    exit 1
fi

echo Creating device ${DEVICE_ID} on hub ${HUB_NAME}
TEMPFILE=$(mktemp)
az iot hub device-identity create -n ${HUB_NAME} --device-id ${DEVICE_ID} --edge-enabled &> ${TEMPFILE}
if [ $? -ne 0 ]; then
    echo "az iot hub device-identity create failed"
    cat ${TEMPFILE}
    rm ${TEMPFILE}
    exit 1;
fi

echo Getting connection string for ${DEVICE_ID} on ${HUB_NAME}
CS=$(az iot hub device-identity connection-string show -d ${DEVICE_ID} -n ${HUB_NAME} --output tsv --query "connectionString")
[ $? -eq 0 ] || { echo "az iot hub device-identity connection-string show failed"; exit 1; }

echo Setting IoTHub configuration
sudo -E iotedge config mp --force --connection-string ${CS}
[ $? -eq 0 ] || { echo "iotedge config mp failed"; exit 1; }

sudo iotedge config apply
[ $? -eq 0 ] || { echo "iotedge config apply failed"; exit 1; }

