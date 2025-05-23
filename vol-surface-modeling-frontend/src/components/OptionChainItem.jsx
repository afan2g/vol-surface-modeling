import React from "react";

function OptionChainItem({ optionInfo }) {
  const { symbol, markIV, markPrice, strikePrice, bsmPrice, logMoneyness } =
    optionInfo;

  return (
    <div style={{ width: "100%" }}>
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
          ${parseFloat(strikePrice).toFixed(2)}
        </div>
        <div style={{ width: "100%" }}>${parseFloat(markPrice).toFixed(2)}</div>
        <div style={{ width: "100%" }}>${parseFloat(bsmPrice).toFixed(2)}</div>
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
