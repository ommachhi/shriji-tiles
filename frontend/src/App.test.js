import { render, screen, waitFor } from "@testing-library/react";
import App from "./App";
import { generateQuotationPDF } from "./pdf/quotationPdf";

jest.mock("./lib/api", () => ({
  fetchClients: jest.fn(() => Promise.resolve({ results: [] })),
  fetchManagedProducts: jest.fn(() => Promise.resolve({ results: [] })),
  fetchQuotations: jest.fn(() => Promise.resolve({ results: [] })),
  fetchQuotationProposalNumber: jest.fn(() => Promise.resolve({ proposal_no: "PROP-20260428-001" })),
  fetchAutocompleteSuggestions: jest.fn(() => Promise.resolve({ suggestions: [] })),
  fetchQuotationPdf: jest.fn(() => Promise.resolve(new Blob(["pdf"]))),
  createQuotation: jest.fn(),
  updateQuotation: jest.fn(),
  fetchQuotation: jest.fn(),
  getQuotationPdfUrl: jest.fn(() => "http://127.0.0.1:8001/quotations/1/pdf"),
  createClient: jest.fn(),
  updateClient: jest.fn(),
  deleteClient: jest.fn(),
  createManagedProduct: jest.fn(),
  updateManagedProduct: jest.fn(),
  deleteManagedProduct: jest.fn(),
  deleteQuotation: jest.fn(),
  getErrorMessage: jest.fn((error, fallback) => fallback || "Error"),
}));

test("renders the create quotation workspace", async () => {
  window.location.hash = "#create-bom";
  render(<App />);

  expect(
    screen.getByText(/quotation management system/i)
  ).toBeInTheDocument();

  await waitFor(() => {
    expect(screen.getByRole("heading", { name: /create quotation/i })).toBeInTheDocument();
  });

  expect(screen.getByPlaceholderText(/search by code, product name/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /save draft/i })).toBeInTheDocument();
});

test("generates a non-empty quotation pdf blob", async () => {
  const blob = await generateQuotationPDF(
    {
      clientInfo: {
        clientName: "Sample Client",
        mobile: "9999999999",
        company: "Sample Company",
        address: "Sample address",
        preparedBy: "Jagdish",
      },
      proposalNo: "PRO-TEST",
      date: "2026-04-20",
      products: [
        {
          name: "Wall Hung Basin",
          details: "Premium ceramic finish",
          sku: "SKU-101",
          size: "600 x 450 mm",
          qty: 2,
          rate: 12500,
          discount: 10,
          room: ["Kids Bathroom", "Master Bathroom"],
        },
      ],
    },
    { branding: true }
  );

  expect(blob).toBeInstanceOf(Blob);
  expect(blob.size).toBeGreaterThan(1000);
});
