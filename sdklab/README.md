<div align=center>
    <img src="../azure-iot-device/doc/images/azure_iot_sdk_python_banner.png"></img>
</div>

# Azure IoT SDK for Python SDK Lab tools

This directory contains a set of command-line tools that exercise the Azure IoT SDK for Python in different and sometimes interesting ways.
The tools are like end-to-end tests, or stress tests, or long-haul tests.

They show examples of library usage, but they should not be considered as samples. In some cases, they do "bad things".

The name "sdklab" is inspired by the idea that this like a laboratory full of tools and experiments that can be used to exercise the SDK.
* Some of them are perfectly innocent apps that do everything "correctly," but perhaps a bit aggressively than traditional samples or tests.
* Some of them use undocumented knowledge to alter or distort the behavior of the library.
* Some of them simulate very specific conditions which have been known to break functionality in the past.
* Some of them use common but strange programming practices technically correct and legal, but don't make much sense.
* Some of them expose (hopefully theoretical) bugs that haven't been fixed yet or weaknesses in the library that will eventually need to be architected away.

These are all designed to return a success value so they can be used in shell scripts or ci/cd pipelines.
The goal is to have them all succeed and return `0` 100% of the time.
When the apps do this, they can be added to `run_gate_tests.py` so they get run regularly to ensure library quality and prevent bit-rot.
Some of the apps in here won't succeed.
Returning failure is reserved for apps that expose issues that have been discovered but not yet fixed.

# Test App Description

## `meantimerecovery` directory

This tool predates the re-organization of this set of tools.
It has a README that describes how it can be used, and it does not follow the "should always return success" rules discussed above.

## `./fuzzing/fuzz_send_message.py`

This tool exercises the `send_message` method with different faults injected into Paho at different times. Documentation on what faults are injected can be found in `../dev_utils/dev_utils/paho_fuzz_hook.py`.

## `./regressions/regression_pr1023_infinite_get_twin.py`

This tool exercises a shutdown scenario that was fixed in pull request #1023.

## `./regressions/regression_github_990.py`

This tool verifies a number of different behaviors around reconnect failures that were originally reported in GitHub issue #990.

## `./simple_stress/simple_send_message_bulk.py`

This tool verifies simple ``send_message` operation in bulk.


