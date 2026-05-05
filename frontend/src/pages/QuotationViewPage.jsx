import React from "react";
import { EmptyState, PageIntro, PanelCard, StatusBadge } from "../components/ui";
import { formatCurrency, formatDate } from "../lib/constants";
import { buildProductImageUrl, handleProductImageError } from "../lib/productUtils";
import { calculateQuoteTotals } from "../lib/quoteUtils";

function QuotationViewPage({ quote, onBack, onEdit, onDuplicate, onViewPdf, onDownload }) {
  if (!quote) {
    return (
      <div className="page-stack">
        <EmptyState
          title="Quotation not found"
          description="Open a quotation from the list to review it here."
          action={
            <button type="button" className="btn-secondary" onClick={onBack}>
              Back to quotations
            </button>
          }
        />
      </div>
    );
  }

  const totals = calculateQuoteTotals({
    items: quote.items,
    gstRate: Number(quote.gst_rate) || 0,
    discountType: quote.discount_type,
    discountValue: Number(quote.discount_value) || 0,
  });

  return (
    <div className="page-stack">
      <PageIntro
        eyebrow="Quotation"
        title={quote.proposal_no}
        description="Review the saved client snapshot, room-wise item allocation, and commercial totals before sharing the quotation."
        actions={
          <>
            <button type="button" className="btn-secondary" onClick={onBack}>
              Back
            </button>
            <button type="button" className="btn-ghost" onClick={() => onDuplicate(quote.id)}>
              Duplicate
            </button>
            <button type="button" className="btn-ghost" onClick={() => onViewPdf(quote.id)}>
              View PDF
            </button>
            <button type="button" className="btn-secondary" onClick={() => onDownload(quote.id)}>
              Download PDF
            </button>
            <button type="button" className="btn-primary" onClick={() => onEdit(quote.id)}>
              Edit quotation
            </button>
          </>
        }
      />

      <div className="detail-layout">
        <PanelCard
          title="Client details"
          subtitle="This quotation keeps its own client snapshot so later client edits do not overwrite saved history."
        >
          <div className="detail-grid">
            <div className="detail-block">
              <span>Client Name</span>
              <strong>{quote.client_name}</strong>
            </div>
            <div className="detail-block">
              <span>Company</span>
              <strong>{quote.company || "-"}</strong>
            </div>
            <div className="detail-block">
              <span>Phone</span>
              <strong>{quote.phone || "-"}</strong>
            </div>
            <div className="detail-block">
              <span>Email</span>
              <strong>{quote.email || "-"}</strong>
            </div>
            <div className="detail-block">
              <span>Date</span>
              <strong>{formatDate(quote.date)}</strong>
            </div>
            <div className="detail-block">
              <span>Status</span>
              <StatusBadge value={quote.status} />
            </div>
            <div className="detail-block">
              <span>Discount Mode</span>
              <strong>{quote.discount_type || "item-wise"}</strong>
            </div>
            <div className="detail-block">
              <span>Discount Value</span>
              <strong>
                {quote.discount_type === "common-percentage"
                  ? `${Number(quote.discount_value) || 0}%`
                  : quote.discount_type === "on-total"
                    ? formatCurrency(quote.discount_value)
                    : "Per item"}
              </strong>
            </div>
            <div className="detail-block span-2">
              <span>Address</span>
              <strong>{quote.address || "-"}</strong>
            </div>
            <div className="detail-block">
              <span>Prepared By</span>
              <strong>{quote.prepared_by || quote.preparedBy || "-"}</strong>
            </div>
            <div className="detail-block">
              <span>Prepared Phone</span>
              <strong>{quote.prepared_phone || quote.preparedPhone || "-"}</strong>
            </div>
          </div>
        </PanelCard>

        <PanelCard title="Totals" subtitle="Commercial summary of the saved quotation.">
          <div className="summary-list compact">
            <div className="summary-line">
              <span>Subtotal</span>
              <strong>{formatCurrency(totals.subtotal)}</strong>
            </div>
            <div className="summary-line">
              <span>Discount</span>
              <strong>{formatCurrency(totals.discountAmount)}</strong>
            </div>
            <div className="summary-line">
              <span>Net taxable</span>
              <strong>{formatCurrency(totals.taxableSubtotal)}</strong>
            </div>
            <div className="summary-line">
              <span>GST ({Number(quote.gst_rate) || 0}%)</span>
              <strong>{formatCurrency(totals.gstAmount)}</strong>
            </div>
            <div className="summary-line total">
              <span>Grand Total</span>
              <strong>{formatCurrency(quote.total)}</strong>
            </div>
          </div>
        </PanelCard>
      </div>

      <PanelCard
        title="Items"
        subtitle="Saved line items remain fixed for this quotation even if the source catalog changes later."
      >
        <div className="table-shell">
          <table className="data-table quote-table">
            <thead>
              <tr>
                <th>Image</th>
                <th>Product Name</th>
                <th>Room</th>
                <th>Qty</th>
                <th>Price</th>
                <th>Discount %</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {(quote.items || []).map((item) => (
                <tr key={item.id}>
                  <td className="quote-image-cell">
                    <img
                      src={buildProductImageUrl({
                        name: item.product_name,
                        image: item.product_image,
                      })}
                      alt=""
                      className="quote-thumb"
                      onError={(event) =>
                        handleProductImageError(event, {
                          name: item.product_name,
                          image: item.product_image,
                        })
                      }
                    />
                  </td>
                  <td>
                    <div className="table-product-cell">
                      <strong>{item.product_name}</strong>
                      <span>
                        {item.product_code || "CUSTOM"}
                        {item.brand ? ` | ${item.brand}` : ""}
                      </span>
                    </div>
                  </td>
                  <td>{item.room_name || "-"}</td>
                  <td>{item.qty}</td>
                  <td className="amount-cell">{formatCurrency(item.price)}</td>
                  <td>{Number(item.discount_percent) || 0}%</td>
                  <td className="amount-cell">{formatCurrency(item.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PanelCard>
    </div>
  );
}

export default QuotationViewPage;
