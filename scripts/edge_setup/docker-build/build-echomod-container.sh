# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.
script_dir=$(cd "$(dirname "$0")" && pwd)

IMAGE_NAME=$1

if [ "${IMAGE_NAME}" == "" ]; then
    echo Usage: $0 imageName
    echo   eg: $0 localhost:5000/echomod:latest
    exit 1
fi

docker pull ${IMAGE_NAME}

if [ $? -eq 0 ]; then
    echo "${IMAGE_NAME} already exists. Skipping build"
else
    cd ${script_dir}/echoMod

    docker build -t ${IMAGE_NAME} .
    [ $? -eq 0 ] || { echo "docker build failed"; exit 1; }

    docker push ${IMAGE_NAME}
    [ $? -eq 0 ] || { echo "docker push failed"; exit 1; }
fi

