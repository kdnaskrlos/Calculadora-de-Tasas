// Monitor gratuito de la tasa Binance USDT/VES para Cloudflare Workers.
// Solo se ejecuta mediante Cron Trigger. No acepta solicitudes HTTP que activen GitHub.
const OWNER = 'kdnaskrlos';
const REPO = 'Calculadora-de-Tasas';
const WORKFLOW = 'actualizar-tasa.yml';
const MAX_AGE_MS = 35 * 60 * 1000;
const MAX_CLOCK_SKEW_MS = 5 * 60 * 1000;

export async function revisarTasa(env, { now = Date.now(), fetcher = fetch } = {}) {
  if (!env.GITHUB_TOKEN) throw new Error('Falta el secreto GITHUB_TOKEN en Cloudflare.');

  // El parámetro único evita leer un JSON antiguo de una caché HTTP.
  const tasaUrl = `https://raw.githubusercontent.com/${OWNER}/${REPO}/main/tasa.json?monitor=${now}`;
  const response = await fetcher(tasaUrl, {
    headers: { Accept: 'application/json', 'Cache-Control': 'no-cache' },
  });
  if (!response.ok) throw new Error(`No se pudo leer tasa.json: HTTP ${response.status}`);
  const data = await response.json();
  const fecha = typeof data?.updated_at === 'string' ? Date.parse(data.updated_at) : NaN;
  if (!Number.isFinite(fecha) || !Number.isFinite(data?.rate) || data.rate <= 0) {
    throw new Error('tasa.json no contiene una tasa y fecha válidas.');
  }
  const ageMs = now - fecha;
  if (ageMs < -MAX_CLOCK_SKEW_MS) throw new Error('La fecha de la tasa está en el futuro.');
  const ageMinutes = Math.max(0, Math.floor(ageMs / 60000));
  if (ageMs < MAX_AGE_MS) {
    console.log(`Tasa reciente: ${ageMinutes} min. No se activa GitHub.`);
    return { action: 'recent', ageMinutes };
  }

  // El token debe ser fine-grained: solo este repositorio, permiso Actions: write.
  // force=false evita saltarse el guardián de 25 minutos del script de Python.
  const dispatchUrl = `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}/dispatches`;
  const dispatch = await fetcher(dispatchUrl, {
    method: 'POST',
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      'Content-Type': 'application/json',
      'User-Agent': 'calculadora-tasas-monitor',
      'X-GitHub-Api-Version': '2022-11-28',
    },
    body: JSON.stringify({ ref: 'main', inputs: { force: 'false' } }),
  });
  if (!dispatch.ok) throw new Error(`GitHub no aceptó la activación: HTTP ${dispatch.status}`);
  console.log(`Tasa antigua (${ageMinutes} min). GitHub Actions activado.`);
  return { action: 'dispatched', ageMinutes };
}

export default {
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(revisarTasa(env));
  },
  // No hay mecanismo público para activar los workflows mediante una URL.
  async fetch() {
    return new Response('No disponible', { status: 404 });
  },
};
