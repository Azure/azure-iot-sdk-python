# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import uuid
import asyncio
from azure.iot.device.aio import IoTHubDeviceClient, IoTHubModuleClient
from azure.iot.device import X509
import http.client
import pprint
import json
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

"""
Welcome to the Upload to Blob sample. To use this sample you must have azure.storage.blob installed in your python environment.
To do this, you can run:

    $ pip isntall azure.storage.blob

This sample covers using the following Device Client APIs:

    get_storage_info_for_blob
        - used to get relevant information from IoT Hub about a linked Storage Account, including
        a hostname, a container name, a blob name, and a sas token. Additionally it returns a correlation_id
        which is used in the notify_blob_upload_status, since the correlation_id is IoT Hub's way of marking
        which blob you are working on.
    notify_blob_upload_status
        - used to notify IoT Hub of the status of your blob storage operation. This uses the correlation_id obtained
        by the get_storage_info_for_blob task, and will tell IoT Hub to notify any service that might be listening for a notification on the
        status of the file upload task.

You can learn more about File Upload with IoT Hub here:

https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-file-upload

"""

# Host is in format "<iothub name>.azure-devices.net"


async def storage_blob(blob_info):
    try:
        print("Azure Blob storage v12 - Python quickstart sample")
        sas_url = "https://{}/{}/{}{}".format(
            blob_info["hostName"],
            blob_info["containerName"],
            blob_info["blobName"],
            blob_info["sasToken"],
        )
        blob_client = BlobClient.from_blob_url(sas_url)
        # Create a file in local Documents directory to upload and download
        local_file_name = "data/quickstart" + str(uuid.uuid4()) + ".txt"
        filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), local_file_name)
        # Write text to the file
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        file = open(filename, "w")
        file.write("Hello, World!")
        file.close()

        print("\nUploading to Azure Storage as blob:\n\t" + local_file_name)
        # # Upload the created file
        with open(filename, "rb") as f:
            result = blob_client.upload_blob(f)
            return (None, result)

    except Exception as ex:
        print("Exception:")
        print(ex)
        return ex


async def main():
    hostname = os.getenv("IOTHUB_HOSTNAME")
    device_id = os.getenv("IOTHUB_DEVICE_ID")
    x509 = X509(
        cert_file=os.getenv("X509_CERT_FILE"),
        key_file=os.getenv("X509_KEY_FILE"),
        pass_phrase=os.getenv("PASS_PHRASE"),
    )

    device_client = IoTHubDeviceClient.create_from_x509_certificate(
        hostname=hostname, device_id=device_id, x509=x509
    )
    # device_client = IoTHubModuleClient.create_from_connection_string(conn_str)

    # Connect the client.
    await device_client.connect()

    # await device_client.get_storage_info_for_blob("fake_device", "fake_method_params")

    # get the storage sas
    blob_name = "fakeBlobName12"
    storage_info = await device_client.get_storage_info_for_blob(blob_name)

    # upload to blob
    connection = http.client.HTTPSConnection(hostname)
    connection.connect()
    # notify iot hub of blob upload result
    # await device_client.notify_upload_result(storage_blob_result)
    storage_blob_result = await storage_blob(storage_info)
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(storage_blob_result)
    connection.close()
    await device_client.notify_blob_upload_status(
        storage_info["correlationId"], True, 200, "fake status description"
    )

    # Finally, disconnect
    await device_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
