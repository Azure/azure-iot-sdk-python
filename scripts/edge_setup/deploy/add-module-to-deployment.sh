# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.
set -o pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
source ${script_dir}/_deployment-helpers.sh

HUB_NAME=$1
DEVICE_ID=$2
MODULE_NAME=$3
MODULE_IMAGE_NAME=$4
CREATE_OPTIONS=$5

if [ "${CREATE_OPTIONS}" == "" ]; then
    CREATE_OPTIONS="\"{}\""
fi


if [ "${HUB_NAME}" == "" ] || [ "${DEVICE_ID}" == "" ] || [ "${MODULE_NAME}" == "" ] || [ "${MODULE_IMAGE_NAME}" == "" ]; then
    echo Usage: $0 hubName deviceId moduleName moduleImageName [createOptionsJsonString]
    echo    hubName is without '.azure-devices.net' suffix
    exit 1
fi

echo Creating manifest json with module ${MODULE_NAME}
TEMPFILE=$(mktemp)

#
# JSON with required module JSON
#
read -d '' EMPTY_MODULE_JSON << EOF
{
  "version": "1.0",
  "type": "docker",
  "status": "running",
  "restartPolicy": "always",
  "settings": {
    "image": "TODO",
    "createOptions": "{}"
  }
}
EOF

BASE=$(az iot edge export-modules --device-id ${DEVICE_ID} --hub-name ${HUB_NAME} --query content)
[ $? -eq 0 ] || { echo "az iot edge export-modules failed"; exit 1; }

echo ${BASE} | jq . \
    | jq "${PATH_MODULES}.${MODULE_NAME} = ${EMPTY_MODULE_JSON}" \
    | jq "${PATH_MODULES}.${MODULE_NAME}.settings.image = \"${MODULE_IMAGE_NAME}\"" \
    | jq "${PATH_MODULES}.${MODULE_NAME}.settings.createOptions = ${CREATE_OPTIONS}" \
    > ${TEMPFILE}
[ $? -eq 0 ] || { "jq failed"; exit 1; }  

echo Applying manifest json with module ${MODULE_NAME}
az iot edge set-modules --device-id ${DEVICE_ID} --hub-name ${HUB_NAME} --content ${TEMPFILE} > /dev/null
[ $? -eq 0 ] || { echo "az iot edge set-modules failed"; exit 1; }

rm ${TEMPFILE} || true
