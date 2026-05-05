import React from "react";
import { MetricCard, PageIntro, PanelCard } from "../components/ui";
import { formatCompactCurrency, formatCurrency } from "../lib/constants";

function ReportsPage({ reportMetrics, monthlyRevenue, topCategories }) {
  return (
    <div className="page-stack">
      <PageIntro
        eyebrow="Insights"
        title="Reports"
        description="Commercial trends, revenue movement, and category demand from saved quotations."
      />

      <div className="metrics-grid three-up">
        <MetricCard
          label="Revenue"
          value={formatCompactCurrency(reportMetrics.revenue)}
          hint={formatCurrency(reportMetrics.revenue)}
          tone="green"
        />
        <MetricCard
          label="Approved Quotes"
          value={reportMetrics.approvedCount}
          hint={`${reportMetrics.sentCount} sent to clients`}
          tone="blue"
        />
        <MetricCard
          label="Average BOM Value"
          value={formatCurrency(reportMetrics.averageValue)}
          hint={`${reportMetrics.quoteCount} total quotations`}
          tone="slate"
        />
      </div>

      <div className="dashboard-content-grid">
        <PanelCard title="Monthly revenue" subtitle="Value of saved quotations by month.">
          <div className="bar-list">
            {monthlyRevenue.map((entry) => (
              <div key={entry.month} className="bar-list-row">
                <div>
                  <strong>{entry.month}</strong>
                  <span>{formatCurrency(entry.value)}</span>
                </div>
                <div className="bar-track">
                  <span style={{ width: `${entry.percentage}%` }} />
                </div>
              </div>
            ))}
          </div>
        </PanelCard>

        <PanelCard title="Top categories" subtitle="Most valuable product categories across quotations.">
          <div className="bar-list compact">
            {topCategories.map((entry) => (
              <div key={entry.name} className="bar-list-row">
                <div>
                  <strong>{entry.name}</strong>
                  <span>{formatCurrency(entry.value)}</span>
                </div>
                <div className="bar-track">
                  <span style={{ width: `${entry.percentage}%` }} />
                </div>
              </div>
            ))}
          </div>
        </PanelCard>
      </div>
    </div>
  );
}

export default ReportsPage;
