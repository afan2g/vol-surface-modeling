import { useEffect, useState } from "react";
import reactLogo from "./assets/react.svg";
import viteLogo from "/vite.svg";
import "./App.css";
import Dropdown from "./components/Dropdown.jsx";
import OptionChainTable from "./components/OptionChainTable.jsx";
import VolSkewPlot from "./components/VolSkewPlot.jsx";
import { Tooltip } from "./components/Tooltip.jsx";
const HOST = "http://127.0.0.1:5000";
function App() {
  const [count, setCount] = useState(0);
  const [availableAssets, setAvailableAssets] = useState([]);
  const [assetSpotPrices, setAssetSpotPrices] = useState([]);
  const [availableExpiries, setAvailableExpiries] = useState([]);
  const [expiryObject, setExpiryObject] = useState({});
  const [selectedAsset, setSelectedAsset] = useState("");
  const [selectedExpiry, setSelectedExpiry] = useState("");
  const [selectedOptionType, setSelectedOptionType] = useState("");
  const [optionData, setOptionData] = useState([]);
  const [showOptionsChain, setShowOptionsChain] = useState(false);
  const [showVolSkew, setShowVolSkew] = useState(false);
  const [volSkewAxis, setVolSkewAxis] = useState("moneyness");
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [optionDataLoading, setOptionDataLoading] = useState(false);
  const [optionDataError, setOptionDataError] = useState(null);
  const [optionDataSuccess, setOptionDataSuccess] = useState(false);

  useEffect(() => {
    fetchAssets();
  }, []);

  useEffect(() => {
    if (selectedAsset && selectedExpiry && selectedOptionType) {
      fetchOptionsData();
    }
  }, [selectedAsset, selectedExpiry, selectedOptionType]);

  const fetchAssets = async () => {
    try {
      const [assetsResponse, expiriesResponse] = await Promise.all([
        fetch(`${HOST}/api/assets`),
        fetch(`${HOST}/api/expiries`),
      ]);
      if (!assetsResponse.ok || !expiriesResponse.ok) {
        throw new Error("Network response was not ok");
      }
      const [assetsData, expiriesData] = await Promise.all([
        assetsResponse.json(),
        expiriesResponse.json(),
      ]);
      setAvailableAssets(assetsData.assets);
      setAssetSpotPrices(assetsData.spot_prices);
      setExpiryObject(expiriesData);
      console.log("Available assets:", assetsData);
      console.log("Available expiries:", expiriesData);
    } catch (error) {
      console.error("Error fetching assets:", error);
    }
  };

  const handleExpiryChange = (expiry) => {
    console.log("Expiry selected:", expiry);
    setSelectedExpiry(expiry[1]);
  };

  const handleAssetChange = (asset) => {
    if (asset === selectedAsset) {
      return;
    }
    setSelectedAsset(asset);
    console.log("Asset selected:", asset);
    console.log("Expiry object:", expiryObject);
    setAvailableExpiries(expiryObject[asset]);
  };

  const fetchOptionsData = async () => {
    if (selectedAsset && selectedExpiry && selectedOptionType) {
      setOptionDataLoading(true);
      setOptionDataError(null);
      setOptionDataSuccess(false);
      try {
        const response = await fetch(`${HOST}/api/option_chain`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            asset: selectedAsset,
            expiry: selectedExpiry,
            side: selectedOptionType.toUpperCase()[0],
          }),
        });
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        const data = await response.json();
        setOptionData(data);

        let strikes = [];
        if (data["C"]) {
          strikes = data["C"].map((option) => option.strikePrice);
        }
        if (data["P"]) {
          strikes = [
            ...strikes,
            ...data["P"].map((option) => option.strikePrice),
          ];
        }
        strikes = [...new Set(strikes)];
        strikes.sort((a, b) => parseFloat(a) - parseFloat(b));
        setOptionDataSuccess(true);
        console.log("Options chain data:", data);
      } catch (error) {
        setOptionDataError(error.message);
        console.error("Error fetching options chain:", error);
      } finally {
        setOptionDataLoading(false);
      }
    }
  };

  const handleShowOptionsChain = () => {
    setShowOptionsChain(true);
    setShowVolSkew(false);
  };
  const handleShowVolSkew = () => {
    setShowOptionsChain(false);
    setShowVolSkew(true);
  };
  return (
    <div
      style={{
        width: "50vw",
        padding: 0,
        margin: 0,
        flexDirection: "column",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div>
        <Dropdown
          onSelect={handleAssetChange}
          options={availableAssets}
          placeholder="Select an asset"
          text={
            assetSpotPrices[selectedAsset]
              ? ` ($${parseFloat(assetSpotPrices[selectedAsset]).toFixed(2)})`
              : null
          }
        />
        <Dropdown
          onSelect={handleExpiryChange}
          options={availableExpiries}
          placeholder="Select an expiry"
        />
        <Dropdown
          onSelect={setSelectedOptionType}
          options={["call", "put", "all"]}
          placeholder="Select option type"
          disabled={!selectedAsset}
        />
        <button
          onClick={handleShowOptionsChain}
          disabled={!selectedAsset || !selectedExpiry || !selectedOptionType}
        >
          Show Options Chain
        </button>
        <button
          onClick={handleShowVolSkew}
          disabled={!selectedAsset || !selectedExpiry || !selectedOptionType}
        >
          Show Volatility Skew
        </button>
      </div>
      {showVolSkew && (
        <div style={{ position: "relative" }}>
          <VolSkewPlot
            data={optionData}
            xAxis={volSkewAxis}
            setHoveredPoint={setHoveredPoint}
          />
          <Tooltip interactionData={hoveredPoint} />
          <Dropdown
            onSelect={setVolSkewAxis}
            options={["moneyness", "logMoneyness", "strikePrice"]}
            defaultValue="moneyness"
          />
        </div>
      )}
      {showOptionsChain && optionData["C"] && (
        <OptionChainTable optionChain={optionData["C"]} />
      )}
      {showOptionsChain && optionData["P"] && (
        <OptionChainTable optionChain={optionData["P"]} />
      )}
    </div>
  );
}

export default App;
