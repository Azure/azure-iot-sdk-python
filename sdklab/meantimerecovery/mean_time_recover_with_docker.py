# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import docker
import asyncio
import uuid
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import Message
from time import perf_counter
import threading
from multiprocessing import Value, Process


# Scenario based values
KEEP_ALIVE = 18
FACTOR_OF_KEEP_ALIVE = 0.5
KEEP_RUNNING = 10
KEEP_DEAD = int(KEEP_ALIVE * FACTOR_OF_KEEP_ALIVE)

MQTT_BROKER_RESTART_COUNT = 5
CONTAINER_NAME = "leaky-cauldron"

elapsed_times = []
container = None


def control_container(
    container_name, keep_running, keep_dead, restart_count, signal_to_quit, should_be_restarted=True
):
    global container

    print("Container started.")
    client = docker.from_env()
    container = client.containers.run(
        "mqtt-broker", detach=True, name=container_name, ports={"8883/tcp": 8883}
    )
    if should_be_restarted:
        kill_and_restart_container(
            keep_running=keep_running,
            keep_dead=keep_dead,
            restart_count=restart_count,
            signal_to_quit=signal_to_quit,
        )
    else:
        # This may need to be varied so that the last message can be SENT without an async task cancellation error.
        kill_container(keep_running=5)
        signal_to_quit.value = 1


def kill_and_restart_container(keep_running, keep_dead, restart_count, signal_to_quit):
    kill_container(keep_running)
    print("Container stopped.")
    start_timer(duration=keep_dead, restart_count=restart_count, signal_to_quit=signal_to_quit)


def kill_container(keep_running):
    print("Container will run for {} secs.".format(keep_running))
    container.stop(timeout=keep_running)
    container.remove()


def quitting_listener(quit_signal):
    while True:
        sig_val = quit_signal.value
        if sig_val == 1:
            print("Quitting...")
            break


async def send_test_message(device_client, restart_count):
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
        val = restart_count.value
        if val >= MQTT_BROKER_RESTART_COUNT:
            print(
                "Executed container restarts with telemetry {} times. Quitting telemetry task.".format(
                    val
                )
            )
            break


def start_timer(duration, restart_count, signal_to_quit):
    def timer_done():
        timer.cancel()
        print("{} secs is up. Cancelled timer. Container will be restarted again.".format(duration))
        restart_count.value = restart_count.value + 1
        # signal_to_quit.value = 0
        needs_restart = True
        if restart_count.value >= MQTT_BROKER_RESTART_COUNT:
            print(
                "Executed container restarts {} times. Container will not be restarted after the current loop. Quitting any future loop.".format(
                    restart_count.value
                )
            )
            # signal_to_quit.value = 1
            needs_restart = False
        control_container(
            CONTAINER_NAME,
            keep_running=KEEP_RUNNING,
            keep_dead=duration,
            restart_count=restart_count,
            signal_to_quit=signal_to_quit,
            should_be_restarted=needs_restart,
        )

    print("Container will be dead for {} secs.".format(duration))
    timer = threading.Timer(duration, timer_done)
    timer.start()


async def main():

    ca_cert = "self_cert_localhost.pem"
    certfile = open(ca_cert)
    root_ca_cert = certfile.read()

    # Inter process values
    times_container_restart = Value("i", 0)
    signal_to_quit = Value("i", 0)

    process_docker = Process(
        target=control_container,
        args=(CONTAINER_NAME, KEEP_RUNNING, KEEP_DEAD, times_container_restart, signal_to_quit),
    )
    process_docker.start()

    # Do not delete sleep from here. Server needs some time to start.
    await asyncio.sleep(5)
    conn_str = "HostName=localhost;DeviceId=devicemtr;SharedAccessKey=Zm9vYmFy"
    device_client = IoTHubDeviceClient.create_from_connection_string(
        conn_str, keep_alive=KEEP_ALIVE, server_verification_cert=root_ca_cert
    )

    await device_client.connect()

    send_message_task = asyncio.create_task(
        send_test_message(device_client, times_container_restart)
    )

    # Run the listener in the event loop
    # This can be a STDIN listener as well for user to indicate quitting.
    loop = asyncio.get_running_loop()
    finished_loops = loop.run_in_executor(None, quitting_listener, signal_to_quit)

    # Wait for count times to reach a certain number indicative of completion
    await finished_loops

    print("Count is " + str(times_container_restart.value))
    print(elapsed_times)

    process_docker.terminate()
    try:
        send_message_task.cancel()
    except asyncio.CancelledError:
        print("send message task is cancelled now")

    await device_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
