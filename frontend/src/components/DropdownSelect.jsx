import React, { useEffect, useMemo, useRef, useState } from "react";

function getDefaultOptionLabel(option) {
  return String(option?.label || option?.name || option?.client_name || option?.value || "").trim();
}

export function DropdownSelect({
  label,
  placeholder,
  options,
  value,
  onSelect,
  getOptionLabel = getDefaultOptionLabel,
  getOptionDescription,
  getOptionValue = (option) => option?.value ?? getOptionLabel(option),
  className = "",
}) {
  const rootRef = useRef(null);
  const [isOpen, setIsOpen] = useState(false);

  const selectedOption = useMemo(
    () => (Array.isArray(options) ? options.find((option) => getOptionValue(option) === value) : null),
    [getOptionValue, options, value]
  );

  useEffect(() => {
    function handlePointerDown(event) {
      if (rootRef.current && !rootRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, []);

  return (
    <div ref={rootRef} className={`dropdown-field ${className}`.trim()}>
      {label ? <span className="dropdown-label">{label}</span> : null}
      <button
        type="button"
        className={`dropdown-trigger ${isOpen ? "is-open" : ""}`.trim()}
        onClick={() => setIsOpen((prev) => !prev)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <span className={selectedOption ? "dropdown-trigger-value" : "dropdown-trigger-placeholder"}>
          {selectedOption ? getOptionLabel(selectedOption) : placeholder}
        </span>
        <span className="dropdown-trigger-caret" aria-hidden="true">
          ▾
        </span>
      </button>

      <div className={`dropdown-panel ${isOpen ? "is-open" : ""}`.trim()} role="listbox">
        {(Array.isArray(options) ? options : []).map((option) => {
          const optionValue = getOptionValue(option);
          const isSelected = String(optionValue) === String(value);
          return (
            <button
              key={String(optionValue)}
              type="button"
              className={`dropdown-option ${isSelected ? "is-selected" : ""}`.trim()}
              onClick={() => {
                onSelect?.(option);
                setIsOpen(false);
              }}
              role="option"
              aria-selected={isSelected}
            >
              <span className="dropdown-option-label">{getOptionLabel(option)}</span>
              {getOptionDescription ? (
                <span className="dropdown-option-description">{getOptionDescription(option)}</span>
              ) : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}
