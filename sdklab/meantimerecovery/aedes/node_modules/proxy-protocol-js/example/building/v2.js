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
