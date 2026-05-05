import {
  BACKEND_BASE_URL,
  PUBLIC_ASSET_BASE_URL,
  PUBLIC_FALLBACK_IMAGE_PATH,
  catalogOptions,
} from "./constants";

export const variantOrder = ["BRG", "BG", "GG", "MB", "CP", "RG", "AB", "G"];

export function buildPlaceholder(productName = "Catalog product") {
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 420">
      <rect width="640" height="420" rx="18" fill="#ededed" />
      <rect x="40" y="40" width="560" height="340" rx="14" fill="#f6f6f6" stroke="#d5d5d5" stroke-width="4" />
      <text x="320" y="194" text-anchor="middle" font-size="44" font-weight="700" font-family="Arial, sans-serif" fill="#5d5d5d">
        IMAGE NOT FOUND
      </text>
      <text x="320" y="236" text-anchor="middle" font-size="18" font-family="Arial, sans-serif" fill="#7a7a7a">
        ${productName.replace(/[<&>]/g, "").slice(0, 44)}
      </text>
    </svg>
  `)}`;
}

export function normalizeSnippet(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

export function coercePrice(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.max(0, Math.round(value));
  }

  const text = String(value ?? "").trim();
  if (!text) {
    return 0;
  }

  const match = text.replace(/,/g, "").match(/\d+(?:\.\d{1,2})?/);
  if (!match) {
    return 0;
  }

  const parsed = Number(match[0]);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return 0;
  }

  return Math.round(parsed);
}

function isLocalHost(hostname) {
  return /^(localhost|127\.0\.0\.1|::1)$/i.test(String(hostname || "").trim());
}

function toAbsolutePublicUrl(value, baseUrl = PUBLIC_ASSET_BASE_URL) {
  const raw = String(value || "").trim();
  if (!raw) {
    return "";
  }

  if (raw.startsWith("data:image") || raw.startsWith("blob:")) {
    return raw;
  }

  try {
    const base = new URL(String(baseUrl || PUBLIC_ASSET_BASE_URL).trim() || PUBLIC_ASSET_BASE_URL);
    const parsed = new URL(raw, base);

    if (!["http:", "https:"].includes(parsed.protocol)) {
      return "";
    }

    if (isLocalHost(parsed.hostname) && !isLocalHost(base.hostname)) {
      return `${base.origin}${parsed.pathname}${parsed.search}${parsed.hash}`;
    }

    return parsed.toString();
  } catch (error) {
    return "";
  }
}

function uniqueNonEmpty(values) {
  const seen = new Set();
  const result = [];

  (Array.isArray(values) ? values : []).forEach((value) => {
    const normalized = String(value || "").trim();
    if (!normalized || seen.has(normalized)) {
      return;
    }
    seen.add(normalized);
    result.push(normalized);
  });

  return result;
}

export function getPublicFallbackImageUrl() {
  const runtimeBase =
    typeof window !== "undefined" && window.location?.origin
      ? window.location.origin
      : PUBLIC_ASSET_BASE_URL;

  return toAbsolutePublicUrl(PUBLIC_FALLBACK_IMAGE_PATH, runtimeBase);
}

export function normalizeImageUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) {
    return "";
  }

  const candidates = uniqueNonEmpty([
    toAbsolutePublicUrl(raw, BACKEND_BASE_URL),
    toAbsolutePublicUrl(raw, PUBLIC_ASSET_BASE_URL),
  ]);

  return candidates[0] || "";
}

export function buildProductImageUrl(product) {
  const primary = normalizeImageUrl(product?.image);
  if (primary) {
    return primary;
  }

  return getPublicFallbackImageUrl() || buildPlaceholder(product?.name);
}

export function handleProductImageError(event, product) {
  const target = event.currentTarget;
  target.dataset.fallbackCount = "1";
  target.src = getPublicFallbackImageUrl() || buildPlaceholder(product?.name);
}

async function isDirectImageUrlAccessible(url) {
  const target = String(url || "").trim();
  if (!target || target.startsWith("data:image") || target.startsWith("blob:")) {
    return Boolean(target);
  }

  try {
    const response = await fetch(target);
    if (!response.ok) {
      return false;
    }

    const contentType = String(response.headers.get("content-type") || "").toLowerCase();
    return contentType.includes("image/");
  } catch (error) {
    return false;
  }
}

