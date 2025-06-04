import requests
import dotenv
import os
from flask import Flask, jsonify
dotenv.load_dotenv()
proxy = os.getenv("PROXY")

example_url = "https://httpbin.org/ip"
binance_url = "https://eapi.binance.com/eapi/v1/time"
def test_proxy():
    res = requests.get(binance_url, proxies={"http": proxy, "https": proxy})
    return res.json()

res = test_proxy()
print(res)




