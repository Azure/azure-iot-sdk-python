#
# Scripe to create an IoT Edge deployment manifest from a template file
#
script_dir=$(cd "$(dirname "$0")" && pwd)

TEST_IMAGE_NAME=$1
ECHO_IMAGE_NAME=$2

if [ "${TEST_IMAGE_NAME}" == "" ] || [ "${ECHO_IMAGE_NAME}" == "" ]; then
    echo Usage: $0 testImageName echoImageName
    exit 1
fi


#
# EdgeAgent and EdgeHub image names
#
DOCKER_TAG_EDGE_AGENT=1.4
DOCKER_TAG_EDGE_HUB=1.4
EDGE_AGENT_IMAGE_NAME="mcr.microsoft.com/azureiotedge-agent:${DOCKER_TAG_EDGE_AGENT}"
EDGE_HUB_IMAGE_NAME="mcr.microsoft.com/azureiotedge-hub:${DOCKER_TAG_EDGE_HUB}"

#
# jq paths for various fields inside the deployment manifest
#
PATH_AGENT_PROPS=".modulesContent[\"\$edgeAgent\"][\"properties.desired\"]"
PATH_SYSTEM_MODULES="${PATH_AGENT_PROPS}.systemModules"
PATH_MODULES="${PATH_AGENT_PROPS}.modules"
PATH_REGISTRY_CREDENTIALS="${PATH_AGENT_PROPS}.runtime.settings.registryCredentials"
PATH_HUB_PROPS=".modulesContent[\"\$edgeHub\"][\"properties.desired\"]"
PATH_ROUTES="${PATH_HUB_PROPS}.routes"

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

#
# Use jq to populate the deployment manifest using the variables we set above.
#
cat ${script_dir}/deployment.template.json |\
    jq "${PATH_SYSTEM_MODULES}.edgeAgent.settings.image = \"${EDGE_AGENT_IMAGE_NAME}\"" |\
    jq "${PATH_SYSTEM_MODULES}.edgeHub.settings.image = \"${EDGE_HUB_IMAGE_NAME}\"" |\
    jq "${PATH_MODULES}.echoMod.settings.image = \"${ECHO_IMAGE_NAME}\"" |\
    jq "${PATH_MODULES}.testMod.settings.image = \"${TEST_IMAGE_NAME}\"" |\
    jq "${PATH_SYSTEM_MODULES}.edgeAgent.settings.createOptions |= tojson" |\
    jq "${PATH_SYSTEM_MODULES}.edgeHub.settings.createOptions |= tojson" |\
    jq "${PATH_MODULES}.echoMod.settings.createOptions |= tojson" |\
    jq "${PATH_MODULES}.testMod.settings.createOptions |= tojson" |\
    jq "${PATH_REGISTRY_CREDENTIALS} = ${REGISTRY_BLOCK}"

