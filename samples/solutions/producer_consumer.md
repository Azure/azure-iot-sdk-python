# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

## CUSTOMER PERSONA
A producer application is creating messages and inserting them in a queue uniformly at an TELEMETRY_INTERVAL secs.
Customer wants to fetch a message from a queue and send the message at some interval consistently as long as network 
connection remains. In case of disconnection the customer wants to retry the connection. Currently, the time at which 
insertions and retrieval happen is at TELEMETRY_INTERVAL secs. All connection failed attempts are retried starting with 
an initial value of INITIAL_SLEEP_TIME_BETWEEN_CONNS after which the interval between each retry attempt increases 
geometrically. Once the sleep time reaches a upper threshold called the THRESHOLD_FOR_RETRY_CONNECTION the application exits. A
ll values are configurable and customizable as per the scenario needs.

## TESTING
Exceptions via disconnections were introduced manually and deliberately in the following manner to check that the app works seamlessly. 
The application continued queuing messages and retrying connections with intermittent sleep till it reached the threshold set. 
In the tested sample the sleep time increased from 2 secs to 512 secs which was the set THRESHOLD_FOR_RETRY_CONNECTION. 
Once it reached this limit the application exited saying `Failed to connect the device client couple of times.Retry time is greater than upper limit set. 
Will be exiting the application.`
There are 2 ways disconnections were introduced as described below :-
  1. Deleted device identity from the IoT Hub. The error message so produced was where SLEEP_TIME = the sleep time calculated for the nth try that was in process.
     `Failed to connect the device client due to error :CredentialError.Sleeping and retrying after <SLEEP_TIME> seconds`
  2. Network was switched off. The error message so produced was where SLEEP_TIME = the sleep time calculated for the nth try that was in process.
     `Failed to connect the device client due to error :ConnectionFailedError.Sleeping and retrying after <SLEEP_TIME> seconds`

In both the above cases operation resumed smoothly by retrieving a message and sending it cases:-
  1. The device identity was created in the IoTHub with the same symmetric key.
  2. The network was brought back on.
  
There is a 3rd situation where the IoTHub was itself deleted. On the sample or on the client side it will show the same error as scenario 2 which is
  3. `Failed to connect the device client due to error :ConnectionFailedError.Sleeping and retrying after <SLEEP_TIME> seconds`- in this event 
      creating back the old hub will not solve the situation and will not resume normal mode of operation. The application will eventually exit once the threshold is reached.

## WORKING APP

The application should work seamlessly and continuously as long as the customer does not exit the application. 
The application can also raise an unrecoverable exception and exit itself. 
In case of recoverable error where the network connection drops, the application should try to establish connection again.

The application has significant logging as well to check on progress and troubleshoot issues. 

## APP SPECIFIC LOGS

Several log files will be generated as the application runs. The DEBUG and INFO logs are generated 
on a timed rotating logging handler. So multiple of DEBUG and INFO files based on time-stamp will be generated. 
The debug log files will be named like `debug.log.2023-01-04_11-28-49` and info log files will be named as 
`info.log.2023-01-04_11-28-49` with the date and timestamp. The next debug and log files will be generated with names 
like `debug.log.2023-01-04_12-28-49` and `info.log.2023-01-04_12-28-49` with a rotation interval of 1 hour.

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
Currently, whenever connection drops it is considered to be recoverable.

In the event the application has stopped working for any error, it will establish connection on its own and resume the 
application whenever the network is back. Such intermittent disruptions are temporary and this is a 
correct process of operation.


Any other cause of exception is not retryable. In case the application has stopped and exited,
the cause could be found out from the logs. 



