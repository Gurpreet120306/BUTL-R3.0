const BASE = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';
let token;
let pending;
async function session() {
  if (token) return token;
  if (!pending) pending = fetch(`${BASE}/api/session`, { cache: 'no-store' }).then(async r => {
    if (!r.ok) throw new Error('Cannot establish local session. Check FRONTEND_ORIGIN and restart the backend.');
    token = (await r.json()).token;
    return token;
  }).finally(() => { pending = null; });
  return pending;
}
export async function api(path, { method = 'GET', body, retry = true } = {}) {
  let response;
  try {
    const sessionToken = await session();
    response = await fetch(`${BASE}/api${path}`, {
      method, cache: 'no-store', headers: { 'X-BUTLR-Token': sessionToken, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
  } catch (error) {
    throw new Error(error.message === 'Failed to fetch' ? 'Backend unavailable. Start FastAPI on 127.0.0.1:8000.' : error.message);
  }
  if (response.status === 403 && retry) {
    token = null;
    return api(path, { method, body, retry: false });
  }
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Request validation failed. Check the supplied values.');
  return result;
}
