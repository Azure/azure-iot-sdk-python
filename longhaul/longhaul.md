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

* Tests will use those same D2C to deliver time-series telemetry (such as memory use, ) to the hub for dashboarding

* Tests will use reported properties to report test configuration and current status to the hub (elapsed time, average latency, etc)

* Tests will run until failure, 

* Failure conditions will include crash, timeout on message receive, timeout on send operation, and heap level checks.

* Tests will be manually launched and manually verified.

### Walk

* Tests will use more iothub features (twin, methods, C2D, etc).

* Fault injection tests will operate the same as simple D2C tests, but will launch as a seperate test scenario.

* Simple randomization of these operations will be supported.  Overlapping of different operations won't need to happen here.

* test launch automation will be increased so tests can be run in Docker containers in more of a bulk fashion


### Run

* More test scenarios will be supported, hopefully with the same test core running with different options.

* Tests can be configured and controlled via desired properties and C2D messages.  This includes operation cadence, failure properties, fault rates, and operation choices.

* Maximum chaos is supported.  

* DPS is used to provision devices to test

* Tests are run with all manner of authenticatoin (x509, symmetric key, edge, etc)

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
| invokeMethod     | walk  |
| DPS register     | run   |
| blob upload      | run   |


## Lonhaul configuration and progress

* D2C telemetry will be used to send time-series data for deshboarding.

* Reported propertis will be used to send static properties and current status.

* Some of these data will be duplicated in telemetry and reported properties

| mechanism           | data                                      | update frequency    |
|---------------------|-------------------------------------------|---------------------|
| D2C                 | progress                                  | once per second     |
| reported properties | platform, sdk, testConfig, progres, stats | four times a minute |
| desired properties  | testConfig (for updates - in run phase)   | service initiated   |
| C2D                 | control messages                          | service initiated   |

## Sample D2C message

```
"longhaulInfo": {
    "progress": {
        "status": "running",
        "runtime": "00:01:07",
        "heapUsed": "12.83",
        "activeObjects": 5184,
        "completeOpertions": 5001,
        "outstandingOperations": 5,
        "slowOperations": 15,
    },
}
```

## Sample reported properties

```
"longhaulInfo": {
    "platform: {
        "os": "linux",
        "framworkVersion": "Node v12.16",
        "heapSize": 15.4,
    },
    "sdk": {
        "language": "node",
        "version": "2.0.0",
        "installSource": "npm",
        "sourceRepo": "Azure/azure-iot-sdk-node",
        "sourceBranch": "master",
        "sourePr": "512",
        "sourceCommit": "a489ab11e53b9c0cfe5c8da9f048c98ae91e9d98",
    },
    testConfig: {
        "scenario": "telemetry 5 mps",
        "total_duration": "3:00",
        "D2C"": {
            "enabled": true,
            "interval": 1,
            "opsPerInterval": 5,
        }

    },
    "progress": {
        "status": "running",
        "processUptime": "00:01:07",
        "memoryUsed": 12.83,
        "activeObjects": 5184,
        "completeOperations": 1321
        "outstandingOperations": 5,
        "failedOperations": 2,
        "slowSends": 10,
        "slowReceives": 25,
    },
    "stats": {
        "D2C": {
            "outstandingOperations": 5,
            "failedOperations": 2,
            "slowSends": 10,
            "slowReceives": 25,
        }
    }
}
```

## Fields (platform)

The data in the platform object describes the hardware and OS that the test is running on.

| Field Name       | type    | required | Description |
|------------------|---------|----------|-------------|
| os               | String  | yes      | The OS type being run on ie Linux, iOS, Win ...
| frameworkVersion | String  | yes      | The version of the system running the application ie node version, python version, ...
| heapSize         | float   | yes      | Total amount of heap available in the process in MB

## Fields (sdk)

The data in the sdk object describes the libraries that the test is using 

