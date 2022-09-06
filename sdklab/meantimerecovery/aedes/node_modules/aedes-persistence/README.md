# aedes-persistence
![](https://github.com/moscajs/aedes-persistence/workflows/ci/badge.svg)
[![Dependencies Status](https://david-dm.org/moscajs/aedes-persistence/status.svg)](https://david-dm.org/moscajs/aedes-persistence)
[![devDependencies Status](https://david-dm.org/moscajs/aedes-persistence/dev-status.svg)](https://david-dm.org/moscajs/aedes-persistence?type=dev)
<br/>
[![Known Vulnerabilities](https://snyk.io/test/github/moscajs/aedes-persistence/badge.svg)](https://snyk.io/test/github/moscajs/aedes-persistence)
[![Coverage Status](https://coveralls.io/repos/moscajs/aedes-persistence/badge.svg?branch=master&service=github)](https://coveralls.io/github/moscajs/aedes-persistence?branch=master)
[![NPM version](https://img.shields.io/npm/v/aedes-persistence.svg?style=flat)](https://www.npmjs.com/package/aedes-persistence)
[![NPM downloads](https://img.shields.io/npm/dm/aedes-persistence.svg?style=flat)](https://www.npmjs.com/package/aedes-persistence)

The spec for an [Aedes](http://npm.im/aedes) persistence, with abstract
tests and a fast in-memory implementation.

* [Install](#install)
* [API](#api)
* [Implement another persistence](#implement)
* [License](#license)

<a name="install"></a>
## Install
To install aedes-persistence, simply use npm:

```
npm install aedes-persistence --save
```

<a name="api"></a>
## API

  * <a href="#constructor"><code><b>persistence()</b></code></a>
  * <a href="#storeRetained"><code>instance.<b>storeRetained()</b></code></a>
  * <a href="#createRetainedStream"><code>instance.<b>createRetainedStream()</b></code></a>
  * <a href="#createRetainedStreamCombi"><code>instance.<b>createRetainedStreamCombi()</b></code></a>
  * <a href="#addSubscriptions"><code>instance.<b>addSubscriptions()</b></code></a>
  * <a href="#removeSubscriptions"><code>instance.<b>removeSubscriptions()</b></code></a>
  * <a href="#subscriptionsByClient"><code>instance.<b>subscriptionsByClient()</b></code></a>
  * <a href="#countOffline"><code>instance.<b>countOffline()</b></code></a>
  * <a href="#subscriptionsByTopic"><code>instance.<b>subscriptionsByTopic()</b></code></a>
  * <a href="#cleanSubscriptions"><code>instance.<b>cleanSubscriptions()</b></code></a>
  * <a href="#outgoingEnqueue"><code>instance.<b>outgoingEnqueue()</b></code></a>
  * <a href="#outgoingEnqueueCombi"><code>instance.<b>outgoingEnqueueCombi()</b></code></a>
  * <a href="#outgoingUpdate"><code>instance.<b>outgoingUpdate()</b></code></a>
  * <a href="#outgoingClearMessageId"><code>instance.<b>outgoingClearMessageId()</b></code></a>
  * <a href="#outgoingStream"><code>instance.<b>outgoingStream()</b></code></a>
  * <a href="#incomingStorePacket"><code>instance.<b>incomingStorePacket()</b></code></a>
  * <a href="#incomingGetPacket"><code>instance.<b>incomingGetPacket()</b></code></a>
  * <a href="#incomingDelPacket"><code>instance.<b>incomingDelPacket()</b></code></a>
  * <a href="#putWill"><code>instance.<b>putWill()</b></code></a>
  * <a href="#getWill"><code>instance.<b>getWill()</b></code></a>
  * <a href="#delWill"><code>instance.<b>delWill()</b></code></a>
  * <a href="#streamWill"><code>instance.<b>streamWill()</b></code></a>
  * <a href="#getClientList"><code>instance.<b>getClientList()</b></code></a>
  * <a href="#destroy"><code>instance.<b>destroy()</b></code></a>

-------------------------------------------------------
<a name="constructor"></a>
### persistence([opts])

Creates a new instance of a persistence, that is already ready to
operate. The default implementation is in-memory only.

-------------------------------------------------------
<a name="storeRetained"></a>
### instance.storeRetained(packet, callback(err))

Store a retained message, calls the callback when it was saved.

-------------------------------------------------------
<a name="createRetainedStream"></a>
### instance.createRetainedStream(pattern)

Return a stream that will load all retained messages matching the given
pattern (according to the MQTT spec) asynchronously. Deprecated.

-------------------------------------------------------
<a name="createRetainedStreamCombi"></a>
### instance.createRetainedStreamCombi(patterns)

Return a stream that will load all retained messages matching given
patterns (according to the MQTT spec) asynchronously.

-------------------------------------------------------
<a name="addSubscriptions"></a>
### instance.addSubscriptions(client, subscriptions, callback(err, client))

Add the given offline subscriptions for the given
[Client](https://github.com/moscajs/aedes#client). The client __must__
have connected with `clean: false`, as this is not checked here.
This is called when a client issue a SUBSCRIBE packet.

`subscriptions` is in the same format of the `subscribe` property in the
[SUBSCRIBE](https://github.com/mqttjs/mqtt-packet#subscribe) packet:

```js
[{
  topic: 'hello/world',
  qos: 1,
}, {
  topic: 'hello/#',
  qos: 2,
}]
```

-------------------------------------------------------
<a name="removeSubscriptions"></a>
### instance.removeSubscriptions(client, subscriptions, callback(err, client))

The inverse of [`addSubscriptions`](#addSubscriptions) but subscriptions is an array of topic names.

-------------------------------------------------------
<a name="subscriptionsByClient"></a>
### instance.subscriptionsByClient(client, callback(err, subscriptions, client))

Returns all the offline subscriptions for the given client. Called when
a client with `clean: false` connects to restore its subscriptions.

`subscriptions` is in the same format of the `subscribe` property in the
[SUBSCRIBE](https://github.com/mqttjs/mqtt-packet#subscribe) packet:

```js
[{
  topic: 'hello/world',
  qos: 1,
}, {
  topic: 'hello/#',
  qos: 2,
}]
```

-------------------------------------------------------
<a name="countOffline"></a>
### instance.countOffline(cb(err, numOfSubscriptions, numOfClients))

Returns the number of offline subscriptions and the number of offline
clients.

-------------------------------------------------------
<a name="subscriptionsByTopic"></a>
### instance.subscriptionsByTopic(pattern, callback(err, subscriptions))

Returns all the offline subscriptions matching the given pattern. Called when
a PUBLISH with `qos: 1` or `qos: 2` is received.

The subscriptions are in the format:

```js
{
  clientId: client.id,
  topic: sub.topic,
  qos: sub.qos
}
```

-------------------------------------------------------
<a name="cleanSubscriptions"></a>
### instance.cleanSubscriptions(client, callback(err, client))

Removes all offline subscriptions for a given client.

-------------------------------------------------------
<a name="outgoingEnqueue"></a>
### instance.outgoingEnqueue(subscription, packet, callback(err))

Enqueue a potentially offline delivery. `subscription` is one of the
objects returned by [`subscriptionsByTopic`](#subscriptionsByTopic). Deprecated.

-------------------------------------------------------
<a name="outgoingEnqueueCombi"></a>
### instance.outgoingEnqueueCombi(subscriptions, packet, callback(err))

Enqueue a potentially offline delivery. `subscriptions` is the whole subscriptions
objects returned by [`subscriptionsByTopic`](#subscriptionsByTopic).

-------------------------------------------------------
<a name="outgoingUpdate"></a>
### instance.outgoingUpdate(client, packet, callback(err))

Called before a (potentially) offline packet is delivered, the caller
should update the `packet.messageId` before updating.

-------------------------------------------------------
<a name="outgoingClearMessageId"></a>
### instance.outgoingClearMessageId(client, packet, callback(err, packet))

Removes a packet with the given `messageId` (passing a PUBACK is ok)
from the persistence. Passes back original packet to the callback.

-------------------------------------------------------
<a name="outgoingStream"></a>
### instance.outgoingStream(client)

Return a stream that will load all offline messages for the given client asynchronously.

-------------------------------------------------------
<a name="incomingStorePacket"></a>
### instance.incomingStorePacket(client, packet, cb(err, packet))

Store an incoming packet for the given client. Used for QoS 2.

-------------------------------------------------------
<a name="incomingGetPacket"></a>
### instance.incomingGetPacket(client, packet, cb(err, packet))

Retrieve an incoming packet with the same `messageId` for the given client. Used for QoS 2.

-------------------------------------------------------
<a name="incomingDelPacket"></a>
### instance.incomingDelPacket(client, packet, cb(err, packet))

Deletes incoming packet with the same `messageId` for the given client. Used for QoS 2.

-------------------------------------------------------
<a name="putWill"></a>
### instance.putWill(client, packet, cb(err))

Stores the will of a client. Used to support multi-broker environments
and to not lose wills in case of a crash.

-------------------------------------------------------
<a name="getWill"></a>
### instance.getWill(client, packet, cb(err))

Retrieves the will of a client. Used to support multi-broker environments
and to not lose wills in case of a crash.

-------------------------------------------------------
<a name="delWill"></a>
### instance.delWill(client, packet, cb(err))

Removes the will of a client. Used to support multi-broker environments
and to not lose wills in case of a crash.

-------------------------------------------------------
<a name="streamWill"></a>
### instance.streamWill(brokers)

Streams all the wills for the given brokers. The brokers are in the
format:

```js
{
  mybroker: {
    brokerId: 'mybroker'
  }
}
```

-------------------------------------------------------
<a name="getCLientList"></a>
### instance.getClientList(topic)

Returns a stream which has all the clientIds subscribed to the
specified topic

<a name="destroy"></a>
### instance.destroy(cb(err))

Destroy current persistence. Use callback `cb(err)` to catch errors if any

<a name="implement"></a>
## Implement another persistence

A persistence needs to pass all tests defined in
[./abstract.js](./abstract.js). You can import and use that test suite
in the following manner:

```js
var test = require('tape').test
var myperst = require('./')
var abs = require('aedes-persistence/abstract')

abs({
  test: test,
  persistence: myperst
})
```

If you require some async stuff before returning, a callback is also
supported:

```js
var test = require('tape').test
var myperst = require('./')
var abs = require('aedes-persistence/abstract')
var clean = require('./clean') // invented module

abs({
  test: test,
  buildEmitter: require('mymqemitter'), // optional
  persistence: function build (cb) {
    clean(function (err) {
      cb(err, myperst())
    })
  }
})
```

## Collaborators

* [__Gnought__](https://github.com/gnought)

## License

MIT
