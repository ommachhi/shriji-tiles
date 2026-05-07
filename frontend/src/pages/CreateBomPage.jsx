import React, { useEffect } from "react";
import { DropdownSelect } from "../components/DropdownSelect";
import { EmptyState, PageIntro, PanelCard } from "../components/ui";
import {
  catalogOptions,
  discountTypeOptions,
  formatCurrency,
  getClientDisplayLabel,
  preparedByOptions,
  roomOptions,
} from "../lib/constants";
import { buildProductImageUrl, handleProductImageError } from "../lib/productUtils";
import { calculateLineTotal } from "../lib/quoteUtils";
import { SharePanel } from "../components/SharePanel";

function CreateBomPage({ workspace, clients = [], onOpenList, onOpenClients }) {
  const {
    draft,
    activeRoom,
    setActiveRoom,
    applyActiveRoomToAllItems,
    subtotal,
    discountAmount,
    taxableSubtotal,
    gstAmount,
    grandTotal,
    query,
    setQuery,
    catalogFilter,
    setCatalogFilter,
    suggestions,
    searching,
    saving,
    initializing,
    customProductOpen,
    customProduct,
    setCustomProduct,
    startNewDraft,
    updateDraftField,
    addSuggestionToDraft,
    addCustomProductToDraft,
    updateItem,
    removeItem,
    saveDraft,
    viewPdf,
    generatePdf,
    generatingPdf,
    sharePanel,
    setSharePanel,
    lastSavedAt,
  } = workspace;

  useEffect(() => {
    const onSaveShortcut = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        void saveDraft();
      }
    };
    window.addEventListener("keydown", onSaveShortcut);
    return () => window.removeEventListener("keydown", onSaveShortcut);
  }, [saveDraft]);

  const discountValueLabel =
    draft.discountType === "common-percentage"
      ? "Common %"
      : draft.discountType === "on-total"
      ? "On-total amount"
      : "Discount value";
  const showDiscountValueField = draft.discountType !== "item-wise";
  const activeRoomItemCount = draft.items.filter((item) => String(item.roomName || "") === String(activeRoom || "")).length;

  return (
    <>
    <div className="page-stack">
      <PageIntro
        eyebrow="Main workspace"
        title="Create quotation"
        description="Select a client, add products, assign rooms, apply the right discount mode, and save or export a professional quotation from one page."
        actions={
          <>
            {lastSavedAt ? <span className="autosave-indicator">Last saved at {new Date(lastSavedAt).toLocaleTimeString()}</span> : null}
            <button type="button" className="btn-secondary" onClick={onOpenList}>
              Saved quotations
            </button>
            <button type="button" className="btn-ghost" onClick={() => void startNewDraft()}>
              New quotation
            </button>
          </>
        }
      />

      <div className="editor-layout">
        <div className="editor-main">
          <PanelCard
            title="Client and proposal"
            subtitle="Fill client details manually for this quotation snapshot."
          >
            <div className="field-grid one-up">
              <DropdownSelect
                label="Saved client"
                placeholder="— Select Saved Client —"
                value={draft.clientId}
                options={clients}
                onSelect={(client) => {
                  if (client?.id) {
                    updateDraftField("clientId", client.id);
                    updateDraftField("clientName", client.client_name || "");
                    updateDraftField("company", client.company || "");
                    updateDraftField("phone", client.phone || "");
                    updateDraftField("email", client.email || "");
                    updateDraftField("address", client.address || "");
                    updateDraftField("gstRate", client.gst_rate || 18);
                  }
                }}
                getOptionLabel={getClientDisplayLabel}
                getOptionDescription={(client) => client?.company || client?.phone || ""}
                getOptionValue={(client) => String(client?.id)}
              />

              <DropdownSelect
                label="Prepared By"
                placeholder="— Select Staff —"
                value={draft.preparedBy}
                options={preparedByOptions}
                onSelect={(option) => {
                  updateDraftField("preparedBy", option?.name || "");
                  updateDraftField("preparedPhone", option?.phone || "");
                }}
                getOptionLabel={(option) => option.label}
                getOptionDescription={(option) => option.phone}
                getOptionValue={(option) => option.name}
              />

            </div>

            <div className="field-grid three-up" style={{ marginTop: "16px" }}>

              <label className="field-shell">
                <span>Proposal Number</span>
                <input
                  className="soft-input"
                  value={draft.proposalNo}
                  onChange={(event) => updateDraftField("proposalNo", event.target.value)}
                  placeholder={initializing ? "Generating..." : "Proposal number"}
                />
              </label>

              <label className="field-shell">
                <span>Date</span>
                <input
                  className="soft-input"
                  type="date"
                  value={draft.quoteDate}
                  onChange={(event) => updateDraftField("quoteDate", event.target.value)}
                />
              </label>

              <label className="field-shell">
                <span>Client Name</span>
                <input
                  className="soft-input"
                  value={draft.clientName}
                  onChange={(event) => updateDraftField("clientName", event.target.value)}
                  placeholder="Client name"
                />
              </label>

              <label className="field-shell">
                <span>Company</span>
                <input
                  className="soft-input"
                  value={draft.company}
                  onChange={(event) => updateDraftField("company", event.target.value)}
                  placeholder="Company"
                />
              </label>

              <label className="field-shell">
                <span>Phone</span>
                <input
                  className="soft-input"
                  value={draft.phone}
                  onChange={(event) => updateDraftField("phone", event.target.value)}
                  placeholder="Phone"
                />
              </label>

              <label className="field-shell">
                <span>Email</span>
                <input
                  className="soft-input"
                  value={draft.email}
                  onChange={(event) => updateDraftField("email", event.target.value)}
                  placeholder="Email"
                />
              </label>

              <label className="field-shell">
                <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  GST %
                  <label style={{ display: "flex", alignItems: "center", gap: "4px", fontWeight: 400, fontSize: "0.8rem", cursor: "pointer", marginLeft: "auto" }}>
                    <input
                      type="checkbox"
                      checked={draft.gstEnabled !== false}
                      onChange={(e) => updateDraftField("gstEnabled", e.target.checked)}
                      style={{ accentColor: "var(--color-primary, #2d6a4f)", width: "15px", height: "15px", cursor: "pointer" }}
                    />
                    Apply GST
                  </label>
                </span>
                <input
                  className="soft-input"
                  type="number"
                  min="0"
                  max="100"
                  value={draft.gstRate}
                  disabled={draft.gstEnabled === false}
                  style={{ opacity: draft.gstEnabled === false ? 0.45 : 1 }}
                  onChange={(event) =>
                    updateDraftField("gstRate", Math.min(100, Math.max(0, Number(event.target.value) || 0)))
                  }
                />
              </label>

              <label className="field-shell span-3">
                <span>Address</span>
                <textarea
                  className="soft-input soft-textarea"
                  value={draft.address}
                  onChange={(event) => updateDraftField("address", event.target.value)}
                  placeholder="Address"
                />
              </label>
            </div>
          </PanelCard>

          <PanelCard
            title="Add products"
            subtitle="Search live catalog results and click once to add them into the BOM table."
          >
            <div className="search-row">
              <div className="search-stack">
                <input
                  className="soft-input hero-input"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search by code, product name, brand, or category"
                />
                {query.trim() ? (
                  <div className="suggestion-panel">
                    <div className="suggestion-panel-head">
                      <strong>{searching ? "Searching..." : "Click to add"}</strong>
                      <span>{catalogFilter === "all" ? "All sources" : catalogFilter}</span>
                    </div>
                    {suggestions.length === 0 ? (
                      <div className="suggestion-empty">No matching products found.</div>
                    ) : (
                      suggestions.map((suggestion) => (
                        <button
                          key={`${suggestion.source || "catalog"}-${suggestion.code}-${suggestion.name}`}
                          type="button"
                          className="suggestion-row"
                          onClick={() => addSuggestionToDraft(suggestion)}
                        >
                          <img
                            src={buildProductImageUrl(suggestion)}
                            alt=""
                            className="suggestion-image"
                            onError={(event) => handleProductImageError(event, suggestion)}
                          />
                          <div className="suggestion-copy">
                            <strong>{suggestion.name}</strong>
                            <span>
                              {suggestion.code}
                              {suggestion.sourceLabel ? ` | ${suggestion.sourceLabel}` : ""}
                            </span>
                          </div>
                          <strong className="suggestion-amount">{formatCurrency(suggestion.price)}</strong>
                        </button>
                      ))
                    )}
                  </div>
                ) : null}
              </div>

              <select
                className="soft-input select-fit"
                value={catalogFilter}
                onChange={(event) => setCatalogFilter(event.target.value)}
              >
                {catalogOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {customProductOpen ? (
              <div className="custom-product-panel">
                <div className="field-grid three-up">
                  <label className="field-shell">
                    <span>Product code</span>
                    <input
                      className="soft-input"
                      value={customProduct.productCode}
                      onChange={(event) =>
                        setCustomProduct((prev) => ({ ...prev, productCode: event.target.value }))
                      }
                      placeholder="Optional custom code"
                    />
                  </label>
                  <label className="field-shell">
                    <span>Product name</span>
                    <input
                      className="soft-input"
                      value={customProduct.productName}
                      onChange={(event) =>
                        setCustomProduct((prev) => ({ ...prev, productName: event.target.value }))
                      }
                      placeholder="Custom product name"
                    />
                  </label>
                  <label className="field-shell">
                    <span>Price</span>
                    <input
                      className="soft-input"
                      type="number"
                      min="0"
                      value={customProduct.price}
                      onChange={(event) =>
                        setCustomProduct((prev) => ({ ...prev, price: event.target.value }))
                      }
                      placeholder="0"
                    />
                  </label>
                  <label className="field-shell">
                    <span>Brand</span>
                    <input
                      className="soft-input"
                      value={customProduct.brand}
                      onChange={(event) =>
                        setCustomProduct((prev) => ({ ...prev, brand: event.target.value }))
                      }
                      placeholder="Brand"
                    />
                  </label>
                  <label className="field-shell">
                    <span>Category</span>
                    <input
                      className="soft-input"
                      value={customProduct.category}
                      onChange={(event) =>
                        setCustomProduct((prev) => ({ ...prev, category: event.target.value }))
                      }
                      placeholder="Category"
                    />
                  </label>
                  <label className="field-shell span-3">
                    <span>Product image URL</span>
                    <input
                      className="soft-input"
                      value={customProduct.productImage}
                      onChange={(event) =>
                        setCustomProduct((prev) => ({ ...prev, productImage: event.target.value }))
                      }
                      placeholder="https://..."
                    />
                  </label>
                  <label className="field-shell span-3">
                    <span>Details</span>
                    <input
                      className="soft-input"
                      value={customProduct.details}
                      onChange={(event) =>
                        setCustomProduct((prev) => ({ ...prev, details: event.target.value }))
                      }
                      placeholder="Optional details"
                    />
                  </label>
                </div>
                <div className="form-actions">
                  <button type="button" className="btn-primary" onClick={addCustomProductToDraft}>
                    Add custom item
                  </button>
                </div>
              </div>
            ) : null}
          </PanelCard>

          {/* Discount configuration moved below Quotation items as requested */}

          <PanelCard
            title="Quotation items"
            subtitle="Adding the same product again updates quantity instead of creating a duplicate row."
          >
            <div className="room-bar">
              <div className="room-bar-head">
                <div>
                  <strong>Current Room</strong>
                  <span>Newly added products will inherit this room automatically.</span>
                </div>
                <button
                  type="button"
                  className="btn-secondary room-apply-button"
                  onClick={() => applyActiveRoomToAllItems()}
                  disabled={draft.items.length === 0}
                >
                  Apply Current Room To All Existing Products
                </button>
              </div>

              <div className="room-chip-row" role="tablist" aria-label="Current working room">
                {roomOptions.map((roomName) => {
                  const isActive = activeRoom === roomName;
                  return (
                    <button
                      key={roomName}
                      type="button"
                      role="tab"
                      aria-selected={isActive}
                      className={isActive ? "room-chip is-active" : "room-chip"}
                      onClick={() => setActiveRoom(roomName)}
                    >
                      {roomName}
                    </button>
                  );
                })}
              </div>

              <div className="room-bar-footer">
                <label className="field-shell room-select-shell">
                  <span>Selected room</span>
                  <select
                    className="soft-input room-select"
                    value={activeRoom}
                    onChange={(event) => setActiveRoom(event.target.value)}
                  >
                    {roomOptions.map((roomName) => (
                      <option key={roomName} value={roomName}>
                        {roomName}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="room-stat">
                  <strong>{activeRoomItemCount}</strong>
                  <span>items already use this room</span>
                </div>
              </div>
            </div>

            <div className="table-shell">
              <table className="data-table quote-table">
                <thead>
                  <tr>
                    <th>Image</th>
                    <th>Product Name</th>
                    <th>Room Name</th>
                    <th>Quantity</th>
                    <th>Price</th>
                    {draft.discountType === "item-wise" ? <th>Disc %</th> : null}
                    <th>Total</th>
                    <th>Delete</th>
                  </tr>
                </thead>
                <tbody>
                  {draft.items.length === 0 ? (
                    <tr>
                      <td colSpan={draft.discountType === "item-wise" ? 8 : 7}>
                        <EmptyState
                          title="No products added yet"
                          description="Search a catalog item or add a custom item to begin the quotation."
                        />
                      </td>
                    </tr>
                  ) : (
                    draft.items.map((item) => (
                      <tr key={item.rowId}>
                        <td className="quote-image-cell">
                          <img
                            src={buildProductImageUrl({
                              name: item.productName,
                              image: item.productImage,
                            })}
                            alt=""
                            className="quote-thumb"
                            onError={(event) =>
                              handleProductImageError(event, { name: item.productName, image: item.productImage })
                            }
                          />
                        </td>
                        <td>
                          <div className="table-product-cell">
                            <strong>{item.productName}</strong>
                            <span>
                              {item.productCode || "CUSTOM"}
                              {item.brand ? ` | ${item.brand}` : ""}
                            </span>
                          </div>
                        </td>
                        <td>
                          <select
                            className="table-input room-select room-select-inline"
                            value={item.roomName}
                            onChange={(event) => updateItem(item.rowId, "roomName", event.target.value)}
                          >
                            <option value="">Select Room</option>
                            {roomOptions.map((roomName) => (
                              <option key={roomName} value={roomName}>
                                {roomName}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <input
                            className="table-input"
                            type="number"
                            min="1"
                            value={item.qty}
                            onChange={(event) => updateItem(item.rowId, "qty", event.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            className="table-input"
                            type="number"
                            min="0"
                            value={item.price}
                            onChange={(event) => updateItem(item.rowId, "price", event.target.value)}
                          />
                        </td>
                        {draft.discountType === "item-wise" ? (
                          <td>
                            <input
                              className="table-input"
                              type="number"
                              min="0"
                              max="100"
                              value={item.discountPercent}
                              onChange={(event) => updateItem(item.rowId, "discountPercent", event.target.value)}
                            />
                          </td>
                        ) : null}
                        <td className="amount-cell">
                          {formatCurrency(
                            calculateLineTotal(item, {
                              discountType: draft.discountType,
                              discountValue: draft.discountValue,
                            })
                          )}
                        </td>
                        <td>
                          <button
                            type="button"
                            className="table-action danger"
                            onClick={() => removeItem(item.rowId)}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </PanelCard>

          <PanelCard
            title="Discount configuration"
            subtitle="Choose one mode only. Room selection is required for every item before save or PDF."
          >
            <div className="discount-config">
              <div className="discount-mode-grid">
                {discountTypeOptions.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    className={draft.discountType === option.id ? "discount-mode is-active" : "discount-mode"}
                    onClick={() => updateDraftField("discountType", option.id)}
                  >
                    <strong>{option.label}</strong>
                    <span>{option.helper}</span>
                  </button>
                ))}
              </div>

              <div className={showDiscountValueField ? "field-grid two-up" : "field-grid one-up"}>
                {showDiscountValueField ? (
                  <label className="field-shell">
                    <span>{discountValueLabel}</span>
                    <input
                      className="soft-input"
                      type="number"
                      min="0"
                      max={draft.discountType === "common-percentage" ? "100" : undefined}
                      value={draft.discountValue}
                      onChange={(event) =>
                        updateDraftField(
                          "discountValue",
                          draft.discountType === "common-percentage"
                            ? Math.min(100, Math.max(0, Number(event.target.value) || 0))
                            : Math.max(0, Number(event.target.value) || 0)
                        )
                      }
                    />
                  </label>
                ) : null}

                <label className="switch-row compact">
                  <span>PDF branding and watermark</span>
                  <input
                    type="checkbox"
                    checked={draft.watermark}
                    onChange={(event) => updateDraftField("watermark", event.target.checked)}
                  />
                </label>
              </div>
            </div>
          </PanelCard>

          <PanelCard title="Summary" subtitle="Totals and actions" className="summary-card">
            <div className="summary-list">
              <div className="summary-line">
                <span>Subtotal</span>
                <strong>{formatCurrency(subtotal)}</strong>
              </div>
              <div className="summary-line">
                <span>Discount</span>
                <strong>{formatCurrency(discountAmount)}</strong>
              </div>
              <div className="summary-line">
                <span>Net taxable</span>
                <strong>{formatCurrency(taxableSubtotal)}</strong>
              </div>
              <div className="summary-line">
                <span>GST ({draft.gstEnabled !== false ? (draft.gstRate || 0) : 0}%){draft.gstEnabled === false ? " (off)" : ""}</span>
                <strong>{formatCurrency(gstAmount)}</strong>
              </div>
              <div className="summary-line total">
                <span>Grand Total</span>
                <strong>{formatCurrency(grandTotal)}</strong>
              </div>
            </div>

            <div className="action-stack">
              <button type="button" className="btn-secondary" onClick={() => void saveDraft()} disabled={saving || generatingPdf}>
                {saving ? "Saving..." : "Save Draft"}
              </button>
              <button type="button" className="btn-ghost" onClick={() => void viewPdf()} disabled={saving || generatingPdf}>
                {generatingPdf ? "Generating..." : "View PDF"}
              </button>
              <button type="button" className="btn-primary" onClick={() => void generatePdf()} disabled={saving || generatingPdf}>
                {generatingPdf ? "Generating..." : "Generate Final PDF"}
              </button>
            </div>
          </PanelCard>
        </div>
      </div>
    </div>
    <SharePanel
      isOpen={Boolean(sharePanel?.isOpen)}
      pdfBlob={sharePanel?.pdfBlob}
      pdfUrl={sharePanel?.pdfUrl}
      proposalNo={sharePanel?.proposalNo}
      date={sharePanel?.date}
      clientName={sharePanel?.clientName}
      clientPhone={sharePanel?.clientPhone}
      clientEmail={sharePanel?.clientEmail}
      clientCompany={sharePanel?.clientCompany}
      subtotal={sharePanel?.subtotal}
      discountValue={sharePanel?.discountValue}
      gstRate={sharePanel?.gstRate}
      gstAmount={sharePanel?.gstAmount}
      grandTotal={sharePanel?.grandTotal}
      items={sharePanel?.items}
      applyGst={sharePanel?.applyGst}
      onClose={() => setSharePanel({ isOpen: false, pdfBlob: null, pdfUrl: null })}
    />
    </>
  );
}

export default CreateBomPage;
