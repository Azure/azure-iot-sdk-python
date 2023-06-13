# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

script_dir=$(cd "$(dirname "$0")" && pwd)
source ${script_dir}/_deployment-helpers.sh

HUB_NAME=$1
DEVICE_ID=$2

if [ "${HUB_NAME}" == "" ] || [ "${DEVICE_ID}" == "" ]; then
    echo Usage: $0 hubName deviceId
    echo    hubName is without '.azure-devices.net' suffix
    exit 1
fi

if [ "${IOTHUB_E2E_REPO_USER}" == "" ] || [ "${IOTHUB_E2E_REPO_ADDRESS}" == "" ] || [ "${IOTHUB_E2E_REPO_PASSWORD}" == "" ]; then
    echo "No private repostiry specified"
    exit 0
fi

TEMPFILE=$(mktemp)

BASE=$(az iot edge export-modules --device-id ${DEVICE_ID} --hub-name ${HUB_NAME} --query content)
[ $? -eq 0 ] || { echo "az iot edge export-modules failed"; exit 1; }

#
# JSON for container retistry credentials
#
read -d '' REGISTRY_BLOCK << EOF
{
    ${IOTHUB_E2E_REPO_USER}: {
        address: \"${IOTHUB_E2E_REPO_ADDRESS}\",
        username: \"${IOTHUB_E2E_REPO_USER}\",
        password: \"${IOTHUB_E2E_REPO_PASSWORD}\"
    }
}
EOF

echo ${BASE} | jq . - \
    | jq "${PATH_REGISTRY_CREDENTIALS} = ${REGISTRY_BLOCK}" \
    > ${TEMPFILE}

echo Adding private registry to deployment manifest
az iot edge set-modules --device-id ${DEVICE_ID} --hub-name ${HUB_NAME} --content ${TEMPFILE}
[ $? -eq 0 ] || { echo "az iot edge set-modules failed"; exit 1; }

rm ${TEMPFILE} || true
