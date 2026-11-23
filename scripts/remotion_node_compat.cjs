// Remotion's local HTTP server probes the host's network interfaces. Some
// managed runners hide those interfaces; loopback is enough for its local
// browser/server handshake and keeps rendering offline.
const os = require('node:os');
const original = os.networkInterfaces.bind(os);
try {
  original();
} catch (error) {
  if (!process.env.REMOTION_FORCE_LOOPBACK_NETWORK) throw error;
  os.networkInterfaces = () => ({
    lo: [
      {address: '127.0.0.1', netmask: '255.0.0.0', family: 'IPv4', mac: '00:00:00:00:00:00', internal: true, cidr: '127.0.0.1/8'},
      {address: '::1', netmask: 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff', family: 'IPv6', mac: '00:00:00:00:00:00', internal: true, cidr: '::1/128', scopeid: 0},
    ],
  });
}
