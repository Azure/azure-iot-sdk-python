'use strict'

var { test } = require('tap')
var Packet = require('./')

test('Packet defaults - PUBLISH, QoS 0', function (t) {
  var instance = new Packet({})
  t.equal(instance.cmd, 'publish')
  t.equal(instance.brokerId, undefined)
  t.equal(instance.brokerCounter, 0)
  t.equal(instance.topic, undefined)
  t.deepEqual(instance.payload, Buffer.alloc(0))
  t.equal(instance.qos, 0)
  t.equal(instance.dup, false)
  t.equal(instance.retain, false)
  t.notOk(Object.prototype.hasOwnProperty.call(instance, 'messageId'))
  t.end()
})

test('Packet defaults - PUBREL, QoS 0', function (t) {
  var instance = new Packet({ cmd: 'pubrel' })
  t.equal(instance.cmd, 'pubrel')
  t.equal(instance.brokerId, undefined)
  t.equal(instance.brokerCounter, 0)
  t.equal(instance.topic, undefined)
  t.deepEqual(instance.payload, Buffer.alloc(0))
  t.equal(instance.qos, 0)
  t.equal(instance.dup, false)
  t.equal(instance.retain, false)
  t.ok(Object.prototype.hasOwnProperty.call(instance, 'messageId'))
  t.equal(instance.messageId, undefined)
  t.end()
})

test('Packet defaults - PUBLISH, QoS 1', function (t) {
  var instance = new Packet({ qos: 1 })
  t.equal(instance.cmd, 'publish')
  t.equal(instance.brokerId, undefined)
  t.equal(instance.brokerCounter, 0)
  t.equal(instance.topic, undefined)
  t.deepEqual(instance.payload, Buffer.alloc(0))
  t.equal(instance.qos, 1)
  t.equal(instance.dup, false)
  t.equal(instance.retain, false)
  t.ok(Object.prototype.hasOwnProperty.call(instance, 'messageId'))
  t.equal(instance.messageId, undefined)
  t.end()
})

test('Packet defaults - PUBLISH, dup=true', function (t) {
  var instance = new Packet({ dup: true })
  t.equal(instance.cmd, 'publish')
  t.equal(instance.brokerId, undefined)
  t.equal(instance.brokerCounter, 0)
  t.equal(instance.topic, undefined)
  t.deepEqual(instance.payload, Buffer.alloc(0))
  t.equal(instance.qos, 0)
  t.equal(instance.dup, true)
  t.equal(instance.retain, false)
  t.equal(instance.messageId, undefined)
  t.end()
})

test('Packet copies over most data', function (t) {
  var original = {
    cmd: 'pubrel',
    brokerId: 'A56c',
    brokerCounter: 42,
    topic: 'hello',
    payload: 'world',
    qos: 2,
    dup: true,
    retain: true,
    messageId: 24
  }
  var instance = new Packet(original)
  var expected = {
    cmd: 'pubrel',
    brokerId: 'A56c',
    brokerCounter: 42,
    topic: 'hello',
    payload: 'world',
    qos: 2,
    dup: true,
    retain: true
  }

  t.ok(Object.prototype.hasOwnProperty.call(instance, 'messageId'))
  t.equal(instance.messageId, undefined)
  delete instance.messageId
  t.deepEqual(instance, expected)
  t.end()
})

test('Packet fills in broker data', function (t) {
  var broker = {
    id: 'A56c',
    counter: 41
  }
  var original = {
    cmd: 'pubrel',
    topic: 'hello',
    payload: 'world',
    qos: 2,
    retain: true,
    messageId: 24
  }
  var instance = new Packet(original, broker)
  var expected = {
    cmd: 'pubrel',
    brokerId: 'A56c',
    brokerCounter: 42,
    topic: 'hello',
    payload: 'world',
    qos: 2,
    dup: false,
    retain: true
  }

  t.ok(Object.prototype.hasOwnProperty.call(instance, 'messageId'))
  t.equal(instance.messageId, undefined)
  delete instance.messageId
  t.deepEqual(instance, expected)
  t.end()
})
