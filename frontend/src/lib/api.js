import axios from "axios";
import { BACKEND_BASE_URL } from "./constants";

export const api = axios.create({
  baseURL: BACKEND_BASE_URL,
  timeout: 30000,
});

function normalizeErrorText(value) {
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value)) {
    return value
      .map((item) => normalizeErrorText(item))
      .filter(Boolean)
      .join("; ");
  }
  if (value && typeof value === "object") {
    return (
      value.msg ||
      value.message ||
      value.detail ||
      [value.loc, value.input].filter(Boolean).join(" ") ||
      JSON.stringify(value)
    );
  }
  return "";
}

export function getErrorMessage(error, fallback = "Something went wrong. Please try again.") {
  return (
    normalizeErrorText(error?.response?.data?.detail) ||
    normalizeErrorText(error?.response?.data?.message) ||
    normalizeErrorText(error?.response?.data) ||
    normalizeErrorText(error?.message) ||
    fallback
  );
}

export async function fetchClients(params = {}) {
  const response = await api.get("/clients", { params });
  return response.data;
}

export async function createClient(payload) {
  const response = await api.post("/clients", payload);
  return response.data;
}

export async function updateClient(clientId, payload) {
  const response = await api.put(`/clients/${clientId}`, payload);
  return response.data;
}

export async function deleteClient(clientId) {
  await api.delete(`/clients/${clientId}`);
}

export async function fetchManagedProducts(params = {}) {
  const response = await api.get("/products", { params });
  return response.data;
}

export async function createManagedProduct(payload) {
  const response = await api.post("/products", payload);
  return response.data;
}

export async function updateManagedProduct(productId, payload) {
  const response = await api.put(`/products/${productId}`, payload);
  return response.data;
}

export async function deleteManagedProduct(productId) {
  await api.delete(`/products/${productId}`);
}

export async function fetchQuotationProposalNumber() {
  const response = await api.get("/quotations/next-proposal");
  return response.data;
}

export async function fetchQuotations(params = {}) {
  const response = await api.get("/quotations", { params });
  return response.data;
}

export async function fetchQuotation(quotationId) {
  const response = await api.get(`/quotations/${quotationId}`);
  return response.data;
}

export function getQuotationPdfUrl(quotationId) {
  return `${BACKEND_BASE_URL}/quotations/${quotationId}/pdf`;
}

export async function fetchQuotationPdf(quotationId) {
  const response = await api.get(`/quotations/${quotationId}/pdf`, {
    responseType: "blob",
  });
  return response.data;
}

export async function createQuotation(payload) {
  const response = await api.post("/quotations", payload);
  return response.data;
}

export async function updateQuotation(quotationId, payload) {
  const response = await api.put(`/quotations/${quotationId}`, payload);
  return response.data;
}

export async function deleteQuotation(quotationId) {
  await api.delete(`/quotations/${quotationId}`);
}

export async function fetchAutocompleteSuggestions(params = {}) {
  const response = await api.get("/autocomplete", { params });
  return response.data;
}

export async function saveDraft(payload) {
  const response = await api.post("/quotations", payload);
  return response.data;
}
