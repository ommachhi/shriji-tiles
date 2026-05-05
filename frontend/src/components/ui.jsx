import React from "react";

function PageIntroComponent({ eyebrow, title, description, actions }) {
  return (
    <div className="page-intro">
      <div>
        <span className="page-intro-eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions ? <div className="page-intro-actions">{actions}</div> : null}
    </div>
  );
}

function PanelCardComponent({ title, subtitle, action, className = "", children }) {
  return (
    <section className={`panel-card ${className}`.trim()}>
      {(title || subtitle || action) && (
        <div className="panel-card-head">
          <div>
            {title ? <h2>{title}</h2> : null}
            {subtitle ? <p>{subtitle}</p> : null}
          </div>
          {action ? <div className="panel-card-action">{action}</div> : null}
        </div>
      )}
      {children}
    </section>
  );
}

function MetricCardComponent({ label, value, hint, tone = "blue" }) {
  return (
    <div className={`metric-card tone-${tone}`}>
      <span className="metric-label">{label}</span>
      <strong>{value}</strong>
      {hint ? <span className="metric-hint">{hint}</span> : null}
    </div>
  );
}

function StatusBadgeComponent({ value }) {
  const normalized = String(value || "").trim().toLowerCase();
  const tone =
    normalized === "approved" || normalized === "final"
      ? "success"
      : normalized === "sent"
        ? "info"
        : normalized === "draft"
          ? "neutral"
          : "neutral";

  return <span className={`status-badge tone-${tone}`}>{value || "Unknown"}</span>;
}

function EmptyStateComponent({ title, description, action }) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      <p>{description}</p>
      {action ? <div>{action}</div> : null}
    </div>
  );
}

export const PageIntro = React.memo(PageIntroComponent);
export const PanelCard = React.memo(PanelCardComponent);
export const MetricCard = React.memo(MetricCardComponent);
export const StatusBadge = React.memo(StatusBadgeComponent);
export const EmptyState = React.memo(EmptyStateComponent);
