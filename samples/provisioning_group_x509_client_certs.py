import asyncio
import logging
from azure.iot.device import (
    ProvisioningSession,
    MQTTConnectionDroppedError,
    MQTTConnectionFailedError,
)
import os
import ssl

id_scope = os.getenv("PROVISIONING_IDSCOPE")

logging.basicConfig(level=logging.DEBUG)


def create_default_context(certfile, keyfile, password):
    ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.check_hostname = True
    ssl_context.load_default_certs()
    ssl_context.load_cert_chain(certfile=certfile, keyfile=keyfile, password=password)
    return ssl_context


async def run_dps(registration_id, certfile, keyfile, password):
    try:
        ssl_context = create_default_context(certfile, keyfile, password)
        async with ProvisioningSession(
            registration_id=registration_id,
            id_scope=id_scope,
            ssl_context=ssl_context,
        ) as session:
            print("Connected")
            result = await session.register()
            print("Finished provisioning")
            print(result)

    except MQTTConnectionDroppedError as me:
        # Connection has been lost.
        print("Dropped connection. Exiting")
        raise Exception("Dropped connection") from me
    except MQTTConnectionFailedError as mce:
        # Connection failed to be established.
        print("Could not connect. Exiting")
        raise Exception("Could not connect. Exiting") from mce


async def main():
    print("Starting group provisioning sample")
    print("Press Ctrl-C to exit")

    try:
        # These are all fake file names and password and to  be replaced as per scenario.
        await asyncio.gather(
            run_dps("devicemydomain1", "device_cert1.pem", "device_key1.pem", "devicepass"),
            run_dps("devicemydomain2", "device_cert2.pem", "device_key2.pem", "devicepass"),
            run_dps("devicemydomain3", "device_cert3.pem", "device_key3.pem", "devicepass"),
        )
    except Exception as e:
        print("Caught exception while trying to run dps")
        print(e.__cause__)
    finally:
        print("Finishing sample")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Exit application because user indicated they wish to exit.
        # This will have cancelled `main()` implicitly.
        print("User initiated exit. Exiting")
