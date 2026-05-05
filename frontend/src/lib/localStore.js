const KEYS = {
  quotes: "sc_quotes_cache_v1",
  clients: "sc_clients_cache_v1",
  products: "sc_products_cache_v1",
};

function safeParse(value, fallback) {
  try {
    return JSON.parse(value);
  } catch (error) {
    return fallback;
  }
}

export function readLocalCollection(key) {
  if (typeof window === "undefined" || !window.localStorage) {
    return [];
  }
  return safeParse(window.localStorage.getItem(key), []);
}

export function writeLocalCollection(key, entries) {
  if (typeof window === "undefined" || !window.localStorage) {
    return;
  }
  window.localStorage.setItem(key, JSON.stringify(Array.isArray(entries) ? entries : []));
}

export function appendLocalEntry(key, entry) {
  if (!entry?.id) {
    return;
  }
  const existing = readLocalCollection(key) || [];
  writeLocalCollection(key, [entry, ...(Array.isArray(existing) ? existing : [])]);
}

export function upsertLocalEntry(key, entry) {
  if (!entry?.id) {
    return;
  }
  const existing = readLocalCollection(key) || [];
  const next = [entry, ...(Array.isArray(existing) ? existing : []).filter((item) => String(item.id) !== String(entry.id))];
  writeLocalCollection(key, next);
}

export function removeLocalEntry(key, id) {
  const existing = readLocalCollection(key) || [];
  writeLocalCollection(
    key,
    (Array.isArray(existing) ? existing : []).filter((item) => String(item.id) !== String(id))
  );
}

export const localStoreKeys = KEYS;

