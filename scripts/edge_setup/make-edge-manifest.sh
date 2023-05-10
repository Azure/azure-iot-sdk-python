#
# Scripe to create an IoT Edge deployment manifest from a template file
#
script_dir=$(cd "$(dirname "$0")" && pwd)


#
# EdgeAgent and EdgeHub image names
#
DOCKER_TAG_EDGE_AGENT=1.4
DOCKER_TAG_EDGE_HUB=1.4
DOCKER_IMAGE_EDGE_AGENT="mcr.microsoft.com/azureiotedge-agent:${DOCKER_TAG_EDGE_AGENT}"
DOCKER_IMAGE_EDGE_HUB="mcr.microsoft.com/azureiotedge-hub:${DOCKER_TAG_EDGE_HUB}"

#
# JQuery paths for various fields inside the deployment manifest
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
# Use JQuery to populate the deployment manifest using the variables we set above.
#
cat ${script_dir}/deployment.template.json |\
    jq "${PATH_SYSTEM_MODULES}.edgeAgent.settings.image = \"${DOCKER_IMAGE_EDGE_AGENT}\"" |\
    jq "${PATH_SYSTEM_MODULES}.edgeHub.settings.image = \"${DOCKER_IMAGE_EDGE_HUB}\"" |\
    jq "${PATH_MODULES}.echoMod.settings.image = \"mcr.microsoft.com/mirror/docker/library/python:3.10-slim-buster\"" |\
    jq "${PATH_MODULES}.testMod.settings.image = \"mcr.microsoft.com/mirror/docker/library/python:3.10-slim-buster\"" |\
    jq "${PATH_SYSTEM_MODULES}.edgeAgent.settings.createOptions |= tojson" |\
    jq "${PATH_SYSTEM_MODULES}.edgeHub.settings.createOptions |= tojson" |\
    jq "${PATH_MODULES}.echoMod.settings.createOptions |= tojson" |\
    jq "${PATH_MODULES}.testMod.settings.createOptions |= tojson" |\
    jq "${PATH_REGISTRY_CREDENTIALS} = ${REGISTRY_BLOCK}"

