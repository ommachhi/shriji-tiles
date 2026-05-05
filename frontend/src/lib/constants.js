const defaultBackendUrl =
  process.env.NODE_ENV === "development"
    ? "http://localhost:8001"
    : "https://shriji-tiles.onrender.com";

const runtimeBackendUrl =
  (typeof window !== "undefined" && window.desktopConfig?.backendUrl) ||
  process.env.REACT_APP_BACKEND_URL ||
  defaultBackendUrl;

export const BACKEND_BASE_URL = runtimeBackendUrl.replace(/\/+$/, "");
export const PUBLIC_ASSET_BASE_URL =
  process.env.REACT_APP_PUBLIC_ASSET_BASE_URL || BACKEND_BASE_URL;
export const PUBLIC_FALLBACK_IMAGE_PATH = "/assets/fallback-product.svg";

export const currencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

export const dateFormatter = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

export const navigationItems = [
  { id: "create-bom", label: "Create Quotation", short: "CQ", caption: "Single-page BOM builder" },
  { id: "quotations", label: "Quotations", short: "QL", caption: "Saved drafts and finals" },
  { id: "clients", label: "Clients", short: "CL", caption: "Client directory" },
  { id: "products", label: "Products", short: "PR", caption: "Managed product codes" },
];

export const hiddenPageIds = ["quotation-view"];

export const catalogOptions = [
  { id: "all", label: "All Sources" },
  { id: "managed", label: "Saved Products" },
  { id: "aquant", label: "Aquant" },
  { id: "kohler", label: "Kohler" },
];

export const quoteStatusOptions = ["all", "draft", "final"];

export const roomOptions = [
  "Kid's Bathroom",
  "Guest Bathroom",
  "Parent's Bathroom",
  "Master Bathroom",
  "Common / Powder Room",
  "Living Room",
  "Kitchen",
  "Balcony",
  "Utility Room",
];

export const discountTypeOptions = [
  { id: "item-wise", label: "Item-wise discount", helper: "Each row uses its own discount percentage." },
  { id: "common-percentage", label: "Common percentage", helper: "Apply one percentage across the full subtotal." },
  { id: "on-total", label: "On-total discount", helper: "Deduct a flat amount after GST is added." },
];

export const preparedByOptions = [
  {
    value: "harsh_bhai",
    label: "Harsh Bhai – +91 82385 21277",
    name: "Harsh Bhai",
    phone: "+91 82385 21277",
  },
  {
    value: "karan_bhai",
    label: "Karan Bhai – +91 82009 17069",
    name: "Karan Bhai",
    phone: "+91 82009 17069",
  },
  {
    value: "kunal_bhai",
    label: "Kunal Bhai – +91 98987 13167",
    name: "Kunal Bhai",
    phone: "+91 98987 13167",
  },
];

export function getClientDisplayLabel(client) {
  const parts = [client?.client_name || client?.name || ""].filter(Boolean);
  const company = String(client?.company || "").trim();
  const phone = String(client?.phone || "").trim();

  if (company) {
    parts.push(company);
  }
  if (phone) {
    parts.push(phone);
  }

  return parts.join(" – ");
}

export function formatCurrency(value) {
  return currencyFormatter.format(Number(value) || 0);
}

export function formatDate(value) {
  if (!value) {
    return dateFormatter.format(new Date());
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return dateFormatter.format(new Date());
  }

  return dateFormatter.format(parsed);
}

export function formatDateForInput(value = new Date()) {
  const parsed = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return formatDateForInput(new Date());
  }
  return [
    parsed.getFullYear(),
    String(parsed.getMonth() + 1).padStart(2, "0"),
    String(parsed.getDate()).padStart(2, "0"),
  ].join("-");
}

export function getPageFromHash() {
  if (typeof window === "undefined") {
    return "create-bom";
  }

  const hash = window.location.hash.replace(/^#/, "").trim().toLowerCase();
  const allowed = new Set([...navigationItems.map((item) => item.id), ...hiddenPageIds]);
  return allowed.has(hash) ? hash : "create-bom";
}

export function formatStatusLabel(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (normalized === "all") {
    return "All";
  }
  if (normalized === "final") {
    return "Final";
  }
  if (normalized === "draft") {
    return "Draft";
  }
  return "Unknown";
}
