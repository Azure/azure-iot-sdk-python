# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.
set -o pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
source ${script_dir}/_deployment-helpers.sh

HUB_NAME=$1
DEVICE_ID=$2
ROUTING_RULES=$3

if [ "${HUB_NAME}" == "" ] || [ "${DEVICE_ID}" == "" ] || [ "${ROUTING_RULES}" == "" ]; then
    echo Usage: $0 hubName deviceId routingRules
    echo    hubName is without '.azure-devices.net' suffix
    exit 1
fi

echo Creating manifest json with routing rules
TEMPFILE=$(mktemp)

BASE=$(az iot edge export-modules --device-id ${DEVICE_ID} --hub-name ${HUB_NAME} --query content)
[ $? -eq 0 ] || { echo "az iot edge export-modules failed"; exit 1; }

echo ${BASE} | jq . \
    | jq "${PATH_ROUTES} = ${ROUTING_RULES}" \
    | jq "${PATH_ROUTES} |= fromjson" \
    > ${TEMPFILE}
[ $? -eq 0 ] || { "jq failed"; exit 1; }  

echo Applying manifest json with routing rules
az iot edge set-modules --device-id ${DEVICE_ID} --hub-name ${HUB_NAME} --content ${TEMPFILE} > /dev/null
[ $? -eq 0 ] || { echo "az iot edge set-modules failed"; exit 1; }

rm ${TEMPFILE} || true
