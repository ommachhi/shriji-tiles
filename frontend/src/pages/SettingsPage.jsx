import React from "react";
import { PageIntro, PanelCard } from "../components/ui";
import { preparedByOptions } from "../lib/constants";

function SettingsPage({ settings, onUpdateSettings }) {
  return (
    <div className="page-stack">
      <PageIntro
        eyebrow="Workspace"
        title="Settings"
        description="Set up company defaults, PDF branding preferences, and workflow behavior for the sales team."
      />

      <div className="management-grid">
        <PanelCard title="Company defaults" subtitle="These values prefill new quotations.">
          <div className="form-stack">
            <input
              className="soft-input"
              value={settings.companyName}
              onChange={(event) => onUpdateSettings("companyName", event.target.value)}
              placeholder="Company name"
            />
            <select
              className="soft-input"
              value={settings.defaultPreparedBy}
              onChange={(event) => onUpdateSettings("defaultPreparedBy", event.target.value)}
            >
              {preparedByOptions.map((option) => (
                <option key={option.value} value={option.name}>
                  {option.label}
                </option>
              ))}
            </select>
            <input
              className="soft-input"
              type="number"
              min="0"
              max="28"
              value={settings.defaultGstRate}
              onChange={(event) =>
                onUpdateSettings("defaultGstRate", Math.max(0, Number(event.target.value) || 0))
              }
              placeholder="GST %"
            />
            <input
              className="soft-input"
              type="email"
              value={settings.supportEmail}
              onChange={(event) => onUpdateSettings("supportEmail", event.target.value)}
              placeholder="Support email"
            />
          </div>
        </PanelCard>

        <PanelCard title="Workflow preferences" subtitle="Small touches that shape the daily sales workflow.">
          <div className="toggle-stack">
            <label className="switch-row">
              <span>Enable PDF watermark branding by default</span>
              <input
                type="checkbox"
                checked={settings.defaultWatermark}
                onChange={(event) => onUpdateSettings("defaultWatermark", event.target.checked)}
              />
            </label>
            <label className="switch-row">
              <span>Keep summary card sticky on large screens</span>
              <input
                type="checkbox"
                checked={settings.summarySticky}
                onChange={(event) => onUpdateSettings("summarySticky", event.target.checked)}
              />
            </label>
            <label className="switch-row">
              <span>Open PDF preview automatically after save</span>
              <input
                type="checkbox"
                checked={settings.autoPreviewAfterSave}
                onChange={(event) => onUpdateSettings("autoPreviewAfterSave", event.target.checked)}
              />
            </label>
          </div>
        </PanelCard>
      </div>
    </div>
  );
}

export default SettingsPage;
