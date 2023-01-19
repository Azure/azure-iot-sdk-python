# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

## SCENARIO
An application is creating random messages and sending them at an interval consistently as long as 
network connection remains. In case of disconnection the customer wants to retry the connection for 
errors that are worth retrying. Currently, the time at which insertions and retrieval happens at 
TELEMETRY_INTERVAL. In this scenario the customer does not care about the messages that were sent 
and the exceptions that might have occurred in sending them. The customer does not store the messages 
that resulted in an exception.

## WORKING APP

The application should work seamlessly and continuously as long as the customer does not exit the application. 
The application can also raise an unrecoverable exception and exit itself. In case of recoverable 
error where the network connection drops, the application should try to establish connection again.

The application has significant logging as well to check on progress and troubleshoot issues. 

## APP SPECIFIC LOGS

Several log files will be generated as the application runs. The DEBUG and INFO logs are generated 
on a timed rotating logging handler. So multiple of DEBUG and INFO files based on time-stamp will be generated. 
The `sample.log` file will contain logging output only from the solution. 
The solution also prints similar texts onto the console for visual purposes.
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
Currently, whenever connection drops due to one of the following exceptions it is considered to be recoverable.
```python
[
    exceptions.OperationCancelled,
    exceptions.OperationTimeout,
    exceptions.ServiceError,
    exceptions.ConnectionFailedError,
    exceptions.ConnectionDroppedError,
    exceptions.NoConnectionError,
    exceptions.ClientError,
]
```
In the event the application has stopped working for any of the above errors, 
it will establish connection on its own and resume the application whenever the network is back.
Such intermittent disruptions are temporary and this is a correct process of operation.

Any other cause of exception is not retry-able. In case the application has stopped and exited,
the cause could be found out from the logs.