import React, { useState } from "react";

function Dropdown({
  options,
  onSelect,
  placeholder,
  text = null,
  disabled,
  defaultValue = null,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedValue, setSelectedValue] = useState(defaultValue);

  const handleOptionClick = (option) => {
    if (Array.isArray(option)) {
      const date = new Date(option[0]);
      const formattedDate = date.toLocaleDateString();
      setSelectedValue(formattedDate);
    } else {
      setSelectedValue(option);
    }
    onSelect(option);
    setIsOpen(false);
  };

  return (
    <div className="dropdown" style={{ width: "100%" }}>
      <button
        className="dropdown-trigger"
        onClick={() => setIsOpen(!isOpen)}
        disabled={options.length === 0 || disabled}
        style={{
          width: "100%",
        }}
      >
        {selectedValue
          ? `${selectedValue}${text !== null ? text : ""}`
          : placeholder || "Select an option"}
      </button>
      {isOpen && (
        <ul
          className="dropdown-menu"
          style={{
            listStyleType: "none",
            textAlign: "center",
            padding: "0",
            margin: "0",
          }}
        >
          {options.map((option) => {
            const displayOption = Array.isArray(option)
              ? new Date(option[0]).toLocaleDateString()
              : option;
            return (
              <li
                key={displayOption}
                onClick={() => handleOptionClick(option)}
                style={{
                  cursor: "pointer",
                  padding: "8px",
                }}
              >
                {displayOption}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default Dropdown;
