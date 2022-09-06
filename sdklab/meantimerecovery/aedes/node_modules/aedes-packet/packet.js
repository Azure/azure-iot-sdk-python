'use strict'

function Packet (original, broker) {
  this.cmd = original.cmd || 'publish'
  this.brokerId = original.brokerId || (broker && broker.id)
  this.brokerCounter = original.brokerCounter || (broker ? (++broker.counter) : 0)
  this.topic = original.topic
  this.payload = original.payload || Buffer.alloc(0)
  this.qos = original.qos || 0
  this.retain = original.retain || false
  this.dup = original.dup || false
  // [MQTT-2.3.1-5]
  if (this.qos > 0 || this.cmd !== 'publish') {
    //  [MQTT-2.3.1-1]
    // This is packet identifier uniquely identifies a message as it flows between
    // client and broker. It is only relevant for QoS levels greater than 0
    this.messageId = undefined
  }
}

module.exports = Packet
