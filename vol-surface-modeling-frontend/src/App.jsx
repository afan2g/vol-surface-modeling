import { useEffect, useState } from "react";
import reactLogo from "./assets/react.svg";
import viteLogo from "/vite.svg";
import "./App.css";
import Dropdown from "./components/Dropdown.jsx";
import OptionChainTable from "./components/OptionChainTable.jsx";
const HOST = "http://127.0.0.1:5000";
function App() {
  const [count, setCount] = useState(0);
  const [availableAssets, setAvailableAssets] = useState([]);
  const [assetSpotPrices, setAssetSpotPrices] = useState([]);
  const [availableExpiries, setAvailableExpiries] = useState([]);
  const [expiryObject, setExpiryObject] = useState({});
  const [availableStrikes, setAvailableStrikes] = useState([]);
  const [selectedAsset, setSelectedAsset] = useState("");
  const [selectedExpiry, setSelectedExpiry] = useState("");
  const [selectedStrike, setSelectedStrike] = useState("");
  const [selectedOptionType, setSelectedOptionType] = useState("");
  const [optionData, setOptionData] = useState([]);
  const [optionDataLoading, setOptionDataLoading] = useState(false);
  const [optionDataError, setOptionDataError] = useState(null);
  const [optionDataSuccess, setOptionDataSuccess] = useState(false);

  useEffect(() => {
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
        setExpiryObject(
          expiriesData.expiries.reduce((obj, expiry) => {
            const date = new Date(expiry[0]).toLocaleDateString();
            obj[date] = expiry[1];
            return obj;
          })
        );
        setAvailableExpiries(
          expiriesData.expiries.map((expiry) =>
            new Date(expiry[0]).toLocaleDateString()
          )
        );
        console.log("Available assets:", assetsData);
        console.log("Available expiries:", expiriesData);
      } catch (error) {
        console.error("Error fetching assets:", error);
      }
    };
    fetchAssets();
  }, []);

  useEffect(() => {
    const fetchStrikes = async () => {
      if (selectedAsset && selectedExpiry && selectedOptionType) {
        try {
          const response = await fetch(`${HOST}/api/strikes`, {
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
          setAvailableStrikes(data.strikes);
          console.log("Available strikes:", data.strikes);
        } catch (error) {
          console.error("Error fetching strikes:", error);
        }
      }
    };
    fetchStrikes();
  }, [selectedAsset, selectedExpiry, selectedOptionType]);

  const handleExpiryChange = (expiry) => {
    setSelectedExpiry(expiryObject[expiry]);
    console.log("Selected expiry:", expiryObject[expiry]);
  };

  const handleAssetChange = (asset) => {
    setSelectedAsset(asset);
    console.log("Selected asset:", asset);
  };

  const handleOptionsChainFetch = async () => {
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
          onSelect={setSelectedAsset}
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
        />
        <button
          onClick={handleOptionsChainFetch}
          disabled={!selectedAsset || !selectedExpiry || !selectedOptionType}
        >
          Fetch Options Chain
        </button>
      </div>
      {optionData["C"] && <OptionChainTable optionChain={optionData["C"]} />}
      {optionData["P"] && <OptionChainTable optionChain={optionData["P"]} />}
    </div>
  );
}

export default App;
