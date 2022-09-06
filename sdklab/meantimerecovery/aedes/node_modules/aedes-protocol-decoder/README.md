# aedes-protocol-decoder

![](https://github.com/moscajs/aedes-protocol-decoder/workflows/ci/badge.svg)
[![Dependencies Status](https://david-dm.org/moscajs/aedes-protocol-decoder/status.svg)](https://david-dm.org/moscajs/aedes-protocol-decoder)
[![devDependencies Status](https://david-dm.org/moscajs/aedes-protocol-decoder/dev-status.svg)](https://david-dm.org/moscajs/aedes-protocol-decoder?type=dev)
<br/>
[![Known Vulnerabilities](https://snyk.io/test/github/moscajs/aedes-protocol-decoder/badge.svg)](https://snyk.io/test/github/moscajs/aedes-protocol-decoder)
[![Coverage Status](https://coveralls.io/repos/moscajs/aedes-protocol-decoder/badge.svg?branch=master&service=github)](https://coveralls.io/github/moscajs/aedes-protocol-decoder?branch=master)
[![NPM version](https://img.shields.io/npm/v/aedes-protocol-decoder.svg?style=flat)](https://www.npmjs.com/package/aedes-protocol-decoder)
[![NPM downloads](https://img.shields.io/npm/dm/aedes-protocol-decoder.svg?style=flat)](https://www.npmjs.com/package/aedes-protocol-decoder)


[![js-standard-style](https://cdn.rawgit.com/feross/standard/master/badge.svg)](https://github.com/feross/standard)

Protocol decoder for Aedes MQTT Broker

The purpose of this module is to be used inside [aedes](https://github.com/moscajs/aedes) `decodeProtocol` hook, which is called when aedes instance receives a first valid buffer from client ( before CONNECT packet). The client object state is in default and its connected state is false. 
The function extract socket details and if aedes `trustProxy` option is set to true, it will first parse http headers (x-real-ip | x-forwarded-for) and proxy protocol (v1 and v2) to retrieve information in client.connDetails.

The function `protocolDecoder` returns [ConnectionDetails](./types/index.d.ts), if the object contains data property, it will be parsed as an mqtt-packet.

## Install

```bash
npm install aedes-protocol-decoder --save
```

## Example 

```js
var aedes = require('aedes')
var { protocolDecoder } = require('aedes-protocol-decoder')
var net = require('net')
var port = 1883

var broker = aedes({
	decodeProtocol: function (client, buffer) {
	  var proto = protocolDecoder(client, buffer)
	  return proto
	},
	preConnect: function (client, done) {
	  if (client.connDetails && client.connDetails.ipAddress) {
	    client.ip = client.connDetails.ipAddress
	  }
	  return done(null, true)
	},
	trustProxy: true
})

var server = net.createServer(broker.handle)

server.listen(port, function () {
  console.log('server listening on port', port)
})


```

## License

MIT
