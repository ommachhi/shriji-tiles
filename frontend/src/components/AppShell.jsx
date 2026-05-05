import React, { startTransition } from "react";
import { navigationItems } from "../lib/constants";

function AppShell({ activePage, onNavigate, notice, onDismissNotice, children }) {
  const navActivePage = activePage === "quotation-view" ? "quotations" : activePage;

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="brand-block">
          <div className="brand-mark">SK</div>
          <div>
            <strong>Shriiji Ceramika</strong>
            <span>Premium quotation system</span>
          </div>
        </div>

        <nav className="app-nav" aria-label="Primary">
          {navigationItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={navActivePage === item.id ? "nav-button is-active" : "nav-button"}
              aria-current={navActivePage === item.id ? "page" : undefined}
              onClick={() => startTransition(() => onNavigate(item.id))}
            >
              <span className="nav-short">{item.short}</span>
              <span className="nav-copy">
                <strong>{item.label}</strong>
                <small>{item.caption}</small>
              </span>
            </button>
          ))}
        </nav>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <div>
            <span className="topbar-kicker">Quotation Builder</span>
            <strong>Shriiji Ceramika</strong>
          </div>
        </header>

        {notice ? (
          <div className={`notice-banner tone-${notice.tone || "neutral"}`}>
            <div>
              <strong>{notice.title}</strong>
              <p>{notice.message}</p>
            </div>
            <button type="button" className="notice-close" onClick={onDismissNotice}>
              Close
            </button>
          </div>
        ) : null}

        <main className="app-content">{children}</main>
      </div>
    </div>
  );
}

export default AppShell;
