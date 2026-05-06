import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import { formatDateForInput, PUBLIC_ASSET_BASE_URL, roomOptions } from "../lib/constants";
import {
  fetchAutocompleteSuggestions,
  fetchQuotationProposalNumber,
  getErrorMessage,
} from "../lib/api";
import {
  buildLineItemFromCustomProduct,
  buildLineItemFromProduct,
  buildQuotationPayload,
  calculateLineTotal,
  calculateQuoteTotals,
  mapQuoteToWorkspace,
  normalizeItemKey,
  sanitizeNumber,
} from "../lib/quoteUtils";
import { generateQuotationPDF } from "../pdf/quotationPdf";
import { localStoreKeys, upsertLocalEntry } from "../lib/localStore";

function formatScProposalNo(rawValue = "", fallbackCounter = 1) {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  const datePart = `${y}${m}${d}`;
  const digits = String(rawValue || "").replace(/\D/g, "");
  const suffix = String(Number(digits.slice(-4)) || fallbackCounter).padStart(4, "0");
  return `SC-${datePart}-${suffix}`;
}

const emptyCustomProduct = {
  productCode: "",
  productName: "",
  brand: "Custom",
  category: "Custom",
  price: "",
  productImage: "",
  details: "",
};

function createEmptyDraft(proposalNo = "") {
  return {
    draftId: null,
    proposalNo,
    clientId: "",
    clientName: "",
    company: "",
    phone: "",
    email: "",
    address: "",
    preparedBy: "",
    preparedPhone: "",
    quoteDate: formatDateForInput(new Date()),
    gstRate: 18,
    gstEnabled: true,
    discountType: "item-wise",
    discountValue: 0,
    status: "draft",
    watermark: true,
    items: [],
  };
}

function getDefaultRoom() {
  return roomOptions.find((room) => room === "Kitchen") || roomOptions[0] || "";
}

function buildDownloadFileName(quote) {
  const proposal = String(quote?.proposal_no || "quotation")
    .replace(/[^a-z0-9_.-]+/gi, "_")
    .replace(/^_+|_+$/g, "");
  return `${proposal || "quotation"}.pdf`;
}

