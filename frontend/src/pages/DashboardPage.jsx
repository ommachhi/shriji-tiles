import React from "react";
import { MetricCard, PageIntro, PanelCard, StatusBadge } from "../components/ui";
import {
  formatCompactCurrency,
  formatCurrency,
  formatDate,
} from "../lib/constants";
import { buildProductImageUrl, handleProductImageError } from "../lib/productUtils";

function DashboardPage({
  summary,
  recentQuotes,
  topProducts,
  onCreateQuote,
  onOpenBomList,
}) {
  return (
    <div className="page-stack">
      <PageIntro
        eyebrow="Control center"
        title="Dashboard"
        description="Monitor active quotations, client coverage, and the product lines creating the most revenue."
        actions={
          <>
            <button type="button" className="btn-secondary" onClick={onOpenBomList}>
              View BOM List
            </button>
            <button type="button" className="btn-primary" onClick={onCreateQuote}>
              Create New BOM
            </button>
          </>
        }
      />

      <div className="metrics-grid four-up">
        <MetricCard
          label="Total BOMs"
          value={summary.totalBoms}
          hint={`${summary.draftBoms} drafts in pipeline`}
          tone="blue"
        />
        <MetricCard
          label="Total Value"
          value={formatCompactCurrency(summary.totalValue)}
          hint={`Grand total ${formatCurrency(summary.totalValue)}`}
          tone="green"
        />
        <MetricCard
          label="Total Products"
          value={summary.totalProducts}
          hint="Across connected catalogs"
          tone="slate"
        />
        <MetricCard
          label="Total Clients"
          value={summary.totalClients}
          hint={`${summary.approvedBoms} approved quotations`}
          tone="violet"
        />
      </div>

      <div className="dashboard-content-grid">
        <PanelCard
          title="Recent BOM activity"
          subtitle="Latest quotation records and current follow-up status."
        >
          <div className="table-shell">
            <table className="data-table">
              <thead>
                <tr>
                  <th>BOM No</th>
                  <th>Client</th>
                  <th>Project</th>
                  <th>Date</th>
                  <th>Total</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {recentQuotes.map((quote) => (
                  <tr key={quote.id}>
                    <td className="code-cell">{quote.proposalNo}</td>
                    <td>{quote.clientName}</td>
                    <td>{quote.projectName}</td>
                    <td>{formatDate(quote.date)}</td>
                    <td className="amount-cell">{formatCurrency(quote.totalAmount)}</td>
                    <td>
                      <StatusBadge value={quote.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PanelCard>

        <div className="dashboard-side-stack">
          <PanelCard
            title="Top products"
            subtitle="Most active product lines across saved quotations."
          >
            <div className="product-highlight-list">
              {topProducts.map((product) => (
                <div key={product.code} className="product-highlight-row">
                  <img
                    src={buildProductImageUrl(product)}
                    alt=""
                    loading="lazy"
                    decoding="async"
                    className="product-mini-thumb"
                    onError={(event) => handleProductImageError(event, product)}
                  />
                  <div>
                    <strong>{product.name}</strong>
                    <span>
                      {product.code} · {product.category || "General"}
                    </span>
                  </div>
                  <div className="product-highlight-metric">
                    <strong>{product.count}x</strong>
                    <span>{formatCompactCurrency(product.value)}</span>
                  </div>
                </div>
              ))}
            </div>
          </PanelCard>

          <PanelCard
            title="Workflow snapshot"
            subtitle="High-level commercial pulse for the sales desk."
          >
            <div className="stacked-stats">
              <div className="stacked-stat-row">
                <span>Approved pipeline</span>
                <strong>{formatCurrency(summary.approvedValue)}</strong>
              </div>
              <div className="stacked-stat-row">
                <span>Sent quotations</span>
                <strong>{summary.sentBoms}</strong>
              </div>
              <div className="stacked-stat-row">
                <span>Average quote value</span>
                <strong>{formatCurrency(summary.averageQuoteValue)}</strong>
              </div>
            </div>
          </PanelCard>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
