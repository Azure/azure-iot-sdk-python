'use strict'

var test = require('tape').test
var aedes = require('aedes')
var http = require('http')
var ws = require('websocket-stream')
var mqtt = require('mqtt')
var mqttPacket = require('mqtt-packet')
var net = require('net')
var proxyProtocol = require('proxy-protocol-js')
var protocolDecoder = require('./lib/protocol-decoder')

// test ipAddress property presence when trustProxy is enabled
test('tcp clients have access to the ipAddress from the socket', function (t) {
  t.plan(2)

  var port = 4883
  var broker = aedes({
    decodeProtocol: function (client, buffer) {
      var proto = protocolDecoder(client, buffer)
      return proto
    },
    preConnect: function (client, done) {
      if (client && client.connDetails && client.connDetails.ipAddress) {
        client.ip = client.connDetails.ipAddress
        t.equal('::ffff:127.0.0.1', client.ip)
      } else {
        t.fail('no ip address present')
      }
      done(null, true)
      setImmediate(finish)
    },
    trustProxy: true
  })

  var server = net.createServer(broker.handle)
  server.listen(port, function (err) {
    t.error(err, 'no error')
  })

  var client = mqtt.connect({
    port,
    keepalive: 0,
    clientId: 'mqtt-client',
    clean: false
  })

  function finish () {
    client.end()
    broker.close()
    server.close()
    t.end()
  }
})

test('tcp proxied (protocol v1) clients have access to the ipAddress(v4)', function (t) {
  t.plan(2)

  var port = 4883
  var clientIp = '192.168.0.140'
  var packet = {
    cmd: 'connect',
    protocolId: 'MQIsdp',
    protocolVersion: 3,
    clean: true,
    clientId: 'my-client-proxyV1',
    keepalive: 0
  }

  var buf = mqttPacket.generate(packet)
  var src = new proxyProtocol.Peer(clientIp, 12345)
  var dst = new proxyProtocol.Peer('127.0.0.1', port)
  var protocol = new proxyProtocol.V1BinaryProxyProtocol(
    proxyProtocol.INETProtocol.TCP4,
    src,
    dst,
    buf
  ).build()

  var broker = aedes({
    decodeProtocol: function (client, buffer) {
      var proto = protocolDecoder(client, buffer)
      return proto
    },
    preConnect: function (client, done) {
      if (client.connDetails && client.connDetails.ipAddress) {
        client.ip = client.connDetails.ipAddress
        t.equal(clientIp, client.ip)
      } else {
        t.fail('no ip address present')
      }
      done(null, true)
      setImmediate(finish)
    },
    trustProxy: true
  })

  var server = net.createServer(broker.handle)
  server.listen(port, function (err) {
    t.error(err, 'no error')
  })

  var client = net.connect({
    port,
    timeout: 0
  }, function () {
    client.write(protocol)
  })

  function finish () {
    client.end()
    broker.close()
    server.close()
    t.end()
  }
})

test('tcp proxied (protocol v2) clients have access to the ipAddress(v4)', function (t) {
  t.plan(2)

  var port = 4883
  var clientIp = '192.168.0.140'
  var packet = {
    cmd: 'connect',
    protocolId: 'MQTT',
    protocolVersion: 4,
    clean: true,
    clientId: 'my-client-proxyV2'
  }

  var protocol = new proxyProtocol.V2ProxyProtocol(
    proxyProtocol.Command.LOCAL,
    proxyProtocol.TransportProtocol.DGRAM,
    new proxyProtocol.IPv4ProxyAddress(
      proxyProtocol.IPv4Address.createFrom(clientIp.split('.')),
      12345,
      proxyProtocol.IPv4Address.createFrom([127, 0, 0, 1]),
      port
    ),
    mqttPacket.generate(packet)
  ).build()

  var broker = aedes({
    decodeProtocol: function (client, buffer) {
      var proto = protocolDecoder(client, buffer)
      return proto
    },
    preConnect: function (client, done) {
      if (client.connDetails && client.connDetails.ipAddress) {
        client.ip = client.connDetails.ipAddress
        t.equal(clientIp, client.ip)
      } else {
        t.fail('no ip address present')
      }
      done(null, true)
      setImmediate(finish)
    },
    trustProxy: true
  })

  var server = net.createServer(broker.handle)
  server.listen(port, function (err) {
    t.error(err, 'no error')
  })

  var client = net.createConnection(
    {
      port,
      timeout: 0
    }, function () {
      client.write(Buffer.from(protocol))
    }
  )

  function finish () {
    client.end()
    broker.close()
    server.close()
    t.end()
  }
})

