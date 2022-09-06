const proxyProtocol = require('proxy-protocol-js');

const protocolText = 'PROXY TCP4 127.0.0.1 192.0.2.1 12345 54321\r\n';
const proto = proxyProtocol.V1ProxyProtocol.parse(protocolText);
console.log(proto);
// => V1ProxyProtocol {
//      inetProtocol: 'TCP4',
//      source: Host { ipAddress: '127.0.0.1', port: 12345 },
//      destination: Host { ipAddress: '192.0.2.1', port: 54321 },
//      data: '' }

