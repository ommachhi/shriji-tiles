import React, { useMemo, useState } from "react";
import { EmptyState, PageIntro, PanelCard, StatusBadge } from "../components/ui";
import { formatCurrency, formatDate, formatStatusLabel, quoteStatusOptions } from "../lib/constants";
import { useDebouncedValue } from "../hooks/useDebouncedValue";

function BomListPage({
  loading,
  quotes,
  onCreateQuotation,
  onViewQuotation,
  onEditQuotation,
  onDeleteQuotation,
  onDuplicateQuotation,
  onDownloadQuotation,
}) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const deferredQuery = useDebouncedValue(query, 300);

  const filteredQuotes = useMemo(() => {
    const normalizedQuery = deferredQuery.trim().toLowerCase();
    return (quotes || []).filter((quote) => {
      const matchesStatus = statusFilter === "all" || String(quote.status || "").toLowerCase() === statusFilter;
      if (!matchesStatus) {
        return false;
      }

      if (!normalizedQuery) {
        return true;
      }

      return [
        quote.proposal_no,
        quote.client_name,
        quote.company,
        quote.phone,
      ]
        .join(" ")
        .toLowerCase()
        .includes(normalizedQuery);
    });
  }, [deferredQuery, quotes, statusFilter]);

  return (
    <div className="page-stack">
      <PageIntro
        eyebrow="Saved records"
        title="Quotation library"
        description="Open, edit, duplicate, delete, or download any saved draft or final quotation from one register."
        actions={
          <button type="button" className="btn-primary" onClick={onCreateQuotation}>
            Create quotation
          </button>
        }
      />

      <PanelCard title="All quotations" subtitle="Search by proposal number, client, company, or phone number.">
        <div className="toolbar-row wrap">
          <input
            type="search"
            className="soft-input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search quotations..."
          />
          <div className="segmented-control">
            {quoteStatusOptions.map((option) => (
              <button
                key={option}
                type="button"
                className={statusFilter === option ? "segment is-active" : "segment"}
                onClick={() => setStatusFilter(option)}
              >
                {formatStatusLabel(option)}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="loading-panel">Loading quotations...</div>
        ) : filteredQuotes.length === 0 ? (
          <EmptyState
            title="No quotations found"
            description="Create a new quotation or broaden the current filters."
            action={
              <button type="button" className="btn-primary" onClick={onCreateQuotation}>
                Create quotation
              </button>
            }
          />
        ) : (
          <div className="quote-card-grid">
            {filteredQuotes.map((quote) => (
              <article key={quote.id} className="quote-card">
                <div className="quote-card-top">
                  <span className="quote-proposal">{quote.proposal_no}</span>
                  <StatusBadge value={quote.status} />
                </div>
                <div className="quote-card-body">
                  <strong>{quote.client_name || "Unnamed Client"}</strong>
                  <span>{quote.company || "-"}</span>
                  <span>{formatDate(quote.date)}</span>
                </div>
                <div className="quote-card-bottom">
                  <strong className="amount-cell">{formatCurrency(quote.total)}</strong>
                  <div className="inline-actions">
                    <button type="button" className="table-action" onClick={() => onEditQuotation(quote.id)}>Edit</button>
                    <button type="button" className="table-action" onClick={() => onDuplicateQuotation(quote.id)}>Duplicate</button>
                    <button type="button" className="table-action" onClick={() => onDownloadQuotation(quote.id)}>PDF</button>
                    <button type="button" className="table-action danger" onClick={() => onDeleteQuotation(quote.id)}>Delete</button>
                    <button type="button" className="table-action" onClick={() => onViewQuotation(quote.id)}>Open</button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </PanelCard>
    </div>
  );
}

export default BomListPage;
