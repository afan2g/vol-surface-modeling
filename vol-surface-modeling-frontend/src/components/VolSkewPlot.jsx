import { svg } from "d3";
import React, { useEffect, useMemo } from "react";
import * as d3 from "d3";
/* 
available data: 
[{
    "bsmPrice": "11029.64084691885278977162643",
    "daysToExpiry": 0.33124053268715187,
    "logMoneyness": "0.10870052536022661741",
    "markIV": "1.0994",
    "markPrice": "11054.1",
    "moneyness": "1.1148284375",
    "riskFreeRate": "0.065",
    "spotPrice": "107023.53000000",
    "strikePrice": "96000.00000000",
    "symbol": "BTC-250524-96000-C",
    "timeToExpiry": 0.0009068871531475752
}, ...]
 where each object holds data for a single option at a specific strike price. The objects are sorted by strike price in ascending order.
*/
/* 
plot these data points, where x-axis is the moneyness, log moneyness, or strike price, and y-axis is the implied volatility.
*/

function VolSkewPlot({
  data,
  xAxis = "logMoneyness",
  dimensions = {
    width: 1024,
    height: 768,
    marginTop: 20,
    marginRight: 20,
    marginBottom: 20,
    marginLeft: 20,
  },
  onPointHover = () => {},
  sviPoints = [],
}) {
  const { width, height, marginTop, marginRight, marginBottom, marginLeft } =
    dimensions;
  const [hoveredPoint, setHoveredPoint] = React.useState(null);
  // Extract calls and puts from the data object
  const calls = data.C || [];
  const puts = data.P || [];

  // Combine all data for scale calculation
  const allData = [...calls, ...puts];

  // Create scales
  const x = d3
    .scaleLinear()
    .domain(d3.extent(allData, (option) => parseFloat(option[xAxis])))
    .nice()
    .range([marginLeft, width - marginRight]);

  const y = d3
    .scaleLinear()
    .domain(d3.extent(allData, (option) => parseFloat(option.markIV)))
    .nice()
    .range([height - marginBottom, marginTop]);

  const sviPath = useMemo(() => {
    if (!sviPoints || sviPoints.length === 0) return null;
    const lineGenerator = d3
      .line()
      .x((d) => x(parseFloat(d[xAxis])))
      .y((d) => y(parseFloat(d.impliedVolatility || d.y))) // Handle naming differences
      .curve(d3.curveMonotoneX);
    return lineGenerator(sviPoints);
  }, [xAxis, sviPoints, x, y]);

    const handleMouseMove = (event) => {
    const mouseX = event.nativeEvent.offsetX;
    const xValue = x.invert(mouseX);
    let closestPoint = sviPoints.reduce((prev, curr) => {
      return Math.abs(parseFloat(curr[xAxis]) - xValue) < Math.abs(parseFloat(prev[xAxis]) - xValue) ? curr : prev;
    });
    onPointHover({
      ...closestPoint,
      xPos: x(parseFloat(closestPoint[xAxis])),
      yPos: y(parseFloat(closestPoint.impliedVolatility || closestPoint.y)),
    });
  };

  const handlePointHover = (point) => {
    setHoveredPoint(point);
    onPointHover(point);
  };

  const handleMouseLeave = () => {
    setHoveredPoint(null);
    onPointHover(null);
  }
  return (
    <div>
      <svg
        width={width}
        height={height}
        style={{ border: "1px solid black", margin: "20px" }}
      >
        {/* Calls - rendered in blue */}
        {calls.map((option, index) => (
          <circle
            key={`call-${index}`}
            cx={x(parseFloat(option[xAxis]))}
            cy={y(parseFloat(option.markIV))}
            r={5}
            fill="#2563eb"
            stroke="#1d4ed8"
            strokeWidth={1}
            opacity={0.8}
            onMouseOver={() => {
              handlePointHover({
                ...option,
                xPos: x(parseFloat(option[xAxis])),
                yPos: y(parseFloat(option.markIV)),
              });
            }}
            onMouseOut={handleMouseLeave}
          />
        ))}

        {/* Puts - rendered in red */}
        {puts.map((option, index) => (
          <circle
            key={`put-${index}`}
            cx={x(parseFloat(option[xAxis]))}
            cy={y(parseFloat(option.markIV))}
            r={5}
            fill="#dc2626"
            stroke="#b91c1c"
            strokeWidth={1}
            opacity={0.8}
            onMouseOver={() => {
              handlePointHover({
                ...option,
                xPos: x(parseFloat(option[xAxis])),
                yPos: y(parseFloat(option.markIV)),
              });
            }}
            onMouseOut={handleMouseLeave}
          />
        ))}
        {/* SVI points - rendered in green */}
        {sviPath && (
          <>
          <path d={sviPath} stroke="#22c55e" strokeWidth={2} fill="none" />
          <path d={sviPath} stroke="transparent" strokeWidth={10} fill="none" onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}/>
          </>
        )}

        {/* X-axis */}
        <g transform={`translate(0, ${height - marginBottom})`}>
          {x.ticks().map((tick) => (
            <g key={tick} transform={`translate(${x(tick)}, 0)`}>
              <line y2={6} stroke="black" />
              <text y={20} textAnchor="middle" fontSize="12">
                {tick.toFixed(2)}
              </text>
            </g>
          ))}
        </g>

        {/* Y-axis */}
        <g transform={`translate(${marginLeft}, 0)`}>
          {y.ticks().map((tick) => (
            <g key={tick} transform={`translate(0, ${y(tick)})`}>
              <line x2={-6} stroke="black" />
              <text x={-10} dy="0.32em" textAnchor="end" fontSize="12">
                {tick.toFixed(2)}
              </text>
            </g>
          ))}
        </g>

        {/* Axis labels */}
        <text
          x={width / 2}
          y={height - 5}
          textAnchor="middle"
          fontSize="14"
          fontWeight="bold"
        >
          {xAxis.charAt(0).toUpperCase() + xAxis.slice(1)}
        </text>

        <text
          x={15}
          y={height / 2}
          textAnchor="middle"
          fontSize="14"
          fontWeight="bold"
          transform={`rotate(-90, 15, ${height / 2})`}
        >
          Implied Volatility
        </text>
      </svg>

      {/* Legend */}
      <div style={{ marginLeft: "20px", marginTop: "10px" }}>
        {calls.length > 0 && (
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              marginRight: "20px",
            }}
          >
            <div
              style={{
                width: "12px",
                height: "12px",
                borderRadius: "50%",
                backgroundColor: "#2563eb",
                border: "1px solid #1d4ed8",
                marginRight: "5px",
              }}
            />
            <span style={{ fontSize: "14px" }}>Calls ({calls.length})</span>
          </div>
        )}
        {puts.length > 0 && (
          <div style={{ display: "inline-flex", alignItems: "center" }}>
            <div
              style={{
                width: "12px",
                height: "12px",
                borderRadius: "50%",
                backgroundColor: "#dc2626",
                border: "1px solid #b91c1c",
                marginRight: "5px",
              }}
            />
            <span style={{ fontSize: "14px" }}>Puts ({puts.length})</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default VolSkewPlot;
