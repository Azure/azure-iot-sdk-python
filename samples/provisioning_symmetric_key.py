import asyncio
import logging
from azure.iot.device import (
    ProvisioningSession,
    MQTTConnectionDroppedError,
    MQTTConnectionFailedError,
)
import os


id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("PROVISIONING_REGISTRATION_ID")
symmetric_key = os.getenv("PROVISIONING_SYMMETRIC_KEY")


logging.basicConfig(level=logging.DEBUG)


async def main():
    try:
        async with ProvisioningSession(
            registration_id=registration_id,
            id_scope=id_scope,
            shared_access_key=symmetric_key,
        ) as session:
            print("Connected")
            result = await session.register(payload="optional registration payload")
            print("Finished provisioning")
            print(result)

    except MQTTConnectionDroppedError:
        # Connection has been lost.
        print("Dropped connection. Exiting")
    except MQTTConnectionFailedError:
        # Connection failed to be established.
        print("Could not connect. Exiting")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Exit application because user indicated they wish to exit.
        # This will have cancelled `main()` implicitly.
        print("User initiated exit. Exiting")
