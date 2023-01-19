# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

## CUSTOMER PERSONA
This application illustrates that connections are expensive and telemetry is only sent whenever connection is present.
Since connections are expensive, it is NOT necessary to keep track of lost messages. By any chance if connection is not 
established due to some error the retry process happens for a fixed set of NUMBER_OF_TRIES. All connection failed 
attempts for those NUMBER_OF_TRIES are retried starting with an initial value of INITIAL_SLEEP_TIME_BETWEEN_CONNS after 
which the interval between each retry attempt increases geometrically. Meanwhile, telemetry messages are enqueued 
inside a list at some random intervals. In the current sample connections are established every TIME_BETWEEN_CONNECTIONS
secs. Once connection is established all messages in the list are sent at once. In case message sending results in an 
exception that batch of messages are discarded. Regardless of whether messages are successfully transmitted or 
not the client is disconnected and waits for the next connection to be established.

## TESTING
Exceptions were thrown artificially and deliberately in the MQTT transport for random messages based on their id 
in the following manner to check that the app works seamlessly. The application discarded messages during an exception 
and moved on to the next batch.

```python
message_id = random.randrange(3, 1000, 1)
self.log_info_and_print("Id of message is: {}".format(message_id))
if message_id % 6 == 0:
    msg = Message("message that must raise exception")
else:
    msg = Message("current wind speed ")
```

## GARBAGE COLLECTION STATISTICS
This application has some garbage collection statistics which it displays from time to time. 
The statistics look like below.

```commandline
GC stats are:-
collections -> 124
collected -> 3212
uncollectable -> 0
collections -> 11
collected -> 366
uncollectable -> 0
collections -> 1
collected -> 323
uncollectable -> 0
```
## WORKING APP

The application should work seamlessly and continuously as long as the customer does not exit the application. 
The application can also raise an unrecoverable exception and exit itself. 
In case of recoverable error where the network connection drops, the application should try to establish connection again.

The application has significant logging as well to check on progress and troubleshoot issues. 

## APP SPECIFIC LOGS

Several log files will be generated as the application runs. The DEBUG and INFO logs are generated 
on a timed rotating logging handler. So multiple of DEBUG and INFO files based on time-stamp will be generated. 
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

In case the application has stopped and exited, the cause could be found out from the logs. 



