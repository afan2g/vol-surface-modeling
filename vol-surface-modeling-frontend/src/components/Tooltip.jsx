export const Tooltip = ({ interactionData, width, height }) => {
  if (!interactionData) {
    return null;
  }

  return (
    // Wrapper div: a rect on top of the viz area
    <div
      style={{
        width: 1024,
        height: 768,
        position: "absolute",
        top: 0,
        left: 0,
        pointerEvents: "none",
      }}
    >
      {/* The actual box with dark background */}
      <div
        style={{
          position: "absolute",
          left: interactionData.xPos,
          top: interactionData.yPos,
        }}
      >
        <TooltipRow label={"Option"} value={interactionData.symbol} />
        <TooltipRow
          label={"Strike"}
          value={`$${parseFloat(interactionData.strikePrice).toFixed(2)}`}
        />
        <TooltipRow
          label={"Premium"}
          value={`$${parseFloat(interactionData.markPrice).toFixed(2)}`}
        />
        <TooltipRow
          label={"Implied Vol"}
          value={(parseFloat(interactionData.markIV) * 100).toFixed(2) + "%"}
        />
        <TooltipRow
          label={"Moneyness"}
          value={parseFloat(interactionData.moneyness).toFixed(3)}
        />
        <TooltipRow
          label={"Log Moneyness"}
          value={parseFloat(interactionData.logMoneyness).toFixed(3)}
        />
      </div>
    </div>
  );
};

const TooltipRow = ({ label, value }) => (
  <div>
    <b>{label}</b>
    <span>: </span>
    <span>{value}</span>
  </div>
);
