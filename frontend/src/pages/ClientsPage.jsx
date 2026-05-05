import React, { useMemo, useState } from "react";
import { EmptyState, PageIntro, PanelCard } from "../components/ui";
import { useDebouncedValue } from "../hooks/useDebouncedValue";

const emptyClientForm = {
  id: "",
  client_name: "",
  company: "",
  phone: "",
  email: "",
  address: "",
  gst_rate: 18,
};

function ClientsPage({ loading, clients, onSaveClient, onDeleteClient }) {
  const [query, setQuery] = useState("");
  const [form, setForm] = useState(emptyClientForm);
  const deferredQuery = useDebouncedValue(query, 300);

  const filteredClients = useMemo(() => {
    const normalizedQuery = deferredQuery.trim().toLowerCase();
    if (!normalizedQuery) {
      return clients || [];
    }

    return (clients || []).filter((client) =>
      [client.client_name, client.company, client.phone, client.email]
        .join(" ")
        .toLowerCase()
        .includes(normalizedQuery)
    );
  }, [clients, deferredQuery]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.client_name.trim()) {
      return;
    }

    const saved = await onSaveClient(form);
    if (saved) {
      setForm(emptyClientForm);
    }
  };

  return (
    <div className="page-stack">
      <PageIntro
        eyebrow="Client directory"
        title="Clients"
        description="Store the client master once, then reuse it from the quotation page without retyping the basics."
      />

      <div className="management-grid">
        <PanelCard title="Saved clients" subtitle="Search existing clients and reopen them for edits.">
          <div className="toolbar-row">
            <input
              type="search"
              className="soft-input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search clients..."
            />
          </div>

          {loading ? (
            <div className="loading-panel">Loading clients...</div>
          ) : filteredClients.length === 0 ? (
            <EmptyState
              title="No clients found"
              description="Create a client record here or return to the quotation page and continue with a manual client snapshot."
            />
          ) : (
            <div className="client-card-list">
              {filteredClients.map((client) => (
                <article key={client.id} className="client-card" onClick={() => setForm(client)} role="button" tabIndex={0}>
                  <div className="client-avatar">{String(client.client_name || "C").slice(0, 1).toUpperCase()}</div>
                  <div className="client-copy">
                    <strong>{client.client_name}</strong>
                    <span>{client.company || "-"}</span>
                    <span>{client.phone || "-"}</span>
                  </div>
                  <button type="button" className="table-action danger" onClick={(event) => {
                    event.stopPropagation();
                    onDeleteClient(client.id);
                  }}>
                    Delete
                  </button>
                </article>
              ))}
            </div>
          )}
        </PanelCard>

        <PanelCard title={form.id ? "Edit client" : "Add client"} subtitle="This only changes the master client record. Saved quotations keep their own snapshots.">
          <form className="form-stack" onSubmit={handleSubmit}>
            <input
              className="soft-input"
              value={form.client_name}
              onChange={(event) => setForm((prev) => ({ ...prev, client_name: event.target.value }))}
              placeholder="Client name"
            />
            <input
              className="soft-input"
              value={form.company}
              onChange={(event) => setForm((prev) => ({ ...prev, company: event.target.value }))}
              placeholder="Company"
            />
            <input
              className="soft-input"
              value={form.phone}
              onChange={(event) => setForm((prev) => ({ ...prev, phone: event.target.value }))}
              placeholder="Phone"
            />
            <input
              className="soft-input"
              value={form.email}
              onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
              placeholder="Email"
            />
            <textarea
              className="soft-input soft-textarea"
              value={form.address}
              onChange={(event) => setForm((prev) => ({ ...prev, address: event.target.value }))}
              placeholder="Address"
            />
            <input
              className="soft-input"
              type="number"
              min="0"
              max="100"
              value={form.gst_rate ?? 18}
              onChange={(event) => setForm((prev) => ({ ...prev, gst_rate: Math.max(0, Math.min(100, Number(event.target.value) || 0)) }))}
              placeholder="GST %"
            />
            <div className="form-actions">
              {form.id ? (
                <button type="button" className="btn-secondary" onClick={() => setForm(emptyClientForm)}>
                  Cancel
                </button>
              ) : null}
              <button type="submit" className="btn-primary">
                {form.id ? "Update client" : "Add client"}
              </button>
            </div>
          </form>
        </PanelCard>
      </div>
    </div>
  );
}

export default ClientsPage;
