import React, { useMemo, useState } from "react";
import { EmptyState, PageIntro, PanelCard } from "../components/ui";
import { formatCurrency } from "../lib/constants";
import { buildProductImageUrl, handleProductImageError } from "../lib/productUtils";
import { useDebouncedValue } from "../hooks/useDebouncedValue";

const emptyProductForm = {
  id: "",
  product_code: "",
  product_name: "",
  brand: "Custom",
  category: "General",
  product_image: "",
  price: "",
};

function ProductsPage({ loading, products, onSaveProduct, onDeleteProduct }) {
  const [query, setQuery] = useState("");
  const [form, setForm] = useState(emptyProductForm);
  const deferredQuery = useDebouncedValue(query, 300);

  const filteredProducts = useMemo(() => {
    const normalizedQuery = deferredQuery.trim().toLowerCase();
    if (!normalizedQuery) {
      return products || [];
    }

    return (products || []).filter((product) =>
      [product.product_code, product.product_name, product.brand, product.category]
        .join(" ")
        .toLowerCase()
        .includes(normalizedQuery)
    );
  }, [deferredQuery, products]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.product_code.trim() || !form.product_name.trim()) {
      return;
    }

    const saved = await onSaveProduct({
      ...form,
      price: Number(form.price) || 0,
    });
    if (saved) {
      setForm(emptyProductForm);
    }
  };

  return (
    <div className="page-stack">
      <PageIntro
        eyebrow="Managed product codes"
        title="Products"
        description="Maintain internal product codes that should appear in live search alongside the connected Aquant and Kohler catalogs."
      />

      <div className="management-grid">
        <PanelCard title="Saved products" subtitle="These products are stored in the BOM database and can be searched inside quotations.">
          <div className="toolbar-row">
            <input
              type="search"
              className="soft-input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search managed products..."
            />
          </div>

          {loading ? (
            <div className="loading-panel">Loading products...</div>
          ) : filteredProducts.length === 0 ? (
            <EmptyState
              title="No managed products found"
              description="Add an internal product here or use the connected catalogs directly from the quotation page."
            />
          ) : (
            <div className="product-card-list">
              {filteredProducts.map((product) => (
                <article key={product.id} className="product-card" onClick={() => setForm(product)} role="button" tabIndex={0}>
                  <img
                    src={buildProductImageUrl({ name: product.product_name, image: product.product_image })}
                    alt=""
                    className="mini-thumb"
                    onError={(event) =>
                      handleProductImageError(event, {
                        name: product.product_name,
                        image: product.product_image,
                      })
                    }
                  />
                  <div className="product-copy">
                    <span className="code-cell">{product.product_code}</span>
                    <strong>{product.product_name}</strong>
                    <span>{product.brand} • {product.category}</span>
                  </div>
                  <strong className="amount-cell">{formatCurrency(product.price)}</strong>
                  <button type="button" className="table-action danger" onClick={(event) => {
                    event.stopPropagation();
                    onDeleteProduct(product.id);
                  }}>
                    Delete
                  </button>
                </article>
              ))}
            </div>
          )}
        </PanelCard>

        <PanelCard title={form.id ? "Edit product" : "Add product"} subtitle="`product_code` stays unique to protect BOM data integrity.">
          <form className="form-stack" onSubmit={handleSubmit}>
            <input
              className="soft-input"
              value={form.product_code}
              onChange={(event) => setForm((prev) => ({ ...prev, product_code: event.target.value }))}
              placeholder="Product code"
            />
            <input
              className="soft-input"
              value={form.product_name}
              onChange={(event) => setForm((prev) => ({ ...prev, product_name: event.target.value }))}
              placeholder="Product name"
            />
            <input
              className="soft-input"
              value={form.brand}
              onChange={(event) => setForm((prev) => ({ ...prev, brand: event.target.value }))}
              placeholder="Brand"
            />
            <input
              className="soft-input"
              value={form.category}
              onChange={(event) => setForm((prev) => ({ ...prev, category: event.target.value }))}
              placeholder="Category"
            />
            <input
              className="soft-input"
              value={form.product_image}
              onChange={(event) => setForm((prev) => ({ ...prev, product_image: event.target.value }))}
              placeholder="Product image URL"
            />
            <input
              className="soft-input"
              type="number"
              min="0"
              value={form.price}
              onChange={(event) => setForm((prev) => ({ ...prev, price: event.target.value }))}
              placeholder="Price"
            />
            <div className="form-actions">
              {form.id ? (
                <button type="button" className="btn-secondary" onClick={() => setForm(emptyProductForm)}>
                  Cancel
                </button>
              ) : null}
              <button type="submit" className="btn-primary">
                {form.id ? "Update product" : "Add product"}
              </button>
            </div>
          </form>
        </PanelCard>
      </div>
    </div>
  );
}

export default ProductsPage;