test('tcp proxied (protocol v2) clients have access to the ipAddress(v6)', function (t) {
  t.plan(2)

  var port = 4883
  var clientIpArray = [0, 0, 0, 0, 0, 0, 0, 0, 255, 255, 192, 168, 1, 128]
  var clientIp = '::ffff:c0a8:180:'
  var packet = {
    cmd: 'connect',
    protocolId: 'MQTT',
    protocolVersion: 4,
    clean: true,
    clientId: 'my-client-proxyV2'
  }

  var protocol = new proxyProtocol.V2ProxyProtocol(
    proxyProtocol.Command.PROXY,
    proxyProtocol.TransportProtocol.STREAM,
    new proxyProtocol.IPv6ProxyAddress(
      proxyProtocol.IPv6Address.createFrom(clientIpArray),
      12345,
      proxyProtocol.IPv6Address.createWithEmptyAddress(),
      port
    ),
    mqttPacket.generate(packet)
  ).build()

  var broker = aedes({
    decodeProtocol: function (client, buffer) {
      var proto = protocolDecoder(client, buffer)
      return proto
    },
    preConnect: function (client, done) {
      if (client.connDetails && client.connDetails.ipAddress) {
        client.ip = client.connDetails.ipAddress
        t.equal(clientIp, client.ip)
      } else {
        t.fail('no ip address present')
      }
      done(null, true)
      setImmediate(finish)
    },
    trustProxy: true
  })

  var server = net.createServer(broker.handle)
  server.listen(port, function (err) {
    t.error(err, 'no error')
  })

  var client = net.createConnection(
    {
      port,
      timeout: 0
    }, function () {
      client.write(Buffer.from(protocol))
    }
  )

  function finish () {
    client.end()
    broker.close()
    server.close()
    t.end()
  }
})

test('websocket clients have access to the ipAddress from the socket (if no ip header)', function (t) {
  t.plan(2)

  var clientIp = '::ffff:127.0.0.1'
  var port = 4883
  var broker = aedes({
    decodeProtocol: function (client, buffer) {
      var proto = protocolDecoder(client, buffer)
      return proto
    },
    preConnect: function (client, done) {
      if (client.connDetails && client.connDetails.ipAddress) {
        client.ip = client.connDetails.ipAddress
        t.equal(clientIp, client.ip)
      } else {
        t.fail('no ip address present')
      }
      done(null, true)
      setImmediate(finish)
    },
    trustProxy: true
  })

  var server = http.createServer()
  ws.createServer({
    server: server
  }, broker.handle)

  server.listen(port, function (err) {
    t.error(err, 'no error')
  })

  var client = mqtt.connect(`ws://localhost:${port}`)

  function finish () {
    broker.close()
    server.close()
    client.end()
    t.end()
  }
})

test('websocket proxied clients have access to the ipAddress from x-real-ip header', function (t) {
  t.plan(2)

  var clientIp = '192.168.0.140'
  var port = 4883
  var broker = aedes({
    decodeProtocol: function (client, buffer) {
      var proto = protocolDecoder(client, buffer)
      return proto
    },
    preConnect: function (client, done) {
      if (client.connDetails && client.connDetails.ipAddress) {
        client.ip = client.connDetails.ipAddress
        t.equal(clientIp, client.ip)
      } else {
        t.fail('no ip address present')
      }
      done(null, true)
      setImmediate(finish)
    },
    trustProxy: true
  })

  var server = http.createServer()
  ws.createServer({
    server: server
  }, broker.handle)

  server.listen(port, function (err) {
    t.error(err, 'no error')
  })

  var client = mqtt.connect(`ws://localhost:${port}`, {
    wsOptions: {
      headers: {
        'X-Real-Ip': clientIp
      }
    }
  })

  function finish () {
    broker.close()
    server.close()
    client.end()
    t.end()
  }
})

