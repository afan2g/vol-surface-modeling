export const Tooltip = ({ interactionData, width, height }) => {
  if (!interactionData) {
    return null;
  }
    const dollarFormatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  });

  return (
    // Wrapper div: a rect on top of the viz area
    <div
      style={{
        width: 1600,
        height: 900,
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
        {interactionData.symbol && <TooltipRow label={"Option"} value={interactionData.symbol} />}
        {interactionData.strikePrice && <TooltipRow
          label={"Strike"}
          value={dollarFormatter.format(parseFloat(interactionData.strikePrice))}
        />}
       {interactionData.markPrice && <TooltipRow
          label={"Premium"}
          value={dollarFormatter.format(parseFloat(interactionData.markPrice))}
        />}
        {interactionData.markIV && <TooltipRow
          label={"Implied Vol"}
          value={(parseFloat(interactionData.markIV) * 100).toFixed(2) + "%"}
        />}
        {interactionData.impliedVolatility && <TooltipRow
          label={"Implied Vol"}
          value={(parseFloat(interactionData.impliedVolatility) * 100).toFixed(2) + "%"}
        />}
        {interactionData.moneyness && <TooltipRow
          label={"Moneyness"}
          value={parseFloat(interactionData.moneyness).toFixed(3)}
        />}
       {interactionData.logMoneyness && <TooltipRow
          label={"Log Moneyness"}
          value={parseFloat(interactionData.logMoneyness).toFixed(3)}
        />}
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
