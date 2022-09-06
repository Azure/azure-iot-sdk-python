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
//   addressFamilyType: 16 }
