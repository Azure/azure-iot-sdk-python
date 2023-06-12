# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

script_dir=$(cd "$(dirname "$0")" && pwd)

DEVICE_ID=$1
HUB_NAME=$2
TEST_IMAGE_NAME=$3
ECHO_IMAGE_NAME=$4

if [ "${DEVICE_ID}" == "" ] || [ "${HUB_NAME}" == "" ] || [ "${TEST_IMAGE_NAME}" == "" ] || [ "${ECHO_IMAGE_NAME}" == "" ]; then
    echo Usage: $0 deviceId hubName testImageName echoImageName
    echo    hubName is without '.azure-devices.net' suffix
    exit 1
fi

TEMP_LOCATION=${SYSTEM_DEFAULTWORKINGDIRECTORY}
if [ "${TEMP_LOCATION}" == "" ]; then
    TEMP_LOCATION=/tmp
fi
MANIFEST_LOCATION=${TEMP_LOCATION}/deployment.json
echo "Storing manifest in ${MANIFEST_LOCATION}"

echo Creating deployment manifest
${script_dir}/make-edge-manifest.sh ${TEST_IMAGE_NAME} ${ECHO_IMAGE_NAME} > "${MANIFEST_LOCATION}"
[ $? -eq 0 ] || { echo "make-edge-manifest failed"; exit 1; }

echo Applying deployment manifest
az iot edge set-modules --device-id ${DEVICE_ID} --hub-name ${HUB_NAME} --content ${MANIFEST_LOCATION}
[ $? -eq 0 ] || { echo "az iot edge set-modules failed"; exit 1; }

