# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.
set -exo pipefail
trap 'echo ERROR on line ${LINENO}' ERR
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
docker build -t ${IMAGE} .
docker push ${IMAGE}

cd ${script_dir}/dockerfiles
for VERSION in py310; do 
    IMAGE=${CONTAINER_REPOSITORY}/python-${VERSION}:${TAG}
    docker build -t ${IMAGE} ${root_dir} -f Dockerfile.${VERSION}
    docker push ${IMAGE}
done

