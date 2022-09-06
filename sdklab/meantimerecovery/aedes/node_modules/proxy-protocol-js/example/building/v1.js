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
