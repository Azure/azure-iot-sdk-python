# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import asyncio
import uuid
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import Message

messages_to_send = 10

async def main():
    # The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
    # NOTE:  connection string must contain ;GatewayHostName=<hostname of your iot edge device>
    # make sure your IoT Edge box is setup as a 'transparent gateway' per the IOT Edge documentation
    conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
    # path to the root ca cert used on your iot edge device (must copy the pem file to this downstream device)
    # example:   /home/azureuser/edge_certs/azure-iot-test-only.root.ca.cert.pem
    ca_cert = os.getenv("IOTEDGE_ROOT_CA_CERT_PATH")

    certfile = open(ca_cert)
    root_ca_cert = certfile.read()

    # The client object is used to interact with your Azure IoT Edge device.
    device_client = IoTHubDeviceClient.create_from_connection_string(connection_string=conn_str,server_verification_cert=root_ca_cert)
    
    # Connect the client.
    await device_client.connect()

    async def send_test_message(i):
        print("sending message #" + str(i))
        msg = Message("test wind speed " + str(i))
        msg.message_id = uuid.uuid4()
        msg.correlation_id = "correlation-1234"
        msg.custom_properties["tornado-warning"] = "yes"
        await device_client.send_message(msg)
        print("done sending message #" + str(i))

    # send `messages_to_send` messages in parallel
    await asyncio.gather(*[send_test_message(i) for i in range(1, messages_to_send + 1)])

    # finally, disconnect
    await device_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
