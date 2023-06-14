# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

script_dir=$(cd "$(dirname "$0")" && pwd)

HUB_NAME=$1
DEVICE_ID=$2
TEST_IMAGE_NAME=$3
ECHO_IMAGE_NAME=$4

if [ "${HUB_NAME}" == "" ] || [ "${DEVICE_ID}" == "" ] || [ "${TEST_IMAGE_NAME}" == "" ] || [ "${ECHO_IMAGE_NAME}" == "" ]; then
    echo Usage: $0 hubName deviceId testImageName echoImageName
    echo    hubName is without '.azure-devices.net' suffix
    exit 1
fi

#
# JSON for test module createOptions
#
read -d '' TEST_MOD_CREATE_OPTIONS << EOF
{
  "HostConfig": {
    "Binds": [
      "/home/bertk/projects/v3:/sdk"
    ]
  },
  "Entrypoint": [
    "python3",
    "-uc",
    "import time; print('waiting'); time.sleep(3600);"
  ]
}
EOF
TEST_MOD_CREATE_OPTIONS=$(echo ${TEST_MOD_CREATE_OPTIONS} | jq ". |= tojson")
[ $? -eq 0 ] || { "jq failed"; exit 1; }

#
# JSON for echo module createOptions
#
read -d '' ECHO_MOD_CREATE_OPTIONS << EOF
{
  "Entrypoint": [
    "python3",
    "-uc",
    "import time; print('waiting'); time.sleep(3600);"
  ]
}
EOF
ECHO_MOD_CREATE_OPTIONS=$(echo ${ECHO_MOD_CREATE_OPTIONS} | jq ". |= tojson")
[ $? -eq 0 ] || { "jq failed"; exit 1; }

#
# JSON for routing rules
#
ROUTING_RULES=$(
jq ". |= tojson" <<EOF
{
  "test_to_echo": "FROM /messages/modules/testMod/outputs/output1  INTO BrokeredEndpoint(\"/modules/echoMod/inputs/input1\")",
  "echo_to_test": "FROM /messages/modules/echoMod/outputs/output2  INTO BrokeredEndpoint(\"/modules/testMod/inputs/input2\")",
  "default_route": "FROM /messages/modules/testMod/* INTO \$upstream"
}
EOF
)
[ $? -eq 0 ] || { "jq failed"; exit 1; }

${script_dir}/set-base-deployment.sh ${HUB_NAME} ${DEVICE_ID} \
    && ${script_dir}/add-registry-to-deployment.sh ${HUB_NAME} ${DEVICE_ID} \
    && ${script_dir}/add-module-to-deployment.sh ${HUB_NAME} ${DEVICE_ID} testMod ${TEST_IMAGE_NAME} "${TEST_MOD_CREATE_OPTIONS}" \
    && ${script_dir}/add-module-to-deployment.sh ${HUB_NAME} ${DEVICE_ID} echoMod ${ECHO_IMAGE_NAME} "${ECHO_MOD_CREATE_OPTIONS}" \
    && ${script_dir}/add-routing-rules-to-deployment.sh ${HUB_NAME} ${DEVICE_ID} "${ROUTING_RULES}" 
if [ $? -eq 0 ]; then
    echo "Deployment succeeded"
else
    echo "Deployment failed"
    exit 1
fi



