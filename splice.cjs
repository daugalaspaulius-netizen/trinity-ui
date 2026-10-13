'use strict';

const net = require('net');
const ziti = require('@openziti/ziti-sdk-nodejs');

const mode = process.argv[2];
const identity = process.argv[3];

function asBuffer(data) {
  if (data == null) return { end: true };
  if (data instanceof Error) return { end: true };
  if (typeof data === 'number') return data < 0 ? { end: true } : { ignore: true };
  if (Buffer.isBuffer(data)) return data.length ? { buf: data } : { ignore: true };
  if (typeof data.len === 'number' && data.len < 0) return { end: true };
  const raw = data.app_data || data.data || data.body;
  if (Buffer.isBuffer(raw)) return raw.length ? { buf: raw } : { ignore: true };
  if (typeof raw === 'string' && raw.length) return { buf: Buffer.from(raw) };
  return { ignore: true };
}

function writer(conn) {
  const queue = [];
  let busy = false;
  function pump() {
    if (busy || queue.length === 0) return;
    busy = true;
    const chunk = queue.shift();
    try {
      ziti.write(conn, chunk, () => {
        busy = false;
        pump();
      });
    } catch {
      busy = false;
    }
  }
  return function push(buf) {
    if (!buf || !buf.length) return;
    queue.push(buf);
    pump();
  };
}

function spliceSocket(conn, socket) {
  let closed = false;
  function finish() {
    if (closed) return;
    closed = true;
    try { socket.destroy(); } catch {}
    try { ziti.close(conn); } catch {}
  }
  const push = writer(conn);
  socket.on('data', push);
  socket.on('error', finish);
  socket.on('close', finish);
  return function incoming(data) {
    const part = asBuffer(data);
    if (part.end) {
      finish();
      return;
    }
    if (part.buf && !socket.destroyed) socket.write(part.buf);
  };
}

async function main() {
  if (!identity || (mode !== 'dial' && mode !== 'bind' && mode !== 'both')) {
    process.stderr.write('usage: splice.cjs dial|bind|both <identity> ...\n');
    process.exit(2);
  }
  await ziti.init(identity);

  if (mode === 'dial' || mode === 'both') {
    const listenPort = Number(process.argv[4]);
    const service = process.argv[5];
    net.createServer((socket) => {
      let incoming = null;
      ziti.dial(service, false, (conn) => {
        if (conn instanceof Error || (typeof conn === 'number' && conn < 0)) {
          socket.destroy();
          return;
        }
        incoming = spliceSocket(conn, socket);
      }, (data) => {
        if (incoming) incoming(data);
      });
    }).listen(listenPort, '127.0.0.1', () => {
      process.stdout.write('DIAL_READY ' + listenPort + ' ' + service + '\n');
    });
  }

  if (mode === 'bind' || mode === 'both') {
    const offset = mode === 'both' ? 6 : 4;
    const targetHost = process.argv[offset];
    const targetPort = Number(process.argv[offset + 1]);
    const service = process.argv[offset + 2];
    const clients = new Map();
    ziti.listen(service, 1, (status) => {
      process.stdout.write('BIND_STATUS ' + status + ' ' + service + '\n');
    }, () => {}, (obj) => {
      const conn = obj.client;
      const socket = net.connect(targetPort, targetHost);
      clients.set(conn, spliceSocket(conn, socket));
      socket.on('error', () => {
        try { ziti.close(conn); } catch {}
        clients.delete(conn);
      });
    }, (obj) => {
      const handler = clients.get(obj.client);
      if (handler) handler(obj);
    });
  }
}

main().catch((err) => {
  process.stderr.write(String(err && err.stack ? err.stack : err) + '\n');
  process.exit(1);
});