export async function resolvePdfImageUrl(item) {
  const normalized = normalizeImageUrl(item?.image);
  const raw = String(item?.image || "").trim();
  const candidates = uniqueNonEmpty([
    normalized,
    toAbsolutePublicUrl(raw, PUBLIC_ASSET_BASE_URL),
    toAbsolutePublicUrl(raw, BACKEND_BASE_URL),
    toAbsolutePublicUrl(raw.split("?")[0], PUBLIC_ASSET_BASE_URL),
  ]);

  for (const candidate of candidates) {
    if (await isDirectImageUrlAccessible(candidate)) {
      return candidate;
    }
  }

  const fallbackUrl = getPublicFallbackImageUrl();
  if (await isDirectImageUrlAccessible(fallbackUrl)) {
    return fallbackUrl;
  }

  return buildPlaceholder(item?.name);
}

export function getCatalogLabel(catalogId, fallback = "") {
  const normalizedCatalogId = String(catalogId || "").trim().toLowerCase();
  const matchedCatalog = catalogOptions.find((option) => option.id === normalizedCatalogId);
  return matchedCatalog?.label || fallback || normalizedCatalogId;
}

export function buildDisplayName(product) {
  const words = normalizeSnippet(product?.name)
    .split(" ")
    .filter(Boolean)
    .filter((word, index, array) => {
      if (index === 0) {
        return true;
      }
      return word.toLowerCase() !== array[index - 1].toLowerCase();
    });

  if (words.length <= 2) {
    return words.join(" ");
  }

  return words.slice(0, 2).join(" ");
}

export function buildSuggestionDetails(product) {
  const details = normalizeSnippet(product?.details);
  const name = normalizeSnippet(product?.name);
  if (!details || details.toLowerCase() === name.toLowerCase()) {
    return "";
  }
  return details;
}

export function buildSuggestionSpecs(product) {
  const category = normalizeSnippet(product?.category);
  const size = normalizeSnippet(product?.size);
  const color = normalizeSnippet(product?.color);
  const variant = normalizeSnippet(product?.variant);
  const specs = [];

  if (category) {
    specs.push(category);
  }
  if (size) {
    specs.push(`Size: ${size}`);
  }
  if (color) {
    specs.push(`Color: ${color}`);
  } else if (variant && !/^n\/?a$/i.test(variant)) {
    specs.push(`Variant: ${variant}`);
  }

  return specs;
}

export function parseCodeParts(value) {
  const text = String(value || "").trim().toUpperCase();
  const baseMatch = text.match(/(\d{3,5})/);
  if (!baseMatch) {
    return { baseCode: "", variant: "" };
  }

  const baseCode = baseMatch[1];
  const tail = text.slice(baseMatch.index + baseCode.length).replace(/[^A-Z0-9]+/g, "").trim();
  return { baseCode, variant: tail.slice(0, 6) };
}

export function buildGroupedResults(results) {
  const groups = new Map();

  for (const product of results) {
    const parsed = parseCodeParts(product?.code);
    const baseCode = product?.baseCode || parsed.baseCode || String(product?.code || "").trim();
    const variant = String(product?.variant || parsed.variant || "").toUpperCase();
    const isCp = Boolean(product?.isCp || variant === "CP");
    const normalizedPrice = coercePrice(product?.price);

    if (!groups.has(baseCode)) {
      groups.set(baseCode, []);
    }

    groups.get(baseCode).push({
      ...product,
      price: normalizedPrice,
      baseCode,
      variant,
      isCp,
    });
  }

  return [...groups.entries()].map(([baseCode, items]) => {
    items.sort((left, right) => {
      const leftIndex = variantOrder.indexOf(left.variant);
      const rightIndex = variantOrder.indexOf(right.variant);
      const leftRank = leftIndex === -1 ? 99 : leftIndex;
      const rightRank = rightIndex === -1 ? 99 : rightIndex;
      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }
      return String(left.code || "").localeCompare(String(right.code || ""));
    });
    return { baseCode, items };
  });
}
