# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

## CUSTOMER PERSONA
This application illustrates that a provisioning request can be sent again and multiple times to the Device Provisioning Service.
On first loading of the application the device registers for the first time. The application waits for the registration 
process to be completely successful. Once an IotHub assignment is done the device connects to the assigned IoTHub and 
starts sending telemetry at a constant rate. Currently, messages are sent at some interval consistently as long as 
network connection remains. In case of disconnection the customer wants to retry the connection. Currently, the time at 
which messages are sent is at TELEMETRY_INTERVAL secs. All connection failed attempts are retried starting with an 
initial value of INITIAL_SLEEP_TIME_BETWEEN_CONNECTION_ATTEMPTS after which the interval between each retry attempt 
increases geometrically. Once the sleep time reaches an upper threshold set by THRESHOLD_FOR_RETRY_CONNECTION the 
application retries the provisioning process again. It is to be noted that the application does not retry provisioning 
in case there is an error from provisioning itself. All values are configurable and customizable as per the scenario needs.

## TESTING
The device was deliberately deleted from the assigned hub to force a disconnection. And after retrying connections 
couple of times based on the sleep time , once it reached a certain threshold the application went 
back into provisioning the device again.

## WORKING APP

The application should work seamlessly and continuously as long as the customer does not exit the application. 
The application can also raise an unrecoverable exception and exit itself. 
In case of recoverable error where the network connection drops, the application should try to establish connection again.

As long as interval time between connection attempts does not go beyond a certain threshold the application will retry connection.
Once above a certain threshold the application starts the provisioning process again.

In case the provisioning process raises an error the application will exit. So the application does not 
retry provisioning in case of error from provisioning itself. Some errors from provisioning are related due to wrong 
configuration of the enrollment. During these times it is best to start over.

The application has significant logging as well to check on progress and troubleshoot issues. 

## APP SPECIFIC LOGS

Several log files will be generated as the application runs. The DEBUG and INFO logs are generated 
on a timed rotating logging handler. So multiple of DEBUG and INFO files based on time-stamp will be generated. 
The debug log files will be named like `debug.log.2023-01-04_11-28-49` and info log files will be named as 
`info.log.2023-01-04_11-28-49` with the date and timestamp. The next debug and log files will be generated with names 
like `debug.log.2023-01-04_12-28-49` and `info.log.2023-01-04_12-28-49` with a rotation interval of 1 hour set by LOG_ROTATION_INTERVAL.

The `sample.log` file will contain logging output only from the solution. The solution also prints similar texts onto the console for visual purposes.
Customer can modify the current logging and set it to a different level by changing one of the loggers.

## ADD LIBRARY SPECIFIC LOGGING

Customer can also add logging for example say into the MQTT Library Paho by doing 
```python
paho_log_handler = logging.handlers.TimedRotatingFileHandler(
    filename="{}/paho.log".format(LOG_DIRECTORY),
    when="S",
    interval=LOG_ROTATION_INTERVAL,
    backupCount=LOG_BACKUP_COUNT,
)
paho_log_handler.setLevel(level=logging.DEBUG)
paho_log_handler.setFormatter(log_formatter)
paho_logger = logging.getLogger("paho")
paho_logger.addHandler(paho_log_handler)
```

## TROUBLESHOOTING TIPS
Currently, whenever connection drops due it is considered to be recoverable, and it is retried for a fixed set of times.

In the event the application has stopped working for any of the above errors, it will establish connection on its own 
and resume the application whenever the network is back. Such intermittent disruptions are temporary and this is 
a correct process of operation.

In case the application has stopped and exited it could be either the provisioning process has run into an error out
or there is some other unrecoverable error that has caused the exit. The cause of such a thing can be found out from the logs.