test('websocket proxied clients have access to the ipAddress from x-forwarded-for header', function (t) {
  t.plan(2)

  var clientIp = '192.168.0.140'
  var port = 4883
  var broker = aedes({
    decodeProtocol: function (client, buffer) {
      var proto = protocolDecoder(client, buffer)
      return proto
    },
    preConnect: function (client, done) {
      if (client.connDetails && client.connDetails.ipAddress) {
        client.ip = client.connDetails.ipAddress
        t.equal(clientIp, client.ip)
      } else {
        t.fail('no ip address present')
      }
      done(null, true)
      setImmediate(finish)
    },
    trustProxy: true
  })

  var server = http.createServer()
  ws.createServer({
    server: server
  }, broker.handle)

  server.listen(port, function (err) {
    t.error(err, 'no error')
  })

  var client = mqtt.connect(`ws://localhost:${port}`, {
    wsOptions: {
      headers: {
        'X-Forwarded-For': clientIp
      }
    }
  })

  function finish () {
    broker.close()
    server.close()
    client.end()
    t.end()
  }
})

test('tcp proxied (protocol v1) clients buffer contains MQTT packet and proxy header', function (t) {
  t.plan(3)

  var brokerPort = 4883
  var proxyPort = 4884
  var clientIp = '192.168.0.140'
  var packet = {
    cmd: 'connect',
    protocolId: 'MQIsdp',
    protocolVersion: 3,
    clean: true,
    clientId: 'my-client-proxyV1',
    keepalive: 0
  }

  var buf = mqttPacket.generate(packet)
  var src = new proxyProtocol.Peer(clientIp, 12345)
  var dst = new proxyProtocol.Peer('127.0.0.1', proxyPort)

  var broker = aedes({
    decodeProtocol: function (client, buff) {
      var proto = protocolDecoder(client, buff)
      if (proto.data) {
        t.equal(proto.data.toString(), buf.toString())
      } else {
        t.fail('no MQTT packet extracted from TCP buffer')
      }
      return proto
    },
    trustProxy: true
  })

  broker.on('clientDisconnect', function (client) {
    // console.log('onClientDisconnect', client.id)
    setImmediate(finish)
  })

  var server = net.createServer(broker.handle)
  server.listen(brokerPort, function (err) {
    t.error(err, 'no error')
  })

  var proxyServer = net.createServer()
  proxyServer.listen(proxyPort, function (err) {
    t.error(err, 'no error')
  })

  var proxyClient

  proxyServer.on('connection', function (socket) {
    socket.on('end', function (data) {
      proxyClient.end(data, function () {
        proxyClient.connected = false
      })
    })

    socket.on('data', function (data) {
      if (proxyClient && proxyClient.connected) {
        proxyClient.write(data)
      } else {
        var protocol = new proxyProtocol.V1BinaryProxyProtocol(
          proxyProtocol.INETProtocol.TCP4,
          src,
          dst,
          data
        ).build()
        proxyClient = net.connect({
          port: brokerPort,
          timeout: 0
        }, function () {
          proxyClient.write(protocol, function () {
            proxyClient.connected = true
          })
        })
      }
    })
  })

  var client = net.connect({
    port: proxyPort,
    timeout: 200
  }, function () {
    client.write(buf)
  })

  client.on('timeout', function () {
    client.end(mqttPacket.generate({ cmd: 'disconnect' }))
  })

  function finish () {
    broker.close()
    server.close()
    proxyServer.close()
    t.end()
  }
})
