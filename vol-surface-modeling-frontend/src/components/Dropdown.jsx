import React, { useState } from "react";

function Dropdown({ options, onSelect, placeholder, text = null }) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedValue, setSelectedValue] = useState(null);

  const handleOptionClick = (option) => {
    setSelectedValue(option);
    onSelect(option);
    setIsOpen(false);
  };

  return (
    <div className="dropdown" style={{ width: "100%" }}>
      <button
        className="dropdown-trigger"
        onClick={() => setIsOpen(!isOpen)}
        disabled={options.length === 0}
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
          {options.map((option) => (
            <li
              key={option}
              onClick={() => handleOptionClick(option)}
              style={{
                cursor: "pointer",
                padding: "8px",
              }}
            >
              {option}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default Dropdown;
