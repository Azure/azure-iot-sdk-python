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

TEMPFILE=$(mktemp)

read -d '' BASE << EOF
{
  "modulesContent": {
    "\$edgeAgent": {
      "properties.desired": {
        "schemaVersion": "1.0",
        "runtime": {
          "type": "docker",
          "settings": {
            "minDockerVersion": "v1.25",
            "loggingOptions": "",
            "registryCredentials": {}
          }
        },
        "systemModules": {
          "edgeAgent": {
            "type": "docker",
            "settings": {
              "image": "mcr.microsoft.com/azureiotedge-agent:1.4",
              "createOptions": {}
            }
          },
          "edgeHub": {
            "type": "docker",
            "status": "running",
            "restartPolicy": "always",
            "settings": {
              "image": "mcr.microsoft.com/azureiotedge-hub:1.4",
              "createOptions": {
                "HostConfig": {
                  "PortBindings": {
                    "5671/tcp": [ { "HostPort": "5671" } ],
                    "8883/tcp": [ { "HostPort": "8883" } ],
                    "443/tcp": [ { "HostPort": "443" } ]
                  }
                }
              }
            }
          }
        },
        "modules": {}
      }
    },
    "\$edgeHub": {
      "properties.desired": {
        "schemaVersion": "1.0",
        "routes": {},
        "storeAndForwardConfiguration": {
          "timeToLiveSecs": 7200
        }
      }
    }
  }
}
EOF



echo ${BASE} | jq . - \
    | jq "${PATH_SYSTEM_MODULES}.edgeAgent.settings.createOptions |= tojson" \
    | jq "${PATH_SYSTEM_MODULES}.edgeHub.settings.createOptions |= tojson" \
    > ${TEMPFILE}

echo Applying base manifest
az iot edge set-modules --device-id ${DEVICE_ID} --hub-name ${HUB_NAME} --content ${TEMPFILE}
[ $? -eq 0 ] || { echo "az iot edge set-modules failed"; exit 1; }

rm ${TEMPFILE} || true
