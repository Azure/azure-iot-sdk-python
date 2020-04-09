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
from azure.core.exceptions import ResourceExistsError
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

"""
Welcome to the Upload to Blob sample for the Azure IoT Device Library for Python. To use this sample you must have azure.storage.blob installed in your python environment.
To do this, you can run:

    $ pip install azure.storage.blob

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

IOTHUB_HOSTNAME = os.getenv("IOTHUB_HOSTNAME")
IOTHUB_DEVICE_ID = os.getenv("IOTHUB_DEVICE_ID")

X509_CERT_FILE = os.getenv("X509_CERT_FILE")
X509_KEY_FILE = os.getenv("X509_KEY_FILE")
X509_PASS_PHRASE = os.getenv("PASS_PHRASE")

# Host is in format "<iothub name>.azure-devices.net"


async def upload_via_storage_blob(blob_info):
    """ Helper function written to perform Storage Blob V12 Upload Tasks

    Arguments:
    blob_info - an object containing the information needed to generate a sas_url for creating a blob client

    Returns:
    status of blob upload operation, in the storage provided strcuture.
    """

    print("Azure Blob storage v12 - Python quickstart sample")
    sas_url = "https://{}/{}/{}{}".format(
        blob_info["hostName"],
        blob_info["containerName"],
        blob_info["blobName"],
        blob_info["sasToken"],
    )
    blob_client = BlobClient.from_blob_url(sas_url)

    # The following file code can be replaced with simply a sample file in a directory.

    # Create a file in local Documents directory to upload and download
    local_file_name = "data/quickstart" + str(uuid.uuid4()) + ".txt"
    filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), local_file_name)

    # Write text to the file
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    file = open(filename, "w")
    file.write("Hello, World!")
    file.close()

    # Perform the actual upload for the data.
    print("\nUploading to Azure Storage as blob:\n\t" + local_file_name)
    # # Upload the created file
    with open(filename, "rb") as data:
        result = blob_client.upload_blob(data)

    return result


async def main():
    hostname = IOTHUB_HOSTNAME
    device_id = IOTHUB_DEVICE_ID
    x509 = X509(cert_file=X509_CERT_FILE, key_file=X509_KEY_FILE, pass_phrase=X509_PASS_PHRASE)

    # Create the Device Client.
    device_client = IoTHubDeviceClient.create_from_x509_certificate(
        hostname=hostname, device_id=device_id, x509=x509
    )

    # Connect the client.
    await device_client.connect()

    # get the Storage SAS information from IoT Hub.
    blob_name = "fakeBlobName12"
    storage_info = await device_client.get_storage_info_for_blob(blob_name)
    result = {"status_code": -1, "status_description": "N/A"}

    # Using the Storage Blob V12 API, perform the blob upload.
    try:
        upload_result = await upload_via_storage_blob(storage_info)
        if upload_result.error_code:
            result = {
                "status_code": upload_result.error_code,
                "status_description": "Storage Blob Upload Error",
            }
        else:
            result = {"status_code": 200, "status_description": ""}
    except ResourceExistsError as ex:
        if ex.status_code:
            result = {"status_code": ex.status_code, "status_description": ex.reason}
        else:
            print("Failed with Exception: {}", ex)
            result = {"status_code": 400, "status_description": ex.message}

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(result)
    if result["status_code"] == 200:
        await device_client.notify_blob_upload_status(
            storage_info["correlationId"], True, result["status_code"], result["status_description"]
        )
    else:
        await device_client.notify_blob_upload_status(
            storage_info["correlationId"],
            False,
            result["status_code"],
            result["status_description"],
        )

    # Finally, disconnect
    await device_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
