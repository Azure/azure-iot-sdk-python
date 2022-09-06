import type { Brokers, Client, Subscription } from 'aedes';
import type { AedesPacket } from 'aedes-packet';
import type { QoS } from 'mqtt-packet';
import type { Readable } from 'stream';
import { expectType } from 'tsd';
import aedesMemoryPersistence, {
  AedesMemoryPersistence,
  AedesPersistenceSubscription,
  CallbackError,
  WillPacket,
} from '.';

expectType<AedesMemoryPersistence>(aedesMemoryPersistence());

expectType<void>(
  aedesMemoryPersistence().storeRetained(
    {
      brokerId: '',
      brokerCounter: 1,
      cmd: 'publish',
      qos: 0,
      dup: false,
      retain: false,
      topic: 'test',
      payload: 'test',
    },
    (err: CallbackError) => {}
  )
);

expectType<void>(
  aedesMemoryPersistence().addSubscriptions(
    {} as Client,
    [] as Subscription[],
    (err: CallbackError) => {}
  )
);

expectType<void>(
  aedesMemoryPersistence().removeSubscriptions(
    {} as Client,
    [] as Subscription[],
    (err: CallbackError) => {}
  )
);

expectType<void>(
  aedesMemoryPersistence().subscriptionsByClient(
    {} as Client,
    (
      error: CallbackError,
      subs: { topic: string; qos: QoS }[],
      client: Client
    ) => {}
  )
);

expectType<void>(
  aedesMemoryPersistence().countOffline(
    (
      error: CallbackError,
      subscriptionsCount: number,
      clientsCount: number
    ) => {}
  )
);

expectType<void>(
  aedesMemoryPersistence().subscriptionsByTopic(
    'pattern',
    (error: CallbackError, subs: AedesPersistenceSubscription[]) => {}
  )
);

expectType<void>(
  aedesMemoryPersistence().cleanSubscriptions(
    {} as Client,
    (error: CallbackError, client: Client) => {}
  )
);

expectType<void>(
  aedesMemoryPersistence().outgoingEnqueue(
    { clientId: '' },
    {} as AedesPacket,
    (error: CallbackError) => {}
  )
);

expectType<void>(
  aedesMemoryPersistence().outgoingEnqueueCombi(
    [{ clientId: '' }],
    {} as AedesPacket,
    (error: CallbackError) => {}
  )
);

expectType<void>(
  aedesMemoryPersistence().outgoingUpdate(
    {} as Client,
    {} as AedesPacket,
    (error: CallbackError, client: Client, packet: AedesPacket) => {}
  )
);

expectType<void>(
  aedesMemoryPersistence().outgoingClearMessageId(
    {} as Client,
    {} as AedesPacket,
    (error: CallbackError, packet?: AedesPacket) => {}
  )
);

expectType<Readable>(aedesMemoryPersistence().outgoingStream({} as Client));

expectType<void>(
  aedesMemoryPersistence().incomingStorePacket(
    {} as Client,
    {} as AedesPacket,
    (error: CallbackError) => {}
  )
);

expectType<void>(
  aedesMemoryPersistence().incomingGetPacket(
    {} as Client,
    {} as AedesPacket,
    (error: CallbackError, packet: AedesPacket) => {}
  )
);

expectType<void>(
  aedesMemoryPersistence().incomingDelPacket(
    {} as Client,
    {} as AedesPacket,
    (error: CallbackError) => {}
  )
);

expectType<void>(
  aedesMemoryPersistence().putWill(
    {} as Client,
    {} as AedesPacket,
    (error: CallbackError, client: Client) => {}
  )
);

expectType<void>(
  aedesMemoryPersistence().getWill(
    {} as Client,
    (error: CallbackError, will: WillPacket, client: Client) => {}
  )
);

expectType<void>(
  aedesMemoryPersistence().delWill(
    {} as Client,
    (error: CallbackError, will: WillPacket, client: Client) => {}
  )
);

expectType<Readable>(aedesMemoryPersistence().streamWill({} as Brokers));

expectType<Readable>(aedesMemoryPersistence().getClientList('topic'));

expectType<void>(aedesMemoryPersistence().destroy());

expectType<void>(aedesMemoryPersistence().destroy(() => {}));
