# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import logging
from dev_utils import test_env
from azure.iot.device.aio import IoTHubDeviceClient

logging.basicConfig(level=logging.WARNING)

"""
This code checks to make sure the bug fixed by GitHub PR #1023 was fixed.

Order of events for the bug repro:

1. Customer code creates a client object and registers for twin change events.
2. When reconnecting, the device client code would issue a twin "GET" packet to the service.
   This is done to ensure the client has a current version of the twin, which may have been
   updated while the client was disconnected.
3. If `shutdown` is called _immediately_ after `connect`, the "GET" operation fails. This
   is expected because there was no response.
4. The EnsureDesiredPropertyStage code responds to the GET operation failure by submitting a
   new GET operation.
5. Because the client is shutting down, this second GET operation also fails.  Go to step 4.

Final result (before this fix):

Multiple GET calls and an access violation.
"""


async def main():
    # Create instance of the device client using the connection string
    device_client = IoTHubDeviceClient.create_from_connection_string(
        test_env.DEVICE_CONNECTION_STRING
    )

    # Connect the device client.
    await device_client.connect()

    async def on_patch(p):
        print("Got patch")

    # Even though we're not expecting a patch, registering for the patch is an important
    # precondition for this particular bug.
    device_client.on_twin_desired_properties_patch_received = on_patch

    # Send a single message
    print("Sending message...")
    await device_client.send_message("This is a message that is being sent")
    print("Message successfully sent!")

    print("Getting twin...")
    await device_client.get_twin()
    print("got twin...")

    print("Disconnecting")
    await device_client.disconnect()
    print("Disconnected")

    print("Connecting")
    await device_client.connect()
    print("Connected")

    # Finally, shut down the client

    # If this is done _immediately_ after the `connect` call, this used to trigger a race condition
    # which would cause a stack overflow and core dump.  Using `disconnect` instead of `shutdown`
    # or putting a sleep before this would not repro the same bug.

    print("Shutting down")
    await device_client.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
