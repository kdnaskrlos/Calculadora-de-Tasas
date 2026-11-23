import test from 'node:test';
import assert from 'node:assert/strict';
import { revisarTasa } from './worker.js';

const NOW = Date.parse('2026-11-23T16:00:00Z');
const token = { GITHUB_TOKEN: 'token-de-prueba' };
const json = (mins, rate = 1099.55) => new Response(JSON.stringify({
  rate, updated_at: new Date(NOW - mins * 60_000).toISOString(),
}), { status: 200 });

test('no activa GitHub si la tasa es reciente', async () => {
  let requests = 0;
  const result = await revisarTasa(token, { now: NOW, fetcher: async () => {
    requests += 1; return json(15);
  } });
  assert.equal(result.action, 'recent');
  assert.equal(requests, 1);
});

test('activa GitHub al superar 35 minutos, sin forzar Binance', async () => {
  const requests = [];
  const result = await revisarTasa(token, { now: NOW, fetcher: async (url, opt) => {
    requests.push({ url, opt });
    return requests.length === 1 ? json(40) : new Response(null, { status: 204 });
  } });
  assert.equal(result.action, 'dispatched');
  assert.equal(requests.length, 2);
  assert.match(requests[1].url, /\/actions\/workflows\/actualizar-tasa.yml\/dispatches$/);
  assert.equal(requests[1].opt.method, 'POST');
  assert.deepEqual(JSON.parse(requests[1].opt.body), { ref: 'main', inputs: { force: 'false' } });
});

test('no envía dispatch cuando falta el token', async () => {
  await assert.rejects(revisarTasa({}, { now: NOW, fetcher: async () => json(120) }), /GITHUB_TOKEN/);
});

test('detiene el proceso si tasa.json es inválido', async () => {
  await assert.rejects(revisarTasa(token, { now: NOW, fetcher: async () => json(90, 0) }), /válidas/);
});

test('reporta falla de GitHub sin exponer token', async () => {
  let count = 0;
  await assert.rejects(revisarTasa(token, { now: NOW, fetcher: async () => {
    count++;
    return count === 1 ? json(90) : new Response(null, { status: 403 });
  } }), /HTTP 403/);
});

test('la URL pública del Worker no puede disparar Actions', async () => {
  const mod = await import('./worker.js');
  const response = await mod.default.fetch();
  assert.equal(response.status, 404);
});
