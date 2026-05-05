import React, { useEffect } from 'react';
import './PdfModal.css';

export function PdfModal({ isOpen, loading, url, error, filename, isDraft, retryFn, onClose }) {
  useEffect(() => {
    if (!isOpen) return;

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleDownload = () => {
    if (!url) return;
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename || "quotation.pdf";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="pdf-modal-overlay" onClick={handleOverlayClick}>
      <div className="pdf-modal-container">
        <div className="pdf-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h2>Quotation Preview</h2>
            {isDraft !== undefined && (
              <span className={`status-badge tone-${isDraft ? 'warning' : 'success'}`} style={{ fontSize: '0.75rem' }}>
                {isDraft ? 'Preview Mode (Unsaved)' : 'Saved Quotation'}
              </span>
            )}
          </div>
          <div className="pdf-modal-actions" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {!loading && !error && url && (
              <button type="button" className="btn-primary" onClick={handleDownload}>
                Download PDF
              </button>
            )}
            <button type="button" className="btn-ghost pdf-modal-close" onClick={onClose}>&times;</button>
          </div>
        </div>
        <div className="pdf-modal-body">
          {loading && (
            <div className="pdf-modal-loading">
              <div className="spinner"></div>
              <p>Generating PDF Preview...</p>
            </div>
          )}
          {error && (
            <div className="pdf-modal-error" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
              <p>{error}</p>
              {retryFn && (
                <button type="button" className="btn-primary" onClick={retryFn}>
                  Retry Generation
                </button>
              )}
            </div>
          )}
          {!loading && !error && url && (
            <iframe src={`${url}#toolbar=0`} className="pdf-iframe" title="PDF Preview" />
          )}
        </div>
      </div>
    </div>
  );
}
