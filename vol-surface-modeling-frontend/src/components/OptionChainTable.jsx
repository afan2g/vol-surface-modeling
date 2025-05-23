import React from "react";
import OptionChainItem from "./OptionChainItem";
function OptionChainTable({ optionChain }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          paddingTop: "10px",
          paddingBottom: "10px",
          borderBottom: "1px solid #ccc",
          width: "100%",
        }}
      >
        <div style={{ width: "100%" }}>Symbol</div>
        <div style={{ width: "100%" }}>Strike Price</div>
        <div style={{ width: "100%" }}>Market Price</div>
        <div style={{ width: "100%" }}>BSM Price</div>
        <div style={{ width: "100%" }}>Implied Volatility</div>
        <div style={{ width: "100%" }}>Moneyness {"(lnS/K)"}</div>
      </div>
      {optionChain.map((optionInfo, index) => (
        <OptionChainItem key={index} optionInfo={optionInfo} />
      ))}
    </div>
  );
}

export default OptionChainTable;
