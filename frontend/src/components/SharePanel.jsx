import React, { useState, useMemo, useEffect, useRef } from "react";

function formatInr(value) {
  return `₹${Number(value || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}



export function SharePanel({
  isOpen,
  onClose,
  pdfBlob,
  pdfUrl,
  proposalNo,
  date,
  clientName,
  clientPhone,
  clientEmail,
  clientCompany,
  subtotal,
  discountValue,
  gstRate: initialGstRate,
  gstAmount: initialGstAmount,
  grandTotal: initialGrandTotal,
  items,
  applyGst,
}) {
  const [extraDiscount, setExtraDiscount] = useState(0);
  const [gstRate, setGstRate] = useState(Number(initialGstRate || 18));
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const shareLockRef = useRef(false);
  // modal/step states removed — single-button WhatsApp flow only
  const safeProposalNo = String(proposalNo || "quotation").trim() || "quotation";

  useEffect(() => {
    setGstRate(Number(initialGstRate || 18));
    setExtraDiscount(0);
  }, [isOpen, initialGstRate]);

  // Calculate totals dynamically
  const netAfterDiscount = Math.max(0, subtotal * (1 - Number(extraDiscount || 0) / 100));
  const calculatedGstAmount = applyGst ? netAfterDiscount * (Number(gstRate || 0) / 100) : 0;
  const calculatedGrandTotal = netAfterDiscount + calculatedGstAmount;

  const pdfUrl_safe = useMemo(() => (pdfBlob ? window.URL.createObjectURL(pdfBlob) : ""), [pdfBlob]);
  const resolvedPdfUrl = pdfUrl_safe || pdfUrl || "";

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (pdfUrl_safe) {
        window.URL.revokeObjectURL(pdfUrl_safe);
      }
    };
  }, [pdfUrl_safe]);

  if (!isOpen) return null;

  // ============================================
  // MESSAGE BUILDERS
  // ============================================

  

  // ============================================
  // BUTTON HANDLERS
  // ============================================

  const handleViewPdf = () => {
    if (resolvedPdfUrl) {
      window.open(resolvedPdfUrl, "_blank");
    }
  };

  const handleDownloadPdf = () => {
    if (resolvedPdfUrl) {
      const a = document.createElement("a");
      a.href = resolvedPdfUrl;
      a.download = `${safeProposalNo}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    }
  };

  const handleWhatsAppShare = async () => {
    try {
      if (shareLockRef.current) {
        return;
      }
      shareLockRef.current = true;
      setLoading(true);
      setStatusMsg("Preparing...");

      const pdfBlobLocal = pdfBlob;
      if (!pdfBlobLocal) {
        setStatusMsg("❌ PDF not available. Generate preview first.");
        return;
      }
      const fileName = `Proposal-${safeProposalNo}.pdf`;
      const pdfFile = new File([pdfBlobLocal], fileName, { type: "application/pdf" });

      // STEP 2: Build complete message
      const roomGroups = {};
      (Array.isArray(items) ? items : []).forEach((item) => {
        const room = item.room_name || item.roomName || item.room || "Unassigned";
        if (!roomGroups[room]) roomGroups[room] = [];
        roomGroups[room].push(item);
      });

      const itemsList = Object.entries(roomGroups)
        .map(([room, roomItems]) => {
          const itemsText = (roomItems || [])
            .map((it) => `  • ${it.product_name || it.productName || it.name || "Item"} (×${it.qty || 0}) — ₹${Number(it.price || it.rate || it.amount || 0).toLocaleString('en-IN')}`)
            .join('\n');
          return `${room}:\n${itemsText}`;
        })
        .join('\n\n');

      const phoneRaw = String(clientPhone || "").replace(/\D/g, "");
      const phoneWithCode = phoneRaw.startsWith("91") ? phoneRaw : `91${phoneRaw}`;

      const message = `Dear ${clientName || ""},\n\nPlease find attached your Business Proposal from Shreeji Ceramica.\n\nProposal No : ${safeProposalNo}\nDate        : ${date}\nCompany     : ${clientCompany || ""}\nAddress     : ${/* address not available */ ""}\nMobile      : ${clientPhone || ""}\n\nITEMS:\n${itemsList}\n\n─────────────────────────\nSubtotal    : ₹${Number(subtotal || 0).toLocaleString('en-IN')}\nDiscount    : -₹${Number(discountValue || 0).toLocaleString('en-IN')}\nGST (18%)   : ₹${Number(initialGstAmount || 0).toLocaleString('en-IN')}\nGrand Total : ₹${Number(initialGrandTotal || calculatedGrandTotal || 0).toLocaleString('en-IN')}\n─────────────────────────\n\nTerms:\n1. Valid for 15 days\n2. 100% advance payment required\n3. Delivery within 7–10 days of payment\n\nRegards,\nShreeji Ceramica\n+91 9033745455`;

      // STEP 3: navigator.share() with PDF file (ONLY share method)
      if (navigator.canShare && navigator.canShare({ files: [pdfFile] })) {
        setStatusMsg('Opening WhatsApp...');
        await navigator.share({ files: [pdfFile], title: fileName, text: message });
        setStatusMsg('✅ Shared successfully!');
      } else {
        // Fallback: download PDF + open WhatsApp Web
        const blobUrl = URL.createObjectURL(pdfBlobLocal);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);

        const encodedMsg = encodeURIComponent(message);
        window.open(`https://web.whatsapp.com/send?phone=${phoneWithCode}&text=${encodedMsg}`, '_blank');

        setStatusMsg('✅ PDF downloaded! Attach it in WhatsApp and click Send.');
      }
    } catch (err) {
      if (err?.name === 'AbortError') {
        // user cancelled native share
        setStatusMsg('');
      } else {
        console.error(err);
        setStatusMsg('❌ Share failed. Please try again.');
      }
    } finally {
      shareLockRef.current = false;
      setLoading(false);
    }
  };

  

  const handleGmailShare = async () => {
    try {
      setLoading(true);
      setStatusMsg("Downloading PDF...");

      // Use existing pdfBlob (already generated with all data validated)
      if (!pdfBlob) {
        setStatusMsg("❌ PDF not available. Generate it first.");
        setLoading(false);
        return;
      }

      // Auto-download PDF silently using existing blob
      const fileName = `Proposal-${safeProposalNo}.pdf`;
      const url = URL.createObjectURL(pdfBlob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setStatusMsg("✅ PDF downloaded! Opening Gmail...");

      // Open Gmail compose
      const to = clientEmail || "";
      const emailSubject = `Business Proposal ${safeProposalNo} – Shreeji Ceramica`;
      const emailBody = (
        `Dear ${clientName || "Sir/Ma'am"},\n\n` +
        `Please find attached your Business Proposal from Shreeji Ceramica.\n\n` +
        `Proposal No: ${safeProposalNo}\n` +
        `Date: ${date}\n` +
        `Company: ${clientCompany || "N/A"}\n\n` +
        `ITEMS:\n` +
        (() => {
          const roomGroups = {};
          (Array.isArray(items) ? items : []).forEach((item) => {
            const room = item.room_name || item.roomName || "Unassigned";
            if (!roomGroups[room]) roomGroups[room] = [];
            roomGroups[room].push(item);
          });
          return Object.entries(roomGroups)
            .map(([room, roomItems]) => {
              const roomItemsText = roomItems
                .map((i) => `• ${i.product_name || i.productName} (×${i.qty || 0}) = ${formatInr(Number(i.qty || 0) * Number(i.price || 0))}`)
                .join("\n");
              return `${room}:\n${roomItemsText}`;
            })
            .join("\n\n");
        })() +
        `\n\n─────────────────────────\n` +
        `Subtotal: ${formatInr(subtotal)}\n` +
        `Discount (${extraDiscount}%): -${formatInr(subtotal * (extraDiscount / 100))}\n` +
        `GST (${gstRate}%): ${formatInr(calculatedGstAmount)}\n` +
        `Grand Total: ${formatInr(calculatedGrandTotal)}\n` +
        `─────────────────────────\n\n` +
        `Terms:\n` +
        `1. Valid for 15 days\n` +
        `2. 100% advance payment required\n` +
        `3. Delivery within 7–10 days of payment\n\n` +
        `Regards,\n` +
        `Shreeji Ceramica | +91 9033745455\n` +
        `shreejiceramica303@gmail.com`
      );

      const gmailUrl =
        `https://mail.google.com/mail/?view=cm` +
        `&to=${to}` +
        `&su=${encodeURIComponent(emailSubject)}` +
        `&body=${encodeURIComponent(emailBody)}`;

      window.open(gmailUrl, "_blank");

      
    } catch (error) {
      console.error("Gmail share error:", error);
      setStatusMsg("❌ Failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleShareMore = async () => {
    const text =
      `Business Proposal ${safeProposalNo} from Shreeji Ceramica\n\n` +
      `Client: ${clientName}\n` +
      `Grand Total: ${formatInr(calculatedGrandTotal)}\n` +
      `Date: ${date}`;

    if (navigator.share) {
      try {
        await navigator.share({
          title: `Business Proposal ${safeProposalNo}`,
          text: text,
        });
      } catch (error) {
        console.log("Share cancelled or failed:", error);
      }
    } else if (navigator.clipboard) {
      try {
        await navigator.clipboard.writeText(text);
        alert("Quotation details copied to clipboard!");
      } catch (error) {
        console.error("Failed to copy:", error);
      }
    }
  };

  // ============================================
  // RENDER
  // ============================================

  return (
    <div className="share-panel-overlay" onClick={onClose}>
      <div className="share-panel" onClick={(e) => e.stopPropagation()}>
        {/* Close Button */}
        <button type="button" className="share-panel-close" onClick={onClose}>
          ×
        </button>

        {/* Financial Summary Section */}
        <div className="share-panel-summary">
          <div className="share-panel-row">
            <span>Subtotal</span>
            <strong>{formatInr(subtotal)}</strong>
          </div>

          <div className="share-panel-row">
            <span>Extra Discount (%)</span>
            <input
              type="number"
              className="share-panel-input"
              min="0"
              max="100"
              value={extraDiscount}
              onChange={(e) => setExtraDiscount(Math.max(0, Math.min(100, Number(e.target.value) || 0)))}
            />
          </div>

          <div className="share-panel-row">
            <span>GST Rate (%)</span>
            <select className="share-panel-input" value={gstRate} onChange={(e) => setGstRate(Number(e.target.value) || 0)}>
              <option value={5}>5%</option>
              <option value={12}>12%</option>
              <option value={18}>18%</option>
              <option value={28}>28%</option>
            </select>
          </div>

          <div className="share-panel-row">
            <span>GST Amount</span>
            <strong className="share-panel-muted">{formatInr(calculatedGstAmount)}</strong>
          </div>

          <hr className="share-panel-divider" />

          <div className="share-panel-row-total">
            <span>Grand Total</span>
            <strong>{formatInr(calculatedGrandTotal)}</strong>
          </div>

          <p className="share-panel-metadata">
            {safeProposalNo} • {date}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="share-panel-buttons">
          {/* Row 1: View & Download */}
          <div className="share-panel-button-row">
            <button
              type="button"
              className="share-panel-button share-panel-button-secondary"
              onClick={handleViewPdf}
              title="View PDF in new tab"
            >
              <span className="share-panel-button-icon">👁</span>
              <span className="share-panel-button-label">View PDF</span>
            </button>
            <button
              type="button"
              className="share-panel-button share-panel-button-primary"
              onClick={handleDownloadPdf}
              title="Download PDF file"
            >
              <span className="share-panel-button-icon">⬇</span>
              <span className="share-panel-button-label">Download PDF</span>
            </button>
          </div>

          {/* Row 2: WhatsApp & Email */}
          <div className="share-panel-button-row">
            <button
              className="share-btn whatsapp-btn"
              onClick={handleWhatsAppShare}
              disabled={loading}
              type="button"
            >
              {loading ? (
                <>
                  <span className="spinner" />
                  {statusMsg || 'Preparing...'}
                </>
              ) : (
                <>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
                    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15
                    -.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475
                    -.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52
                    .149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207
                    -.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372
                    -.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 
                    5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 
                    1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m
                    -5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648
                    -.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 
                    5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 
                    9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 
                    2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005
                    c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
                  </svg>
                  Share on WhatsApp
                </>
              )}
            </button>
            <button
              type="button"
              className="share-panel-button share-panel-button-email"
              onClick={handleGmailShare}
              disabled={loading}
              title="Download PDF and open Gmail compose"
            >
              <span className="share-panel-button-icon">✉</span>
              <span className="share-panel-button-label">Gmail</span>
              <span className="share-panel-button-sublabel">Attach PDF</span>
            </button>
          </div>

          <div className="share-panel-button-row">
            <button
              type="button"
              className="share-panel-button share-panel-button-secondary"
              onClick={handleShareMore}
              title="Share using native share or copy to clipboard"
            >
              <span className="share-panel-button-icon">🔗</span>
              <span className="share-panel-button-label">Share More</span>
            </button>
            <button
              type="button"
              className="share-panel-button share-panel-button-edit"
              onClick={onClose}
              title="Close panel and keep editing"
            >
              <span className="share-panel-button-icon">✏</span>
              <span className="share-panel-button-label">Edit Again</span>
            </button>
          </div>
        </div>

        

        {/* Status Toast */}
        {statusMsg && (
          <div
            className={`share-toast ${
              statusMsg.includes("✅")
                ? "success"
                : statusMsg.includes("❌")
                ? "error"
                : "info"
            }`}
          >
            {loading && <span className="share-toast-spinner" />}
            <p>{statusMsg}</p>
          </div>
        )}
      </div>
    </div>
  );
}

