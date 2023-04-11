import asyncio
import logging
from azure.iot.device import ProvisioningSession
import os


provisioning_host = os.getenv("PROVISIONING_HOST")
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
    async with ProvisioningSession(
        provisioning_host=provisioning_host,
        registration_id=registration_id,
        id_scope=id_scope,
        shared_access_key=symmetric_key,
    ) as session:
        print("Connected")
        # async with asyncio.timeout(10):
        properties = {"Type": "Apple", "Sweet": "True"}
        fruit_a = Fruit("McIntosh", "Red", properties)
        # dic_props = '{"text": "hello from hogwarts"}'
        result = await session.register(payload=fruit_a)
        print(result)

    print("Out of session loop")


if __name__ == "__main__":
    asyncio.run(main())
