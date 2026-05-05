import React, { startTransition, useCallback, useEffect, useRef, useState } from "react";
import "./App.css";
import AppShell from "./components/AppShell";
import { ToastContainer } from "./components/ToastContainer";
import { useBomWorkspace } from "./hooks/useBomWorkspace";
import { useToast } from "./hooks/useToast";
import {
  createClient,
  createManagedProduct,
  deleteClient,
  deleteManagedProduct,
  deleteQuotation,
  fetchClients,
  fetchManagedProducts,
  fetchQuotation,
  fetchQuotationPdf,
  fetchQuotations,
  getErrorMessage,
  updateClient,
  updateManagedProduct,
} from "./lib/api";
import { getPageFromHash, PUBLIC_ASSET_BASE_URL } from "./lib/constants";
import { generateQuotationPDF } from "./pdf/quotationPdf";
import { PdfModal } from "./components/PdfModal";
import { appendLocalEntry, localStoreKeys, readLocalCollection, removeLocalEntry, upsertLocalEntry } from "./lib/localStore";

import CreateBomPage from "./pages/CreateBomPage";
import BomListPage from "./pages/BomListPage";
import ClientsPage from "./pages/ClientsPage";
import ProductsPage from "./pages/ProductsPage";
import QuotationViewPage from "./pages/QuotationViewPage";

function sortQuotesByDate(quotes) {
  return [...quotes].sort((left, right) => {
    const leftTime = new Date(left.date || left.created_at || 0).getTime();
    const rightTime = new Date(right.date || right.created_at || 0).getTime();
    return rightTime - leftTime;
  });
}

function mergeById(localArray, remoteArray) {
  const idMap = {};
  (remoteArray || []).forEach((item) => {
    idMap[item.id] = item;
  });
  (localArray || []).forEach((item) => {
    if (item.id && !idMap[item.id]) {
      idMap[item.id] = item;
    }
  });
  return Object.values(idMap);
}

function isNumericId(value) {
  return /^\d+$/.test(String(value || "").trim());
}

function buildClientSnapshotFromQuote(quote) {
  const clientName = String(quote?.client_name || quote?.clientName || "").trim();
  const phone = String(quote?.phone || "").trim();
  const email = String(quote?.email || "").trim();
  const address = String(quote?.address || "").trim();
  const company = String(quote?.company || "").trim();
  const clientId = quote?.client_id ?? quote?.clientId ?? null;

  if (!clientName && !phone && !email && !address && !company) {
    return null;
  }

  return {
    id: clientId ? String(clientId) : `local-client-${String(quote?.id || Date.now())}`,
    client_name: clientName || phone || "Client",
    company,
    phone,
    email,
    address,
    gst_rate: Number(quote?.gst_rate ?? quote?.gstRate ?? 18) || 18,
  };
}

function toPlainNoticeText(value) {
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map((item) => toPlainNoticeText(item)).filter(Boolean).join("; ");
  }
  if (value && typeof value === "object") {
    return value.msg || value.message || value.detail || JSON.stringify(value);
  }
  return value == null ? "" : String(value);
}

function buildPdfDownloadName(quote) {
  return `${String(quote?.proposal_no || "quotation")
    .replace(/[^a-z0-9_.-]+/gi, "_")
    .replace(/^_+|_+$/g, "") || "quotation"}.pdf`;
}

