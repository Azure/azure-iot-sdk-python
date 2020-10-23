# Mean time to recover first phase

## Current situation

Currently the only way to run `aedes` without changing code in the SDK. 
This is done so that we can pass server authentication with a self signed server verification certificate. 
In order to do so, a certificate needs to be generated whose subject is equivalent to the hostname of the machine where the `aedes` server is being run.

### Same HOST machine

Run the `aedes` server (with or without container) in the same host.
For connecting to this server the connection string for device client would have
`HostName=localhost`.
* Ensure that the `aedes` server is loaded with certificates whose common name is `localhost`.
* Ensure that this certificate is passed as the `kwarg server_verification_cert` during device client creation. 

### Different HOST Machine

Run the `aedes` server (with or without container) in a different host.
For example lets say the hostname of the machine or the container is `alohomora.net`.
For connecting to this server the connection string for device client would have
`HostName=alohomora.net`.
* Ensure that the `aedes` server is loaded with certificates whose common name is `alohomora.net`.
* Ensure that this certificate is passed as the `kwarg server_verification_cert` during device client creation.

#### Script for Mean Time to Recover

The main script for tracking mean time to recover is `mean_time_recover_with_docker.py`.
For this part the python package called `docker` needs to be installed.
`pip install docker` will do this. 

This package is needed so that the python script can access the Docker Engine API. 
It enables to do anything the docker command does, but from within python apps.

There are some variables that can be changed :-

`FACTOR_OF_KEEP_ALIVE` : the multiplication factor via which keep alive needs to be modified to calculate the amount of time the MQTT Broker will be down.

Other important variables already having values are :-

`KEEP_ALIVE` : option for changing the default keep alive for MQTT broker. Currently set at 15 secs.
`KEEP_RUNNING` : the amount of time the server needs to keep running for.
dead_duration : the amount of time the MQTT broker will be taken down for.
`KEEP_DEAD` : The amount of time the MQTT broker will be non responsive.
`MQTT_BROKER_RESTART_COUNT` : the count of times server will be stopped and started.

Before running the the `mean_time_recover_with_docker.py` script make sure your docker engine is running.

#### Certificate creation

There is another script which will create some self signed certificates for use in the `aedes` server.
For this part we would need a package called `cryptography`.
Prior to running this script please do `pip install cryptography` in the corresponding python environment .
To generate a certificate with a certain common name (possibly `localhost`) the script needs to be run like
`python create_self.py "localhost"`. There are no certificates included in the folder for aedes, so 
prior to running `aedes` server, certificates need to be generated.

### Debug or Test

If the `aedes` server or the docker container is run separately then for testing or debugging purposes
a simpler script called `simple_send_message.py`.

#### MQTT Broker

For this part docker is needed to be installed in your machine.
The mqtt broker being used is in the folder `aedes`. 
This has been configured to run locally in a docker container.
There is no need to run the container as the python script will do so 
but it is needed to build the image so that the `mean_time_recover_with_docker.py` can create a container later.

The docker commands to build the appropriate image is :
`docker build -t mqtt-broker . `

The docker command to remove the above image is
`docker image rm mqtt-broker`

#### Running aedes in a container

For `aedes` server these are required

* Navigate to `aedes` folder and run the above image building commands 
which will build the image with the help of the `Dockerfile` in that folder.
* Ensure that the `package.json` file similar to the one inside `aedes` folder exists.

#### Running docker container separately 

If `aedes` is run not as the part of the mean time script then the 
following steps need to be performed prior to that

* node js must be installed locally
* `npm install` must be done with the `package.json` in the current folder.
* appropriate certificates must be generated

For running the containerized aedes separately please use this command.
`docker run -d --publish 8883:8883 --name expecto-patronum mqtt-broker`