function buildLocalQuoteRecord(payload, statusValue, existingId, totals) {
  const id = existingId || `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  return {
    id,
    proposal_no: payload.proposal_no,
    date: payload.date || formatDateForInput(new Date()),
    prepared_by: payload.prepared_by || "",
    prepared_phone: payload.prepared_phone || "",
    gst_rate: payload.gst_rate,
    gst_enabled: payload.gst_enabled !== false,
    discount_type: payload.discount_type,
    discount_value: payload.discount_value,
    status: statusValue,
    watermark: payload.watermark,
    client_id: payload.client_id,
    client_name: payload.client_name || "",
    company: payload.company || "",
    phone: payload.phone || "",
    email: payload.email || "",
    address: payload.address || "",
    items: payload.items || [],
    subtotal: totals?.subtotal || 0,
    total: totals?.grandTotal || 0,
    _local: true,
    updated_at: new Date().toISOString(),
  };
}

function downloadBlob(blob, fileName) {
  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1000);
}



export function useBomWorkspace({ clients, onQuoteSaved, notify, showPdfModal }) {
  const [draft, setDraft] = useState(() => createEmptyDraft(""));
  const [activeRoom, setActiveRoom] = useState(() => getDefaultRoom());
  const [query, setQuery] = useState("");
  const [catalogFilter, setCatalogFilter] = useState("all");
  const [suggestions, setSuggestions] = useState([]);
  const [searching, setSearching] = useState(false);
  const [saving, setSaving] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [customProductOpen, setCustomProductOpen] = useState(false);
  const [customProduct, setCustomProduct] = useState(emptyCustomProduct);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [sharePanel, setSharePanel] = useState({ isOpen: false, quote: null, blob: null, savedAt: null });
  const [lastSavedAt, setLastSavedAt] = useState(null);
  const pdfCacheRef = useRef({ payloadString: null, blob: null });
  const searchCacheRef = useRef(new Map());

  const effectiveGstRate = draft.gstEnabled ? draft.gstRate : 0;

  const quoteTotals = useMemo(
    () =>
      calculateQuoteTotals({
        items: draft.items,
        gstRate: effectiveGstRate,
        discountType: draft.discountType,
        discountValue: draft.discountValue,
      }),
    [draft.discountType, draft.discountValue, effectiveGstRate, draft.items]
  );

  const requestFreshProposalNumber = useCallback(async () => {
    const response = await fetchQuotationProposalNumber();
    return formatScProposalNo(response?.proposal_no, Date.now() % 10000);
  }, []);

  const startNewDraft = useCallback(async () => {
    setInitializing(true);
    try {
      const proposalNo = await requestFreshProposalNumber();
      setDraft(createEmptyDraft(proposalNo));
      setActiveRoom(getDefaultRoom());
      setQuery("");
      setSuggestions([]);
      setCatalogFilter("all");
      setCustomProductOpen(false);
      setCustomProduct(emptyCustomProduct);
    } catch (error) {
      notify?.({
        tone: "warning",
        title: "Unable to create a fresh draft",
        message: getErrorMessage(error, "The system could not fetch a new proposal number."),
      });
      setDraft(createEmptyDraft(""));
    } finally {
      setInitializing(false);
    }
  }, [notify, requestFreshProposalNumber]);

  useEffect(() => {
    void startNewDraft();
  }, [startNewDraft]);

  useEffect(() => {
    const trimmedQuery = query.trim();
    if (trimmedQuery.length < 1) {
      setSuggestions([]);
      setSearching(false);
      return undefined;
    }

    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setSearching(true);
      try {
        const cacheKey = `${catalogFilter}::${trimmedQuery.toLowerCase()}`;
        if (searchCacheRef.current.has(cacheKey)) {
          if (!cancelled) {
            setSuggestions(searchCacheRef.current.get(cacheKey));
          }
          return;
        }
        const response = await fetchAutocompleteSuggestions({ q: trimmedQuery, catalog: catalogFilter, limit: 8 });
        const nextSuggestions = Array.isArray(response?.suggestions) ? response.suggestions : [];
        searchCacheRef.current.set(cacheKey, nextSuggestions);
        if (!cancelled) {
          setSuggestions(nextSuggestions);
        }
      } catch (error) {
        if (!cancelled) {
          setSuggestions([]);
        }
      } finally {
        if (!cancelled) {
          setSearching(false);
        }
      }
    }, 300);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [catalogFilter, query]);

  const selectClient = useCallback(
    (clientId) => {
      if (!clientId) {
        setDraft((prev) => ({
          ...prev,
          clientId: "",
          clientName: "",
          company: "",
          phone: "",
          email: "",
          address: "",
        }));
        return;
      }

      const matchedClient = (Array.isArray(clients) ? clients : []).find(
        (client) => String(client.id) === String(clientId)
      );
      if (!matchedClient) {
        return;
      }

      setDraft((prev) => ({
        ...prev,
        clientId: String(matchedClient.id),
        clientName: matchedClient.client_name || "",
        company: matchedClient.company || "",
        phone: matchedClient.phone || "",
        email: matchedClient.email || "",
        address: matchedClient.address || "",
        gstRate: Number(matchedClient.gst_rate ?? matchedClient.gst ?? prev.gstRate) || prev.gstRate,
      }));
    },
    [clients]
  );

  const updateDraftField = useCallback((field, value) => {
    setDraft((prev) => ({ ...prev, [field]: value }));
  }, []);

  const addItem = useCallback(
    (nextItem, sourceLabel = "Product added") => {
      let duplicateMessage = "";
      let successMessage = "";
      const selectedRoom = String(activeRoom || nextItem.roomName || "").trim();
      const itemToAdd = selectedRoom ? { ...nextItem, roomName: selectedRoom } : nextItem;

      setDraft((prev) => {
        const nextKey = normalizeItemKey(itemToAdd.productCode, itemToAdd.productName);
        const existingIndex = prev.items.findIndex((item) => item.productKey === nextKey);

        if (existingIndex >= 0) {
          const updatedItems = prev.items.map((item, index) =>
            index === existingIndex
              ? {
                  ...item,
                  qty: sanitizeNumber(item.qty, 1) + sanitizeNumber(itemToAdd.qty, 1),
                  roomName: String(item.roomName || selectedRoom || "").trim(),
                }
              : item
          );
          duplicateMessage = `${itemToAdd.productName} already existed in this quotation, so the quantity was increased instead of adding a duplicate row.`;
          return { ...prev, items: updatedItems };
        }

        successMessage = `${itemToAdd.productName} is ready in the quotation table.`;
        return { ...prev, items: [...prev.items, itemToAdd] };
      });

      if (duplicateMessage) {
        notify?.({
          tone: "neutral",
          title: "Item already exists, quantity updated",
          message: duplicateMessage,
        });
      } else if (successMessage) {
        notify?.({
          tone: "success",
          title: sourceLabel,
          message: successMessage,
        });
      }

      setQuery("");
      setSuggestions([]);
    },
    [activeRoom, notify]
  );

  const addSuggestionToDraft = useCallback(
    (suggestion) => {
      addItem(buildLineItemFromProduct(suggestion));
    },
    [addItem]
  );

  const addCustomProductToDraft = useCallback(() => {
    if (!customProduct.productName.trim()) {
      notify?.({
        tone: "warning",
        title: "Custom product name required",
        message: "Enter the product name before adding a custom item.",
      });
      return;
    }

    addItem(buildLineItemFromCustomProduct(customProduct), "Custom product added");
    setCustomProduct(emptyCustomProduct);
    setCustomProductOpen(false);
  }, [addItem, customProduct, notify]);

  const updateItem = useCallback((rowId, field, value) => {
    setDraft((prev) => ({
      ...prev,
      items: prev.items.map((item) => {
        if (item.rowId !== rowId) {
          return item;
        }

        if (field === "qty") {
          return { ...item, qty: Math.max(1, Number(value) || 1) };
        }
        if (field === "price") {
          return { ...item, price: Math.max(0, Number(value) || 0) };
        }
        if (field === "discountPercent") {
          return { ...item, discountPercent: Math.min(100, Math.max(0, Number(value) || 0)) };
        }
        return { ...item, [field]: value };
      }),
    }));
  }, []);

  const applyActiveRoomToAllItems = useCallback(() => {
    const roomName = String(activeRoom || "").trim();
    if (!roomName) {
      notify?.({
        tone: "warning",
        title: "Select a room first",
        message: "Choose a current room before applying it to existing products.",
      });
      return;
    }

    setDraft((prev) => ({
      ...prev,
      items: prev.items.map((item) => ({ ...item, roomName })),
    }));

    notify?.({
      tone: "success",
      title: "Room applied to all rows",
      message: `${roomName} has been applied to every existing product row.`,
    });
  }, [activeRoom, notify]);

  const removeItem = useCallback((rowId) => {
    setDraft((prev) => {
      if (!window.confirm("Delete this BOM row?")) {
        return prev;
      }
      return {
        ...prev,
        items: prev.items.filter((item) => item.rowId !== rowId),
      };
    });
  }, []);

  const persistQuote = useCallback(
    async (statusValue) => {
      // Ensure items is always an array
      const items = Array.isArray(draft.items) ? draft.items : [];
      
      if (items.length === 0) {
        notify?.({
          tone: "warning",
          title: "No items added",
          message: "Add at least one product before saving the quotation.",
        });
        return null;
      }

      const itemMissingRoom = items.find((item) => !String(item?.roomName || "").trim());
      if (itemMissingRoom) {
        notify?.({
          tone: "warning",
          title: "Room selection required",
          message: `Select a room for ${itemMissingRoom?.productName || "an item"} before saving the quotation.`,
        });
        return null;
      }

      setSaving(true);
      try {
        // Ensure items array is properly set before building payload
        const draftWithSafeItems = {
          ...draft,
          items: items,
          status: statusValue,
        };
        
        const payload = buildQuotationPayload(draftWithSafeItems);
        
        const localRecord = buildLocalQuoteRecord(
          {
            ...payload,
            proposal_no: formatScProposalNo(payload.proposal_no || draft.proposalNo, Date.now() % 10000),
          },
          statusValue,
          draft.draftId,
          quoteTotals
        );
        upsertLocalEntry(localStoreKeys.quotes, localRecord);
        const savedQuote = localRecord;

        setDraft((prev) => ({
          ...prev,
          ...mapQuoteToWorkspace(savedQuote),
          proposalNo: formatScProposalNo(savedQuote?.proposal_no || prev.proposalNo, Date.now() % 10000),
        }));
        setLastSavedAt(new Date());
        onQuoteSaved?.(savedQuote);
        notify?.({
          tone: "success",
          title: statusValue === "final" ? "Quotation saved and finalized" : "Draft saved successfully",
          message:
            statusValue === "final"
              ? `${savedQuote.proposal_no} saved as final quotation.`
              : "Draft saved successfully",
        });
        return savedQuote;
      } catch (error) {
        const errorMsg = error?.message || String(error);
        console.error("Save quotation error:", { error, errorMsg, draft });
        notify?.({
          tone: "warning",
          title: "Unable to save quotation",
          message: getErrorMessage(
            error,
            "Please review the proposal number, room selection, and item details, then try again."
          ),
        });
        return null;
      } finally {
        setSaving(false);
      }
    },
    [draft, notify, onQuoteSaved, quoteTotals]
  );

  const saveDraft = useCallback(async () => persistQuote("draft"), [persistQuote]);

  const viewPdf = useCallback(() => {
    const items = Array.isArray(draft.items) ? draft.items : [];
    
    if (items.length === 0) {
      notify?.({
        tone: "warning",
        title: "No items added",
        message: "Add at least one product before viewing the PDF.",
      });
      return;
    }

    const itemMissingRoom = items.find((item) => !String(item?.roomName || "").trim());
    if (!draft.quoteDate || itemMissingRoom) {
      notify?.({
        tone: "neutral",
        title: "Incomplete details",
        message: "Generating preview with missing date or room details.",
      });
    }

    if (showPdfModal) {
      showPdfModal(async () => {
        const payload = buildQuotationPayload({ ...draft, status: draft.status || "draft" });
        const currentHash = JSON.stringify(payload) + String(effectiveGstRate);

        if (pdfCacheRef.current.payloadString === currentHash && pdfCacheRef.current.blob) {
          return pdfCacheRef.current.blob;
        }

        const pdfBlob = await generateQuotationPDF(payload, {
          gstRate: effectiveGstRate,
          publicAssetBase: PUBLIC_ASSET_BASE_URL,
        });

        pdfCacheRef.current = { payloadString: currentHash, blob: pdfBlob };
        return pdfBlob;
      }, { filename: buildDownloadFileName(draft), isDraft: true });
    }
  }, [draft, notify, showPdfModal, effectiveGstRate]);

  const generatePdf = useCallback(async () => {
    const items = Array.isArray(draft.items) ? draft.items : [];
    
    if (items.length === 0) {
      notify?.({
        tone: "warning",
        title: "No items added",
        message: "Add at least one product before generating the PDF.",
      });
      return;
    }

    const savedQuote = await persistQuote("final");
    if (!savedQuote) {
      return;
    }

    setGeneratingPdf(true);
    try {
      const savedDraft = mapQuoteToWorkspace(savedQuote);
      const payload = buildQuotationPayload({ 
        ...draft, 
        ...savedDraft, 
        status: "final" 
      });
      const pdfBlob = await generateQuotationPDF(payload, {
        gstRate: draft.gstRate,
        publicAssetBase: PUBLIC_ASSET_BASE_URL,
      });
      
      // Build complete data for SharePanel with all client details
      const shareData = {
        pdfBlob: pdfBlob,
        pdfUrl: URL.createObjectURL(pdfBlob),
        proposalNo: savedQuote?.proposal_no || payload.proposal_no || draft.proposalNo || "",
        date: formatDateForInput(payload.date || draft.quoteDate),
        clientName: payload.client_name || draft.clientName || "",
        clientPhone: payload.phone || draft.phone || "",
        clientEmail: payload.email || draft.email || "",
        clientCompany: payload.company || draft.company || "",
        subtotal: quoteTotals.subtotal,
        discountValue: quoteTotals.discountAmount,
        gstRate: draft.gstRate,
        gstAmount: quoteTotals.gstAmount,
        grandTotal: quoteTotals.grandTotal,
        items: Array.isArray(payload.items) ? payload.items : [],
        applyGst: draft.gstEnabled !== false,
      };
      
      setSharePanel({
        isOpen: true,
        ...shareData,
      });
      downloadBlob(pdfBlob, buildDownloadFileName(savedQuote));
    } catch (error) {
      console.error("PDF generation error:", { error });
      notify?.({
        tone: "warning",
        title: "PDF generation failed",
        message: getErrorMessage(error, "The PDF could not be downloaded."),
      });
    } finally {
      setGeneratingPdf(false);
    }
  }, [draft, notify, persistQuote, quoteTotals]);

  const loadQuote = useCallback(
    async (quote, mode = "edit") => {
      if (!quote) {
        return;
      }

      if (mode === "duplicate") {
        const nextProposalNo = await requestFreshProposalNumber();
        const duplicated = mapQuoteToWorkspace(quote);
        const initialRoom =
          (Array.isArray(duplicated.items) ? duplicated.items : []).find((item) => String(item?.roomName || "").trim())
            ?.roomName || getDefaultRoom();
        // Ensure all array fields are initialized
        setDraft({
          ...duplicated,
          draftId: null,
          proposalNo: nextProposalNo,
          quoteDate: formatDateForInput(new Date()),
          status: "draft",
          items: Array.isArray(duplicated.items) ? duplicated.items : [],
        });
        setActiveRoom(initialRoom);
        notify?.({
          tone: "success",
          title: "Quotation duplicated",
          message: "A fresh draft was created with a new proposal number.",
        });
        return;
      }

      const loadedDraft = mapQuoteToWorkspace(quote);
      const initialRoom =
        (Array.isArray(loadedDraft.items) ? loadedDraft.items : []).find((item) => String(item?.roomName || "").trim())
          ?.roomName || getDefaultRoom();
      // Ensure all array fields are initialized when loading
      setDraft({
        ...loadedDraft,
        items: Array.isArray(loadedDraft.items) ? loadedDraft.items : [],
      });
      setActiveRoom(initialRoom);
    },
    [notify, requestFreshProposalNumber]
  );

  return {
    draft,
    activeRoom,
    setActiveRoom,
    applyActiveRoomToAllItems,
    quoteTotals,
    subtotal: quoteTotals.subtotal,
    discountAmount: quoteTotals.discountAmount,
    taxableSubtotal: quoteTotals.taxableSubtotal,
    gstAmount: quoteTotals.gstAmount,
    grandTotal: quoteTotals.grandTotal,
    query,
    setQuery,
    catalogFilter,
    setCatalogFilter,
    suggestions,
    searching,
    saving,
    generatingPdf,
    sharePanel,
    setSharePanel,
    lastSavedAt,
    initializing,
    customProductOpen,
    setCustomProductOpen,
    customProduct,
    setCustomProduct,
    startNewDraft,
    selectClient,
    updateDraftField,
    addSuggestionToDraft,
    addCustomProductToDraft,
    updateItem,
    removeItem,
    saveDraft,
    viewPdf,
    generatePdf,
    loadQuote,
    calculateLineTotal,
  };
}

