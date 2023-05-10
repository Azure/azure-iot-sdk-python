# wait for a docker container to be running
CONTAINER_NAME=$1
while true; do
    state=$(docker inspect -f {{.State.Running}} ${CONTAINER_NAME})
    if [ $? -eq 0 ] && [ "${state}" == "true" ]; then
        echo ${CONTAINER_NAME} is running
        exit 0
    else
        sleep 5
    fi
done;
