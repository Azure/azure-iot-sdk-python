# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.
script_dir=$(cd "$(dirname "$0")" && pwd)
root_dir=$(cd "${script_dir}/../.." && pwd)

CONTAINER_REPOSITORY=$1
TAG=$2

if [ "${TAG}" == "" ]; then
    TAG=latest
fi

if [ "${CONTAINER_REPOSITORY}" == "" ]; then
    echo Usage: $0 containerRepository [tag]
    exit 1
fi


cd ${script_dir}/echoMod
IMAGE=${CONTAINER_REPOSITORY}/echomod:${TAG}
docker pull ${IMAGE}

if [ $? -eq 0 ]; then
    echo "${IMAGE} already exists. Skipping build"
else
    docker build -t ${IMAGE} .
    [ $? -eq 0 ] || { echo "docker build failed"; exit 1; }
    docker push ${IMAGE}
    [ $? -eq 0 ] || { echo "docker push failed"; exit 1; }
fi