function getLocalQuoteById(quoteId) {
  if (!quoteId) {
    return null;
  }

  const localQuotes = readLocalCollection(localStoreKeys.quotes);
  return (Array.isArray(localQuotes) ? localQuotes : []).find((quote) => String(quote.id) === String(quoteId)) || null;
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



function App() {
  const [activePage, setActivePage] = useState(() => getPageFromHash());
  const [clients, setClients] = useState([]);
  const [products, setProducts] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [selectedQuote, setSelectedQuote] = useState(null);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [notice, setNotice] = useState(null);
  const [pdfModal, setPdfModal] = useState({ isOpen: false, loading: false, url: null, error: null, filename: null, isDraft: false, retryFn: null });
  const quoteCacheRef = useRef({});
  const pdfCacheRef = useRef({});
  const { toasts, showToast, dismissToast } = useToast();

  const notify = useCallback((payload) => {
    const safePayload = payload
      ? {
          ...payload,
          title: toPlainNoticeText(payload.title),
          message: toPlainNoticeText(payload.message),
        }
      : payload;
    setNotice(safePayload);
    if (payload?.title || payload?.message) {
      const toastMessage = [toPlainNoticeText(payload.title), toPlainNoticeText(payload.message)].filter(Boolean).join(": ") || "Notification";
      showToast(toastMessage, payload.tone || "info");
    }
  }, [showToast]);

  const showPdfModal = useCallback((generatorFn, options = {}) => {
    const { filename, isDraft } = options;
    
    const execute = async () => {
      setPdfModal({ isOpen: true, loading: true, url: null, error: null, filename, isDraft, retryFn: execute });
      try {
        const blob = await generatorFn();
        const url = window.URL.createObjectURL(blob);
        setPdfModal((prev) => prev.isOpen ? { ...prev, loading: false, url, error: null } : prev);
      } catch (err) {
        setPdfModal((prev) => prev.isOpen ? { ...prev, loading: false, url: null, error: getErrorMessage(err, "Failed to generate PDF") } : prev);
      }
    };
    
    execute();
  }, []);

  const closePdfModal = useCallback(() => {
    setPdfModal(prev => {
      if (prev.url) window.URL.revokeObjectURL(prev.url);
      return { isOpen: false, loading: false, url: null, error: null, filename: null, isDraft: false, retryFn: null };
    });
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    if (!window.location.hash) {
      window.location.hash = activePage;
    }

    const handleHashChange = () => setActivePage(getPageFromHash());
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, [activePage]);

  useEffect(() => {
    if (!notice) {
      return undefined;
    }

    const timer = window.setTimeout(() => setNotice(null), 5000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const navigateTo = useCallback((pageId) => {
    if (typeof window !== "undefined" && window.location.hash !== `#${pageId}`) {
      window.location.hash = pageId;
    }
    startTransition(() => setActivePage(pageId));
  }, []);

  const upsertQuote = useCallback((quote) => {
    if (!quote?.id) {
      return;
    }
    quoteCacheRef.current[quote.id] = quote;
    upsertLocalEntry(localStoreKeys.quotes, quote);
    const clientSnapshot = buildClientSnapshotFromQuote(quote);
    if (clientSnapshot) {
      if (quote?.client_id || quote?.clientId) {
        upsertLocalEntry(localStoreKeys.clients, clientSnapshot);
        setClients((prev) =>
          [...prev.filter((client) => String(client.id) !== String(clientSnapshot.id)), clientSnapshot].sort((left, right) =>
            String(left.client_name || "").localeCompare(String(right.client_name || ""))
          )
        );
      } else {
        appendLocalEntry(localStoreKeys.clients, clientSnapshot);
        setClients((prev) => [clientSnapshot, ...prev].sort((left, right) =>
          String(left.client_name || "").localeCompare(String(right.client_name || ""))
        ));
      }
    }
    setQuotes((prev) => sortQuotesByDate([quote, ...prev.filter((entry) => entry.id !== quote.id)]));
    setSelectedQuote((prev) => (prev?.id === quote.id ? quote : prev));
  }, []);

  const getQuotationDetail = useCallback(async (quotationId) => {
    const cachedQuote = quoteCacheRef.current[quotationId];
    if (cachedQuote) {
      return cachedQuote;
    }

    const localQuote = quotes.find((quote) => String(quote.id) === String(quotationId)) || getLocalQuoteById(quotationId);
    if (localQuote) {
      quoteCacheRef.current[quotationId] = localQuote;
      return localQuote;
    }

    if (!isNumericId(quotationId)) {
      throw new Error("Local quotation not found.");
    }

    const detail = await fetchQuotation(Number(quotationId));
    quoteCacheRef.current[quotationId] = detail;
    return detail;
  }, [quotes]);

  const workspace = useBomWorkspace({
    clients,
    onQuoteSaved: upsertQuote,
    notify,
    showPdfModal,
  });

  const loadInitialData = useCallback(async () => {
    setBootstrapping(true);
    const cachedClients = readLocalCollection(localStoreKeys.clients);
    const cachedProducts = readLocalCollection(localStoreKeys.products);
    const cachedQuotes = readLocalCollection(localStoreKeys.quotes);
    setClients(Array.isArray(cachedClients) ? cachedClients : []);
    setProducts(Array.isArray(cachedProducts) ? cachedProducts : []);
    setQuotes(sortQuotesByDate(Array.isArray(cachedQuotes) ? cachedQuotes : []));
    try {
      const [clientResponse, productResponse, quoteResponse] = await Promise.all([
        fetchClients(),
        fetchManagedProducts(),
        fetchQuotations(),
      ]);

      const remoteClients = Array.isArray(clientResponse?.results) ? clientResponse.results : [];
      const remoteProducts = Array.isArray(productResponse?.results) ? productResponse.results : [];
      const remoteQuotes = Array.isArray(quoteResponse?.results) ? quoteResponse.results : [];

      const mergedClients = mergeById(cachedClients, remoteClients);
      setClients(mergedClients);
      setProducts(remoteProducts);
      const mergedQuotes = mergeById(cachedQuotes, remoteQuotes);
      setQuotes(sortQuotesByDate(mergedQuotes));
      
      remoteClients.forEach((client) => upsertLocalEntry(localStoreKeys.clients, client));
      remoteProducts.forEach((product) => upsertLocalEntry(localStoreKeys.products, product));
      remoteQuotes.forEach((quote) => upsertLocalEntry(localStoreKeys.quotes, quote));
    } catch (error) {
      notify({
        tone: "warning",
        title: "Unable to load the BOM system",
        message: getErrorMessage(error, "Loaded the latest local cache. Check backend connection and refresh."),
      });
    } finally {
      setBootstrapping(false);
    }
  }, [notify]);

  useEffect(() => {
    void loadInitialData();
  }, [loadInitialData]);

  const handleCreateQuotation = useCallback(async () => {
    await workspace.startNewDraft();
    navigateTo("create-bom");
  }, [navigateTo, workspace]);

  const handleViewQuotation = useCallback(async (quotationId) => {
    try {
      const detail = await getQuotationDetail(quotationId);
      setSelectedQuote(detail);
      navigateTo("quotation-view");
    } catch (error) {
      notify({
        tone: "warning",
        title: "Unable to open quotation",
        message: getErrorMessage(error, "Please try again."),
      });
    }
  }, [getQuotationDetail, navigateTo, notify]);

  const handleEditQuotation = useCallback(async (quotationId) => {
    try {
      const detail = await getQuotationDetail(quotationId);
      await workspace.loadQuote(detail, "edit");
      navigateTo("create-bom");
    } catch (error) {
      notify({
        tone: "warning",
        title: "Unable to load quotation",
        message: getErrorMessage(error, "Please try again."),
      });
    }
  }, [getQuotationDetail, navigateTo, notify, workspace]);

  const handleDuplicateQuotation = useCallback(async (quotationId) => {
    try {
      const detail = await getQuotationDetail(quotationId);
      await workspace.loadQuote(detail, "duplicate");
      navigateTo("create-bom");
    } catch (error) {
      notify({
        tone: "warning",
        title: "Unable to duplicate quotation",
        message: getErrorMessage(error, "Please try again."),
      });
    }
  }, [getQuotationDetail, navigateTo, notify, workspace]);

  const handleDownloadQuotation = useCallback(async (quotationId) => {
    try {
      const detail = await getQuotationDetail(quotationId);
      if (isNumericId(quotationId)) {
        try {
          const pdfBlob = await fetchQuotationPdf(Number(quotationId));
          downloadBlob(pdfBlob, buildPdfDownloadName(detail));
          return;
        } catch (pdfError) {
          notify({ tone: "neutral", title: "Using local generation", message: "Backend unreachable, generating PDF locally." });
        }
      }

      const pdfBlob = await generateQuotationPDF(detail, {
        gstRate: detail.gst_rate || 18,
        publicAssetBase: PUBLIC_ASSET_BASE_URL,
      });
      downloadBlob(pdfBlob, buildPdfDownloadName(detail));
    } catch (error) {
      notify({
        tone: "warning",
        title: "Unable to download PDF",
        message: getErrorMessage(error, "Please try again."),
      });
    }
  }, [getQuotationDetail, notify]);

  const handleViewQuotationPdf = useCallback(async (quotationId) => {
    try {
      const detail = await getQuotationDetail(quotationId);
      const filename = buildPdfDownloadName(detail);
      
      showPdfModal(async () => {
        const currentHash = `${quotationId}-${detail.updated_at || detail.id}`;
        if (pdfCacheRef.current[currentHash]) {
          return pdfCacheRef.current[currentHash];
        }

        let pdfBlob;
        if (isNumericId(quotationId)) {
          try {
            pdfBlob = await fetchQuotationPdf(Number(quotationId));
          } catch (pdfError) {
            notify({ tone: "neutral", title: "Using local generation", message: "Backend unreachable, generating PDF locally." });
          }
        }

        if (!pdfBlob) {
          pdfBlob = await generateQuotationPDF(detail, {
            gstRate: detail.gst_rate || 18,
            publicAssetBase: PUBLIC_ASSET_BASE_URL,
          });
        }
        
        pdfCacheRef.current[currentHash] = pdfBlob;
        return pdfBlob;
      }, { filename, isDraft: false });
    } catch (error) {
      notify({
        tone: "warning",
        title: "Unable to open quotation PDF",
        message: getErrorMessage(error, "Please try again."),
      });
    }
  }, [getQuotationDetail, notify, showPdfModal]);

  const handleDeleteQuotation = useCallback(async (quotationId) => {
    if (!window.confirm("Delete this quotation permanently?")) {
      return;
    }

    try {
      if (isNumericId(quotationId)) {
        await deleteQuotation(Number(quotationId));
      }
      delete quoteCacheRef.current[quotationId];
      removeLocalEntry(localStoreKeys.quotes, quotationId);
      setQuotes((prev) => prev.filter((quote) => quote.id !== quotationId));
      setSelectedQuote((prev) => (prev?.id === quotationId ? null : prev));
      notify({
        tone: "success",
        title: "Quotation deleted",
        message: "The quotation was removed successfully.",
      });
      if (activePage === "quotation-view") {
        navigateTo("quotations");
      }
    } catch (error) {
      notify({
        tone: "warning",
        title: "Unable to delete quotation",
        message: getErrorMessage(error, "Please try again."),
      });
    }
  }, [activePage, navigateTo, notify]);

  const handleSaveClient = useCallback(async (form) => {
    try {
      const savedClient = form.id
        ? await updateClient(form.id, form)
        : await createClient(form);

      setClients((prev) =>
        [...prev.filter((client) => client.id !== savedClient.id), savedClient].sort((left, right) =>
          String(left.client_name || "").localeCompare(String(right.client_name || ""))
        )
      );
      upsertLocalEntry(localStoreKeys.clients, savedClient);
      notify({
        tone: "success",
        title: form.id ? "Client updated" : "Client created",
        message: `${savedClient.client_name} is ready to use in quotations.`,
      });
      return savedClient;
    } catch (error) {
      notify({
        tone: "warning",
        title: "Unable to save client",
        message: getErrorMessage(error, "Please review the client details and try again."),
      });
      return null;
    }
  }, [notify]);

  const handleDeleteClient = useCallback(async (clientId) => {
    if (!window.confirm("Delete this client from the master list?")) {
      return;
    }

    try {
      await deleteClient(clientId);
      setClients((prev) => prev.filter((client) => client.id !== clientId));
      removeLocalEntry(localStoreKeys.clients, clientId);
      notify({
        tone: "success",
        title: "Client deleted",
        message: "The client record was removed successfully.",
      });
    } catch (error) {
      notify({
        tone: "warning",
        title: "Unable to delete client",
        message: getErrorMessage(error, "This client may be linked to saved quotations."),
      });
    }
  }, [notify]);

  const handleSaveProduct = useCallback(async (form) => {
    try {
      const savedProduct = form.id
        ? await updateManagedProduct(form.id, form)
        : await createManagedProduct(form);

      setProducts((prev) =>
        [...prev.filter((product) => product.id !== savedProduct.id), savedProduct].sort((left, right) =>
          String(left.product_code || "").localeCompare(String(right.product_code || ""))
        )
      );
      upsertLocalEntry(localStoreKeys.products, savedProduct);
      notify({
        tone: "success",
        title: form.id ? "Product updated" : "Product created",
        message: `${savedProduct.product_code} is now available in managed search.`,
      });
      return savedProduct;
    } catch (error) {
      notify({
        tone: "warning",
        title: "Unable to save product",
        message: getErrorMessage(error, "Check that the product code is unique and try again."),
      });
      return null;
    }
  }, [notify]);

  const handleDeleteProduct = useCallback(async (productId) => {
    if (!window.confirm("Delete this managed product?")) {
      return;
    }

    try {
      await deleteManagedProduct(productId);
      setProducts((prev) => prev.filter((product) => product.id !== productId));
      removeLocalEntry(localStoreKeys.products, productId);
      notify({
        tone: "success",
        title: "Product deleted",
        message: "The managed product was removed successfully.",
      });
    } catch (error) {
      notify({
        tone: "warning",
        title: "Unable to delete product",
        message: getErrorMessage(error, "Please try again."),
      });
    }
  }, [notify]);

  let pageContent = null;
  if (activePage === "quotations") {
    pageContent = (
      <BomListPage
        loading={bootstrapping}
        quotes={quotes}
        onCreateQuotation={handleCreateQuotation}
        onViewQuotation={handleViewQuotation}
        onEditQuotation={handleEditQuotation}
        onDeleteQuotation={handleDeleteQuotation}
        onDuplicateQuotation={handleDuplicateQuotation}
        onDownloadQuotation={handleDownloadQuotation}
      />
    );
  } else if (activePage === "clients") {
    pageContent = (
      <ClientsPage
        loading={bootstrapping}
        clients={clients}
        onSaveClient={handleSaveClient}
        onDeleteClient={handleDeleteClient}
      />
    );
  } else if (activePage === "products") {
    pageContent = (
      <ProductsPage
        loading={bootstrapping}
        products={products}
        onSaveProduct={handleSaveProduct}
        onDeleteProduct={handleDeleteProduct}
      />
    );
  } else if (activePage === "quotation-view") {
    pageContent = (
      <QuotationViewPage
        quote={selectedQuote}
        onBack={() => navigateTo("quotations")}
        onEdit={handleEditQuotation}
        onDuplicate={handleDuplicateQuotation}
        onViewPdf={handleViewQuotationPdf}
        onDownload={handleDownloadQuotation}
      />
    );
  } else {
    pageContent = (
      <CreateBomPage
        workspace={workspace}
        clients={clients}
        onOpenList={() => navigateTo("quotations")}
        onOpenClients={() => navigateTo("clients")}
        onOpenProducts={() => navigateTo("products")}
      />
    );
  }

  return (
    <>
      <AppShell
        activePage={activePage}
        onNavigate={navigateTo}
        notice={notice}
        onDismissNotice={() => setNotice(null)}
      >
        {pageContent}
      </AppShell>
      <PdfModal
        isOpen={pdfModal.isOpen}
        loading={pdfModal.loading}
        url={pdfModal.url}
        error={pdfModal.error}
        filename={pdfModal.filename}
        isDraft={pdfModal.isDraft}
        retryFn={pdfModal.retryFn}
        onClose={closePdfModal}
      />
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </>
  );
}

export default App;
