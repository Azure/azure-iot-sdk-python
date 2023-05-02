import asyncio
import logging
from azure.iot.device import ProvisioningSession, MQTTError, MQTTConnectionFailedError
import os


id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("PROVISIONING_REGISTRATION_ID")
symmetric_key = os.getenv("PROVISIONING_SYMMETRIC_KEY")


logging.basicConfig(level=logging.DEBUG)


class Fruit(object):
    def __init__(self, first_name, last_name, dict_of_stuff):
        self.first_name = first_name
        self.last_name = last_name
        self.props = dict_of_stuff


async def main():
    try:
        async with ProvisioningSession(
            registration_id=registration_id,
            id_scope=id_scope,
            shared_access_key=symmetric_key,
        ) as session:
            print("Connected")
            properties = {"Type": "Apple", "Sweet": "True"}
            fruit_a = Fruit("McIntosh", "Red", properties)
            result = await session.register(payload=fruit_a)
            print("Finished provisioning")
            print(result)

    except MQTTError:
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
