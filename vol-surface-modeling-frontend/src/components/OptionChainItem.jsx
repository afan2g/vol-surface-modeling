import React from "react";
import {} from "react-number-format";
function OptionChainItem({ optionInfo }) {
  const { symbol, markIV, markPrice, strikePrice, bsmPrice, logMoneyness } =
    optionInfo;

  const dollarFormatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  });
  let backgroundColor = "#fff";
  if (symbol.slice(-1) === "P") {
    if (parseFloat(logMoneyness) < 0) {
      backgroundColor = "#90EE90"; // Light green for ITM puts
    }
    if (parseFloat(logMoneyness) > 0) {
      backgroundColor = "#FFCCCB"; // Light red for OTM puts
    }
  }
  if (symbol.slice(-1) === "C") {
    if (parseFloat(logMoneyness) < 0) {
      backgroundColor = "#FFCCCB"; // Light red for OTM calls
    }
    if (parseFloat(logMoneyness) > 0) {
      backgroundColor = "#90EE90"; // Light green for ITM calls
    }
  }
  return (
    <div style={{ width: "100%", backgroundColor }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          paddingTop: "10px",
          paddingBottom: "10px",
          borderBottom: "1px solid #ccc",
        }}
      >
        <div style={{ width: "100%" }}>{symbol}</div>
        <div style={{ width: "100%" }}>
          {dollarFormatter.format(strikePrice)}
        </div>
        <div style={{ width: "100%" }}>{dollarFormatter.format(markPrice)}</div>
        <div style={{ width: "100%" }}>{dollarFormatter.format(bsmPrice)}</div>
        <div style={{ width: "100%" }}>
          {(parseFloat(markIV) * 100).toFixed(2)}%
        </div>
        <div style={{ width: "100%" }}>
          {parseFloat(logMoneyness).toFixed(2)}
        </div>
      </div>
    </div>
  );
}

export default OptionChainItem;
