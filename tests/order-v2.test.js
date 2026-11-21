import test from 'node:test';
import assert from 'node:assert/strict';
import { constants, generateKeyPairSync, verify } from 'node:crypto';
import { KalshiClient } from '../server/kalshiClient.js';

for (const algorithm of ['ed25519', 'rsa']) {
  test(`${algorithm} signs full path without query, and uses V2 order endpoint`, async () => {
    const pair = algorithm === 'rsa'
      ? generateKeyPairSync('rsa', { modulusLength: 2048 })
      : generateKeyPairSync('ed25519');
    const pem = pair.privateKey.export({ format: 'pem', type: 'pkcs8' });
    const client = new KalshiClient({ baseUrl: 'https://external-api.demo.kalshi.co/trade-api/v2', keyId: 'test', privateKeyPem: pem, enabled: true });
    const original = globalThis.fetch;
    let calls = 0;
    globalThis.fetch = async (url, options) => {
      calls++;
      if (calls === 1) {
        assert.equal(url.pathname, '/trade-api/v2/portfolio/events/orders');
        assert.equal(options.method, 'POST');
        assert.deepEqual(JSON.parse(options.body), {
          ticker: 'TEST', side: 'bid', count: '1.00', price: '0.4000',
          time_in_force: 'immediate_or_cancel', self_trade_prevention_type: 'taker_at_cross',
        });
      } else {
        assert.equal(url.pathname, '/trade-api/v2/portfolio/balance');
        assert.equal(url.search, '?subaccount=3');
        assert.equal(options.method, 'GET');
      }
      const h = options.headers;
      const message = Buffer.from(h['KALSHI-ACCESS-TIMESTAMP'] + options.method + url.pathname);
      const sig = Buffer.from(h['KALSHI-ACCESS-SIGNATURE'], 'base64');
      const key = algorithm === 'rsa' ? { key: pair.publicKey, padding: constants.RSA_PKCS1_PSS_PADDING, saltLength: 32 } : pair.publicKey;
      assert.equal(verify(algorithm === 'rsa' ? 'sha256' : null, message, key, sig), true);
      return { ok: true, text: async () => '{"order_id":"fixture"}' };
    };
    try {
      const response = await client.createOrder({ ticker: 'TEST', side: 'bid', count: '1.00', price: '0.4000', time_in_force: 'immediate_or_cancel', self_trade_prevention_type: 'taker_at_cross' });
      assert.equal(response.order_id, 'fixture');
      assert.equal(calls, 1);
      await client.getPortfolioBalance(3);
      assert.equal(calls, 2);
    } finally { globalThis.fetch = original; }
  });
}

test('legacy body and non-demo authenticated hosts fail closed before network', async () => {
  const pair = generateKeyPairSync('ed25519');
  const key = pair.privateKey.export({ format: 'pem', type: 'pkcs8' });
  const client = new KalshiClient({ baseUrl: 'https://external-api.kalshi.com/trade-api/v2', keyId: 'test', privateKeyPem: key, enabled: true });
  assert.throws(() => client.createOrder({ market_ticker: 'TEST', side: 'buy' }), /Invalid V2/);
  await assert.rejects(client.createOrder({ ticker: 'TEST', side: 'bid', count: '1.00', price: '0.4000', time_in_force: 'immediate_or_cancel', self_trade_prevention_type: 'taker_at_cross' }), /official demo hosts/);
});

test('HTTP portfolio and order routes fail closed even with configured keys', async () => {
  const { spawn } = await import('node:child_process');
  const { createServer } = await import('node:net');
  const probe = createServer();
  await new Promise((resolve, reject) => { probe.once('error', reject); probe.listen(0, '127.0.0.1', resolve); });
  const port = probe.address().port;
  await new Promise(resolve => probe.close(resolve));
  const key = generateKeyPairSync('ed25519').privateKey.export({ format: 'pem', type: 'pkcs8' });
  const child = spawn(process.execPath, ['server/index.js'], {
    env: { ...process.env, PORT: String(port), KALSHI_ACCESS_KEY: 'fixture', KALSHI_PRIVATE_KEY: key },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  try {
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('server startup timed out')), 10000);
      child.once('error', reject);
      child.once('exit', code => reject(new Error(`server exited ${code}`)));
      child.stdout.on('data', chunk => {
        if (chunk.toString().includes('Kalshi demo dashboard backend on')) { clearTimeout(timeout); resolve(); }
      });
    });
    const portfolio = await fetch(`http://127.0.0.1:${port}/api/portfolio`);
    assert.equal(portfolio.status, 503);
    const order = await fetch(`http://127.0.0.1:${port}/api/trades/execute`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ market_ticker: 'TEST', side: 'yes', price: 0.4, count: 1 }),
    });
    assert.equal(order.status, 503);
    assert.match((await order.json()).error, /disabled/);
  } finally {
    child.kill('SIGKILL');
  }
});
