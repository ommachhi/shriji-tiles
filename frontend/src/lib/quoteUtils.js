export function normalizeItemKey(code, name) {
  return String(code || name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

export function sanitizeNumber(value, minimum = 0) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return minimum;
  }
  return Math.max(minimum, numeric);
}

/**
 * Normalize a quotation to ensure all array fields are properly initialized.
 * This prevents null.filter() errors when loading quotations from storage.
 */
export function normalizeQuotation(q) {
  if (!q) return null;
  
  const normalized = { ...q };
  
  // Ensure all array fields exist and are arrays
  if (!Array.isArray(normalized.items)) {
    normalized.items = [];
  }
  
  return normalized;
}

function clampPercent(value) {
  return Math.min(100, sanitizeNumber(value, 0));
}

function createRowId(seed = "item") {
  return `row-${seed}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function getItemDiscountPercent(item) {
  return clampPercent(item?.discountPercent ?? item?.discount_percent ?? 0);
}

export function getItemRoomName(item) {
  return String(item?.roomName ?? item?.room_name ?? "").trim();
}

export function getItemImage(item) {
  return String(item?.productImage ?? item?.product_image ?? item?.image ?? "").trim();
}

export function calculateItemBaseTotal(item) {
  return sanitizeNumber(item?.qty, 1) * sanitizeNumber(item?.price, 0);
}

export function calculateItemDiscountAmount(item, options = {}) {
  const baseTotal = calculateItemBaseTotal(item);
  const discountType = String(options.discountType || "item-wise").trim().toLowerCase();
  const discountValue = clampPercent(options.discountValue);

  if (discountType === "common-percentage") {
    return (baseTotal * discountValue) / 100;
  }

  if (discountType === "item-wise") {
    return (baseTotal * getItemDiscountPercent(item)) / 100;
  }

  return 0;
}

export function calculateLineTotal(item, options = {}) {
  const baseTotal = calculateItemBaseTotal(item);
  const discountAmount = calculateItemDiscountAmount(item, options);
  return Math.max(0, baseTotal - discountAmount);
}

export function calculateQuoteTotals({
  items = [],
  gstRate = 18,
  discountType = "item-wise",
  discountValue = 0,
}) {
  const normalizedItems = Array.isArray(items) ? items : [];
  const normalizedDiscountType = String(discountType || "item-wise").trim().toLowerCase();
  const safeGstRate = clampPercent(gstRate);
  const safeDiscountValue = sanitizeNumber(discountValue, 0);
  const grossSubtotal = normalizedItems.reduce((sum, item) => sum + calculateItemBaseTotal(item), 0);

  // Subtotal should always represent the original sum of item prices (gross total)
  let discountAmount = 0;
  const subtotal = grossSubtotal;

  // Calculate discount amount based on discount mode
  if (normalizedDiscountType === "item-wise" || normalizedDiscountType === "common-percentage") {
    discountAmount = normalizedItems.reduce(
      (sum, item) =>
        sum +
        calculateItemDiscountAmount(item, {
          discountType: normalizedDiscountType,
          discountValue: safeDiscountValue,
        }),
      0
    );
  } else if (normalizedDiscountType === "on-total") {
    // 'on-total' is a flat amount; cap it at grossSubtotal to avoid negative taxable amounts.
    discountAmount = Math.max(0, Math.min(safeDiscountValue, grossSubtotal));
  }

  // Taxable subtotal = original prices minus discounts (user requested this behavior)
  const taxableSubtotal = Math.max(0, grossSubtotal - discountAmount);
  const gstAmount = (taxableSubtotal * safeGstRate) / 100;

  const grandTotal = Math.max(0, taxableSubtotal + gstAmount);

  return {
    subtotal,
    grossSubtotal,
    discountAmount,
    taxableSubtotal,
    gstAmount,
    grandTotal,
    gstRate: safeGstRate,
  };
}

export function buildLineItemFromProduct(product) {
  return {
    rowId: createRowId(normalizeItemKey(product?.code, product?.name) || "item"),
    productKey: normalizeItemKey(product?.code, product?.name),
    productCode: product?.code || "",
    productName: product?.name || "Custom Product",
    brand: product?.brand || product?.sourceLabel || product?.source || "Custom",
    category: product?.category || "General",
    productImage: product?.image || "",
    details: product?.details || "",
    size: product?.size || "",
    color: product?.color || "",
    roomName: "",
    qty: sanitizeNumber(product?.qty, 1) || 1,
    price: sanitizeNumber(product?.price, 0),
    discountPercent: clampPercent(product?.discountPercent ?? product?.discount ?? 0),
  };
}

export function buildLineItemFromCustomProduct(form) {
  const trimmedName = String(form?.productName || "").trim();
  const trimmedCode = String(form?.productCode || "").trim();
  return buildLineItemFromProduct({
    code:
      trimmedCode ||
      `CUS-${trimmedName.replace(/[^a-z0-9]+/gi, "-").replace(/^-+|-+$/g, "").slice(0, 24) || "ITEM"}`,
    name: trimmedName || "Custom Product",
    brand: form?.brand || "Custom",
    category: form?.category || "Custom",
    price: form?.price,
    image: form?.productImage || "",
    details: form?.details || "",
  });
}

export function mapQuoteToWorkspace(quote) {
  const normalized = normalizeQuotation(quote);
  if (!normalized) {
    return null;
  }
  
  return {
    draftId: normalized?.id || null,
    proposalNo: normalized?.proposal_no || "",
    clientId: normalized?.client_id ? String(normalized.client_id) : "",
    clientName: normalized?.client_name || "",
    company: normalized?.company || "",
    phone: normalized?.phone || "",
    email: normalized?.email || "",
    address: normalized?.address || "",
    preparedBy: normalized?.prepared_by || normalized?.preparedBy || "",
    preparedPhone: normalized?.prepared_phone || normalized?.preparedPhone || "",
    quoteDate: normalized?.date || "",
    gstRate: Number(normalized?.gst_rate) || 18,
    gstEnabled: normalized?.gst_enabled !== false,
    discountType: normalized?.discount_type || "item-wise",
    discountValue: sanitizeNumber(normalized?.discount_value, 0),
    status: normalized?.status || "draft",
    watermark: Boolean(normalized?.watermark ?? true),
    items: Array.isArray(normalized?.items)
      ? (normalized.items || []).map((item) => ({
          rowId: createRowId(item?.product_key || item?.product_code || "item"),
          productKey: item?.product_key || normalizeItemKey(item?.product_code, item?.product_name),
          productCode: item?.product_code || "",
          productName: item?.product_name || "Product",
          brand: item?.brand || "",
          category: item?.category || "General",
          productImage: getItemImage(item),
          details: item?.details || "",
          size: item?.size || "",
          color: item?.color || "",
          roomName: getItemRoomName(item),
          qty: sanitizeNumber(item?.qty, 1) || 1,
          price: sanitizeNumber(item?.price, 0),
          discountPercent: getItemDiscountPercent(item),
        }))
      : [],
  };
}

export function buildQuotationPayload({
  proposalNo,
  clientId,
  clientName,
  company,
  phone,
  email,
  address,
  preparedBy,
  preparedPhone,
  quoteDate,
  gstRate,
  gstEnabled,
  discountType,
  discountValue,
  status,
  watermark,
  items,
}) {
  return {
    proposal_no: proposalNo,
    proposalNo,
    client_id: clientId ? Number(clientId) : null,
    client_name: clientName,
    company,
    phone,
    email,
    address,
    prepared_by: preparedBy,
    prepared_phone: preparedPhone,
    date: quoteDate,
    gst_rate: clampPercent(gstRate),
    gst_enabled: Boolean(gstEnabled ?? true),
    discount_type: String(discountType || "item-wise").trim().toLowerCase(),
    discount_value: sanitizeNumber(discountValue, 0),
    status,
    watermark: Boolean(watermark),
    items: (Array.isArray(items) ? items : []).map((item) => ({
      product_code: item?.productCode || "",
      product_name: item?.productName || "Product",
      brand: item?.brand || "",
      category: item?.category || "General",
      product_image: getItemImage(item),
      details: item?.details || "",
      size: item?.size || "",
      color: item?.color || "",
      room_name: getItemRoomName(item),
      qty: sanitizeNumber(item?.qty, 1) || 1,
      price: sanitizeNumber(item?.price, 0),
      discount_percent: getItemDiscountPercent(item),
    })),
  };
}
