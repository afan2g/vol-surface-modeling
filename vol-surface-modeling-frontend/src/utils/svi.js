
const rawSVI = (a, b, rho, m, sigma, strikePrice, spot, timeToExpiry) => {
  const k = Math.log(spot / strikePrice); // k: log moneyness, = ln(spot / strikePrice)
  const impVar =
    a + b * rho * (k - m) + Math.sqrt(Math.pow(k - m, 2) + Math.pow(sigma, 2)); // returns total implied variance
  const impliedVol = Math.sqrt(totalImpVar / timeToExpiry); // returns implied volatility

  return {
    impliedVar: impVar,
    impliedVol: impliedVol,
    logMoneyness: k,
    strikePrice: strikePrice,
  };
};

const naturalSVI = (
  delta,
  mu,
  rho,
  omega,
  zeta,
  strikePrice,
  spot,
  timeToExpiry
) => {
  const k = Math.log(spot / strikePrice);
  const totalVar =
    delta +
    (omega / 2) *
      (1 +
        zeta * rho * (k - mu) +
        Math.sqrt(Math.pow(zeta * (k - mu) + rho, 2) + (1 - Math.pow(rho, 2))));
  const impliedVol = Math.sqrt(totalVar / timeToExpiry);
  return {
    totalVar: totalVar,
    impliedVol: impliedVol,
    logMoneyness: k,
    strikePrice: strikePrice,
  };
};

export {rawSVI, naturalSVI};