| Field Namei    | type    | required | Description |
|----------------|---------|----------|-------------|
| language       | String  | yes      | Azure SDK language
| version        | String  | yes      | The version of the SDK version
| installSource  | String  | no       | either the name of a package manager (pypi, npm, etc) or an install URI
| sourceRepo     | String  | no       | repo for source code 
| sourceBranch   | String  | no       | branch for source code
| sourePr        | String  | no       | PR # for source code
| sourceCommit   | String  | no       | sha for source commit 

## Fields (testConfig)

The data in the testConfg object describes the runtime configuration for the current test run.
Fields in this structure can be reported (R), desired (D), or both.

| Field Name    | type    | required | Desired or Reported | Description |
|---------------|---------|----------|---------------------|-------------|
| scenario      | String  | yes      | Reported            | Name of the test scenario being run 
| totalDuration | Time    | yes      | Both                | Total run time for the test scenario being run

Also, for each operation, there is a sub-object which contains configuration for that operation:

| Field Name            | type    | required | Desired or Reported | Default value | Description |
|-----------------------|---------|----------|---------------------|---------------|-------------|
| enabled               | bool    | yes      | Both                |               | Is this op inclued in the test run?
| interval              | integer | yes      | Both                |               | interval (in seconds) to run this test operation
| opsPerInterval        | integer | yes      | Both                |               |  How many test operations to run per interval
| timeoutThreshold      | float   | yes      | Both                | 600           | Maximum time in seconds before an operatoin is considered failed
| allowedFailures       | integer | no       | Both                | 0             | Number of failures allowed before a test run fails
| slowSendThreshold     | float   | yes      | Both                | 10            | Maximum time to send before an operatoin is considered "slow"
| slowReceiveThreshold  | float   | yes      | Both                | 30            | Maximum time to receive before an operation is considered "slow"
| allowedSlowSends      | integer | no       | Both                | 0             | Number of slow ops allowed before the test run fails
| allowedSlowReceives   | integer | no       | Both                | 0             | Number of slow ops allowed before the test run fails

## Fields (progress)

The data in the progress object describes the progress of teh test run along with a minimal set of 
telemetry that can be used to graph the progression of the test

| Field Name            | type    | required | Description |
|-----------------------|---------|----------|-------------|
| index                 | integer | yes      | index for this progress record, starts at 1 and incriments for each succcessive report
| status                | string  | yes      | current status.  one of new, running, failed, or succeeded 
| processUptime         | Time    | yes      | Amount of time the process has been running
| memoryUsed            | double  | yes      | Amount of heap use in the process in MB
| activeObjects         | integer | no       | Number of active objects being used (if available)
| completeOperations    | integer | yes      | Number of discrete opersations run so far
| outstandingOperations | integer | yes      | Number of operations started but not yet completed
| failedOperations      | integer | yes      | Number of operations that have failed
| slowSends             | integer | yes      | Number of operations that have sent "slowly" (defined by the slowness threshold for that operation type)
| slowReceives          | integer | yes      | Number of operations that have received "slowly" (defined by the slowness threshold for that operation type)


## Fields (stats)

The data in the stats object describes performance statistics on different groups of operations.
The stats object is composed of a number of sub objects, each named for the test operation they apply to.

| Field Name            | type    | required | Description |
|-----------------------|---------|----------|-------------|
| totalFailed           | integer | yes      | Total number of operations of this type failed so far
| totalComplete         | integer | yes      | Total number of operations of this type completed so far
| totalOutstanding      | integer | yes      | Total number of operations of this type started but not completed
| totalSlow             | integer | yes      | Total number of operations that are considered "slow"


## Longhaul Operations

1. Connect to DPS to retrieve IoTHub information (run phase)

2. Connect to the specified IoTHub

3. Once connected to IoThub retrieve Device Twin for configuration settings

4. Setup C2D connection to retrieve exit msg

5. Send Telemetry messages in a loop for designated time

6. Inspect the telemetry message in the Eventhub to ensure the message is sent correctly

A twin update may be retrieved that will updated the frequency of the sending of the telemetry messages
