# IoT SDK Long Haul Technical Spec

The Longhaul tests are to ensure the SDK can handle the rigors of in-field life.

## Delivery scheduled

* Longhaul tests will follow a crawl-\>walk-\>run approach.  

* Longhaul tests will sim-ship tests for both node and python using the Horton framework.

## Parameters for Longhaul Testing

* The test should run between 12 and 336 hours (2 weeks), but could be run for much longer periods

* The test will perform a variety of operations and verify the results.  For example, D2C telemetry test will verify that the telemetry is sent successfully and also  arrived at the EventHub

### Crawl

* Tests will send D2C messages at a fixed cadence and verify receipt

* Tests will send time-series telemetry to the hub IoT Central dashboarding

* Tests will send reported properties to report test configuration and current status to the hub (elapsed time, average latency, etc)

* Tests will run until failure, 

* Failure conditions will include crash, timeout on message receive, timeout on send operation.

* Tests will be manually launched and manually verified.

* Basic IoT Central dashboarding will be avaliable.

### Walk

* Tests will use more iothub features (twin, methods, C2D, etc).

* Events such as "client disconnected" and "SAS token renewed" will be added to the telemetry stream.

* Fault injection tests will operate the same as simple D2C tests, but will launch as a seperate test scenario.

* test launch automation will be increased so tests can be run in Docker containers in more of a bulk fashion

* IoT Central dashboarding will be improved.

### Run

* More test scenarios will be supported.

* Tests can be configured and controlled via desired properties and C2D messages.  This includes operation cadence, failure properties, fault rates, and operation choices.

* Maximum chaos is supported.  

* DPS is used to provision devices to test

* Tests are run with all manner of authentication (x509, symmetric key, edge, etc)

## Operations to test

Operations will be phased in as follows.  These operation names are also used inside the various test structures below.

| Operation        | Stage |
|------------------|-------|
| D2C              | crawl |
| C2D              | walk  |
| getTwin          | walk  |
| updateTwin       | walk  |
| receiveTwinPatch | walk  |
| handleMethod     | walk  |
| invokeMe//ncy to send each message and get a PUBACK (includes REST overhead)
    # average since last telemetry report
    "averageLatencyD2cSend": 0.23031153284073919,
    # Additional latency until we can verify that eventhub received it.
    "averageLatencyD2cVerify": 0.15155073497080027,

    # How many send operations are currently in progress (probably waiting for PUBACK)
    "currentCountD2cSending": 0,
    # How many operations have been PUBACK'ed but not verified via eventhub
    "currentCountD2cVerifying": 0,
    
    # Counts completed/failed since start of run
    "totalCountD2cCompleted": 1039410,
    "totalCountD2cFailed": 0
}
 ```

## System health telemetry
 ```json
{
    # context switches in process running SDK.  "poor man's CPU utilization"
    "processVoluntaryContextSwitchesPerSecond": 2999.9,
    "processNonvoluntaryContexxtSwitchesPerSecond": 27.7,

    # memory use of process running SDK.
    "processResidentMemoryInKb": 70096,
    "processSharedMemoryInKb": 22924,

    # object count in pytest process
    "pytestGcObjectCount": 69133,

    # system memory stats
    "systemMemoryAvailableInKb": 3907996,
    "systemMemoryFreeInKb": 1712156,
    "systemMemorySizeInKb": 6777144,

    # sytem uptime.  useful?  maybe not
    "systemUptimeInSeconds": 61955.08
}
 ```

## Longhaul Operations

The main loop of the test schedules different operations on one-second intervals.  Each operation object is responsible for deciding what to do every time `schedule_one_second` is clled.  Some Operation objects will schedule multiple tasks in a single seconds (e.g. send x telemetry messages per second) and other Operation objects will only schedule tasks on every n'th call to `schedule_one_second` (e.g. update properties every 10 seconds).

The main loop looks roughly like this:
# flow
```python
# Array of operation objects that the loop can schedule.
operationlist = [ 
    SendTestTelemetry,          # send telemetry to IoTHub, measure latency, and verify receipt
    SendCentralTelemetry,       # send time-series data to IoT Central.
    UpdateCentralProperties ]   # update IoT Central properties
# Currently running tasks (Futures)
running_tasks = []

# Set initial properties such as language and OS version
update_initial_central_properties()

# loop forever
while not done:
    # Once per second, schedule one second worth of work for each operation.  All scheduled work
    # is returned and added to the running_tasks list.
    for operation in operation_list:
        if operation.enabled:
            running_tasks += operation.schedule_one_second()

    # Now that work is schedule, we can sleep for the rest of the second and let the Tasks run.
    await sleep_for_the_rest_of_the_second()
    
    # Look for completed tasks and failures before we schedule the next second of work
    running_tasks = check_for_completed_tasks_and_failures(running_tasks)
```
