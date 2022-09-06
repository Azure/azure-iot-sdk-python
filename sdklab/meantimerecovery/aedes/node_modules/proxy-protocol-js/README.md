proxy-protocol-js [![CircleCI](https://circleci.com/gh/moznion/proxy-protocol-js.svg?style=svg)](https://circleci.com/gh/moznion/proxy-protocol-js) [![codecov](https://codecov.io/gh/moznion/proxy-protocol-js/branch/master/graph/badge.svg)](https://codecov.io/gh/moznion/proxy-protocol-js) [![NPM](https://nodei.co/npm/proxy-protocol-js.png?compact=true)](https://nodei.co/npm/proxy-protocol-js/)
==

A [PROXY protocol](http://www.haproxy.org/download/1.8/doc/proxy-protocol.txt) builder and parser for JavaScript.

Features
--

- Supports the features
  - building PROXY protocol payload
  - parsing PROXY protocol payload
  - identifying the PROXY protocol version
- Supports both of the version: V1 and V2 protocol
- Also supports TypeScript
- It doesn't requre the extra dependencies

Usage
--

See also [examples](./example) and TSDoc.

### Build (and identity the protocol version)

#### V1 protocol

```JavaScript
const proxyProtocol = require('proxy-protocol-js');

const src = new proxyProtocol.Peer('127.0.0.1', 12345);
const dst = new proxyProtocol.Peer('192.0.2.1', 54321);
const protocolText = new proxyProtocol.V1ProxyProtocol(
  proxyProtocol.INETProtocol.TCP4,
  src,
  dst,
).build();
console.log(protocolText); // => PROXY TCP4 127.0.0.1 192.0.2.1 12345 54321\r\n

const identifiedProtocolVersion = proxyProtocol.ProxyProtocolIdentifier.identify(protocolText);
console.log(identifiedProtocolVersion); // => proxyProtocol.ProxyProtocolVersion.V1 (= 0xx10)
```

#### V2 protocol

```JavaScript
const proxyProtocol = require('proxy-protocol-js');

const proto = new proxyProtocol.V2ProxyProtocol(
  proxyProtocol.Command.LOCAL,
  proxyProtocol.TransportProtocol.DGRAM,
  new proxyProtocol.IPv4ProxyAddress(
    proxyProtocol.IPv4Address.createFrom([127, 0, 0, 1]),
    12345,
    proxyProtocol.IPv4Address.createFrom([192, 0, 2, 1]),
    54321,
  ),
).build();
console.log(proto);

const identifiedProtocolVersion = proxyProtocol.ProxyProtocolIdentifier.identify(proto);
console.log(identifiedProtocolVersion); // => proxyProtocol.ProxyProtocolVersion.V2 (= 0x20)
```

### Parse

#### V1 protocol

```JavaScript
const proxyProtocol = require('proxy-protocol');

const protocolText = 'PROXY TCP4 127.0.0.1 192.0.2.1 12345 54321\r\n';
const proto = proxyProtocol.V1ProxyProtocol.parse(protocolText);
console.log(proto);
// => V1ProxyProtocol {
//      inetProtocol: 'TCP4',
//      source: Host { ipAddress: '127.0.0.1', port: 12345 },
//      destination: Host { ipAddress: '192.0.2.1', port: 54321 },
//      data: '' }
```

#### V2 protocol

```JavaScript
const proxyProtocol = require('proxy-protocol-js');

const protoBin = new Uint8Array([13, 10, 13, 10, 0, 13, 10, 81, 85, 73, 84, 10, 32, 18, 0, 12, 127, 0, 0, 1, 192, 0, 2, 1, 48, 57, 212, 49]);
const proto = proxyProtocol.V2ProxyProtocol.parse(protoBin);
console.log(proto);
// => V2ProxyProtocol {
//   command: 0,
//   transportProtocol: 2,
//   proxyAddress:
//    IPv4ProxyAddress {
//      sourceAddress: IPv4Address { address: [Array] },
//      sourcePort: 12345,
//      destinationAddress: IPv4Address { address: [Array] },
//      destinationPort: 54321 },
//   data: Uint8Array [],
//   addressFamilyType: 16 }`
```

Performance
--

The result of the comparison between this library (`proxy-protocol-js`) and [proxy-protocol](https://www.npmjs.com/package/proxy-protocol) is here:

```
proxy-protocol.parse x 246,423 ops/sec ±3.10% (32 runs sampled)
proxy-protocol-js.parse x 481,388 ops/sec ±5.32% (69 runs sampled)
Fastest is proxy-protocol-js.parse
```

(moreover, `proxy-protocol-js`'s benchmark contains unnecessary dummy codes for fairness)

This benchmark run on the node v10.15.3 and the code is [here](./bench).

Author
--

moznion (<moznion@gmail.com>)

License
--

[MIT](./LICENSE)

