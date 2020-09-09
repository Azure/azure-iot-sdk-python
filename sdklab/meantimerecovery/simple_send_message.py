import asyncio
import uuid
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import Message
from time import perf_counter

elapsed_times = []


# define behavior for halting the application
def quitting_listener():
    while True:
        selection = input("Press Q to quit\n")
        if selection == "Q" or selection == "q":
            print("Quitting...")
            break


async def send_test_message(device_client):
    i = 0
    while True:
        print("sending message #" + str(i))
        msg = Message("test wind speed " + str(i))
        msg.message_id = uuid.uuid4()
        t_start = perf_counter()
        await device_client.send_message(msg)
        t_stop = perf_counter()
        elapsed_time = t_stop - t_start
        elapsed_times.append(elapsed_time)
        print("done sending message #" + str(i))
        i = i + 1
        await asyncio.sleep(3)


async def main():
    # Scenario based values
    keep_alive = 15

    conn_str = "HostName=localhost;DeviceId=devicemtr;SharedAccessKey=Zm9vYmFy"
    device_client = IoTHubDeviceClient.create_from_connection_string(
        conn_str, keep_alive=keep_alive
    )

    await device_client.connect()

    send_message_task = asyncio.create_task(send_test_message(device_client))

    # Run the listener in the event loop
    # This can be a STDIN listener as well for user to indicate quitting.
    loop = asyncio.get_running_loop()
    finished_loops = loop.run_in_executor(None, quitting_listener)

    # Wait for count times to reach a certain number indicative of completion
    await finished_loops

    print(elapsed_times)

    try:
        send_message_task.cancel()
    except asyncio.CancelledError:
        print("send message task is cancelled now")

    await device_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
