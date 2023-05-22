# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.
script_dir=$(cd "$(dirname "$0")" && pwd)
root_dir=$(cd "${script_dir}/../.." && pwd)

DOCKERFILE_NAME=$1
IMAGE_NAME=$2

if [ "${DOCKERFILE_NAME}" == "" ] || [ "${IMAGE_NAME}" = "" ]; then
    echo Usage: $0 dockerfileName imageName 
    echo eg. $f Dockerfile.py310 localhost:5000/python-e2e-py310:latest
    exit 1
fi

cd ${script_dir}/dockerfiles

docker build -t ${IMAGE_NAME} ${root_dir} -f ${DOCKERFILE_NAME}
[ $? -eq 0 ] || { echo "docker build failed"; exit 1; }

docker push ${IMAGE_NAME}
[ $? -eq 0 ] || { echo "docker push failed"; exit 1; }

