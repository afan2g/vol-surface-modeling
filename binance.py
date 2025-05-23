import requests
from dotenv import load_dotenv
import os
import json
import pprint
from decimal import Decimal, getcontext
import time
from scipy.stats import norm
import math
import matplotlib.pyplot as plt
from flask import Flask, jsonify, request
from flask_cors import CORS

getcontext().prec = 20
class Binance:
    def __init__(self, proxy):
        self.derivatives_base_endpoint = "https://eapi.binance.com"
        self.spot_base_endpoint = "https://api.binance.com"
        self.endpoints = {
            "time": self.derivatives_base_endpoint+"/eapi/v1/time",
            "ping": self.derivatives_base_endpoint+"/eapi/v1/ping",
            "info": self.derivatives_base_endpoint+"/eapi/v1/exchangeInfo",
            "orderbook": self.derivatives_base_endpoint+"/eapi/v1/depth",
            "mark": self.derivatives_base_endpoint+"/eapi/v1/mark",
            "open_interest": self.derivatives_base_endpoint+"/eapi/v1/openInterest",
            "spot": self.spot_base_endpoint+"/api/v3/ticker/price",
        }
        self.proxies = {
            "http": proxy,
            "https": proxy
        }

        self.market_info = {}
        self.option_markets = {}
        self.spot_prices = {}
        self.underlyings = {}
        self.expiry_dates = []
        self.cur_time = time.time() * 1000
        self.get_market_info()
        self.get_spot_markets()
        self.get_options()
        self.insert_mark_info()

    def get_orderbook(self, symbol, limit=100):
        """
        Get order book for a symbol
        :param symbol: Symbol to get order book for
        :param limit: Limit of order book
        :return: Order book
        """
        params = {
            "symbol": symbol,
            "limit": limit
        }
        response = requests.get(self.endpoints['orderbook'], params=params, proxies=self.proxies)
        return response.json()
    
    def get_spot_markets(self):
        """
        Get spot markets
        :return: Spot markets
        """
        response = requests.get(self.endpoints['spot'], proxies=self.proxies)
        data = response.json()
        for item in data:
            symbol = item['symbol']
            price = Decimal(item['price'])
            self.spot_prices[symbol] = price
        return self.spot_prices

    def get_marks(self):
        """
        Get mark price for a symbol
        :param symbol: Symbol to get mark price for
        :return: Mark price
        """
        response = requests.get(self.endpoints['mark'], proxies=self.proxies)
        return response.json()

    def get_options(self):
        """
        Get option symbols
        :return: Option symbols
        """
        info = self.market_info

        dates = set()
        for symbol in info['optionSymbols']:
            expiry_timestamp, underlying, strike_price = symbol['expiryDate'], symbol['underlying'], symbol['strikePrice']
            asset, expiry, strike, side = symbol['symbol'].split('-')
            time_diff_ms = expiry_timestamp - self.cur_time
            days_to_expiry = time_diff_ms / (1000 * 60 * 60 * 24)
            self.underlyings[asset] = underlying
            if asset not in self.option_markets:
                self.option_markets[asset] = {}
            if expiry not in self.option_markets[asset]:
                self.option_markets[asset][expiry] = {'C': [], 'P': []}
            self.option_markets[asset][expiry][side].append({
                "symbol": symbol['symbol'],
                "strikePrice": Decimal(strike_price),
                "expiry": expiry_timestamp,
                "time_to_expiry_ms": expiry_timestamp - self.cur_time,
                "days_to_expiry": (expiry_timestamp - self.cur_time) / (1000 * 60 * 60 * 24),
                "time_to_expiry": days_to_expiry/365.25,
                "underlying": underlying,
            })
            dates.add((expiry_timestamp, expiry))
        
        for asset in self.option_markets:
            for expiry in self.option_markets[asset]:
                self.option_markets[asset][expiry]['C'] = sorted(self.option_markets[asset][expiry]['C'], key=lambda x: x['strikePrice'])
                self.option_markets[asset][expiry]['P'] = sorted(self.option_markets[asset][expiry]['P'], key=lambda x: x['strikePrice'])
        self.expiry_dates = list(dates)
        self.expiry_dates.sort(key=lambda x: x[0])
        return self.underlyings, self.option_markets

    def get_market_info(self):
        """
        Get market info
        :return: Market info
        """
        if len(self.market_info) == 0:
            response = requests.get(self.endpoints['info'], proxies=self.proxies)
            self.market_info = response.json()
        return self.market_info
    
    def get_endpoint(self, endpoint, params=None):
        """
        Get endpoint
        :param endpoint: Endpoint to get
        :return: Endpoint
        """
        response = requests.get(self.endpoints[endpoint], params=params, proxies=self.proxies)
        return response.json()
    
    def get_option_info(self, symbol):
        """
        Get option info
        :param symbol: Symbol to get option info for
        :return: Option info
        """
        response = requests.get(self.endpoints['mark'], params={'symbol': symbol}, proxies=self.proxies)
        return response.json()
    def insert_mark_info(self):
        mark_info = self.get_marks()
        for data in mark_info:
            symbol = data['symbol']
            mark_price = data['markPrice']
            mark_iv = data['markIV']
            risk_free_rate = data['riskFreeInterest']
            asset, expiry, strike, side = symbol.split('-')
            idx = self.find_mark_index(asset, expiry, strike, side)
            if idx is not None:
                option = self.option_markets[asset][expiry][side][idx]
                underlying = option['underlying']
                strike_price = option['strikePrice']
                spot_price = Decimal(self.spot_prices[underlying])
                mark_data = {
                    'mark_price': mark_price,
                    'mark_iv': mark_iv,
                    'risk_free_rate': risk_free_rate,
                    'log_moneyness': Decimal(spot_price/strike_price).ln(),
                    'moneyness': Decimal(spot_price/strike_price),
                }
                self.option_markets[asset][expiry][side][idx].update(mark_data)
            else:
                print(f"Mark info not found for {symbol}")
    

    def find_mark_index(self, asset, expiry, strike, side):
        """
        Find mark index
        :param asset: Asset to find mark index for
        :param expiry: Expiry to find mark index for
        :param strike: Strike to find mark index for
        :param side: Side to find mark index for
        :return: Mark index
        """
        if asset not in self.option_markets:
            return None
        if expiry not in self.option_markets[asset]:
            return None
        if side not in self.option_markets[asset][expiry]:
            return None
        options_list = self.option_markets[asset][expiry][side]
        if not options_list:
            return None
        l,r = 0, len(self.option_markets[asset][expiry][side]) - 1
        target = Decimal(str(strike))
        while l <= r:
            mid = (l + r) // 2
            mid_strike = options_list[mid]['strikePrice']
            if mid_strike == target:
                return mid
            elif mid_strike < target:
                l = mid + 1
            else:
                r = mid - 1
        return None
    def filter_options(self, asset=None, expiry=None, side=None):
        """
        Filter options
        :param asset: Asset to filter options for
        :param expiry: Expiry to filter options for
        :param side: Side to filter options for
        :return: Filtered options
        """
        if asset not in self.option_markets:
            return self.option_markets
        if expiry is None:
            return self.option_markets[asset]
        if side is None:
            return self.option_markets[asset][expiry]
        return self.option_markets[asset][expiry][side]
    



    def calculate_option_price(self, S, K, T, r, sigma, option_type='C'):
        """
        Calculate Black-Scholes option price.
        :param S: Spot price
        :param K: Strike price
        :param T: Time to maturity (in years)
        :param r: Risk-free interest rate
        :param sigma: Volatility
        :param option_type: 'C' for Call, 'P' for Put
        :return: Option price as Decimal
        """

        S, K, T, r, sigma = map(Decimal, (S, K, T, r, sigma))

        sqrt_T = T.sqrt()
        d1 = ((S / K).ln() + (r + sigma**2 / 2) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T

        # Convert to float for CDF calls
        d1_f = float(d1)
        d2_f = float(d2)
        rT_f = float(-r * T)

        if option_type == 'C':
            price = S * Decimal(norm.cdf(d1_f)) - K * Decimal(math.exp(rT_f)) * Decimal(norm.cdf(d2_f))
        elif option_type == 'P':
            price = K * Decimal(math.exp(rT_f)) * Decimal(norm.cdf(-d2_f)) - S * Decimal(norm.cdf(-d1_f))
        else:
            raise ValueError("Invalid option type. Use 'C' for call and 'P' for put.")
        
        return price
            
    def get_option_chain(self, asset, expiry, side):
        """
        Display option chain
        :param asset: Asset to display option chain for
        :param expiry: Expiry to display option chain for
        :param side: Side to display option chain for
        :return: Option chain
        """
        if asset not in self.option_markets:
            return None
        if expiry not in self.option_markets[asset]:
            return None
        if side not in self.option_markets[asset][expiry] and side != 'A':
            return None
        res = {}
        if side == 'A':
            call_options = self.option_chain(asset, expiry, 'C')
            put_options = self.option_chain(asset, expiry, 'P')
            res = {'C': call_options, 'P': put_options}
        else:
            chain = self.option_chain(asset, expiry, side)
            res = {side: chain}
        return res
    
    def option_chain(self, asset, expiry, side):
        """
        Display option chain
        :param asset: Asset to display option chain for
        :param expiry: Expiry to display option chain for
        :param side: Side to display option chain for
        :return: Option chain
        """
        options_list = self.option_markets[asset][expiry][side]
        res = []
        for option in options_list:
            symbol = option['symbol']
            mark_price = option['mark_price']
            mark_iv = option['mark_iv']
            risk_free_rate = option['risk_free_rate']
            strike_price = option['strikePrice']
            time_to_expiry = option['time_to_expiry']
            days_to_expiry = option['days_to_expiry']
            moneyness = option['moneyness']
            log_moneyness = option['log_moneyness']
            spot_price = Decimal(self.spot_prices[option['underlying']])
            bsm_price = self.calculate_option_price(spot_price, strike_price, time_to_expiry, risk_free_rate, mark_iv, side)
            res.append({
                'symbol': symbol,
                'strikePrice': strike_price,
                'markPrice': mark_price,
                'markIV': mark_iv,
                'riskFreeRate': risk_free_rate,
                'timeToExpiry': time_to_expiry,
                'daysToExpiry': days_to_expiry,
                'moneyness': moneyness,
                'logMoneyness': log_moneyness,
                'spotPrice': spot_price,
                'bsmPrice': bsm_price,
            })
        return res
def main():

    load_dotenv()
    proxy = os.getenv("PROXY")
    BinanceAPI = Binance(proxy)
    

    call_strikes, call_ivs = BinanceAPI.display_option_chain('BTC', '251226', 'C')
    put_strikes, put_ivs = BinanceAPI.display_option_chain('BTC', '251226', 'P')
    plt.scatter(call_strikes, call_ivs, marker='o', color='blue')
    plt.scatter(put_strikes, put_ivs, marker='x', color='red')
    plt.legend(['Call Options', 'Put Options'])
    plt.title(f"Implied Volatility for BTCUSDT Options on 2023-10-25")
    plt.xlabel("Strike Price")
    plt.ylabel("Implied Volatility")
    plt.grid()
    plt.show()

app = Flask(__name__)
CORS(app)

@app.route('/api/option_chain', methods=['GET', 'POST'])
def get_option_chain():
    if request.method == 'POST':
        data = request.get_json()
        asset = data.get('asset')
        expiry = data.get('expiry')
        side = data.get('side')
    else:
        asset = request.args.get('asset')
        expiry = request.args.get('expiry')
        side = request.args.get('side')
    chain = BinanceAPI.get_option_chain(asset, expiry, side)
    return jsonify(chain)

@app.route('/api/assets', methods=['GET'])
def get_available_assets():
    assets = list(BinanceAPI.option_markets.keys())
    spot_prices = {}
    for asset in assets:
        spot_prices[asset] = BinanceAPI.spot_prices[BinanceAPI.underlyings[asset]]
    return jsonify({'assets': assets, 'spot_prices': spot_prices})

@app.route('/api/expiries', methods=['GET'])
def get_available_expiries():
    expiries = list(BinanceAPI.expiry_dates)
    return jsonify({'expiries': expiries})

@app.route('/api/strikes', methods=['GET', 'POST'])
def get_available_strikes():
    if request.method == 'POST':
        data = request.get_json()
        asset = data.get('asset')
        expiry = data.get('expiry')
        side = data.get('side')
    else:
        asset = request.args.get('asset')
        expiry = request.args.get('expiry')
        side = request.args.get('side')
    print(f"Asset: {asset}, Expiry: {expiry}, Side: {side}")
    print(BinanceAPI.option_markets[asset][expiry])
    if side == 'A':
        call_strikes = [option['strikePrice'] for option in BinanceAPI.option_markets[asset][expiry]['C']]
        put_strikes = [option['strikePrice'] for option in BinanceAPI.option_markets[asset][expiry]['P']]
        strikes = {'call': call_strikes, 'put': put_strikes}
    else:
        strikes = [option['strikePrice'] for option in BinanceAPI.option_markets[asset][expiry][side]]
    return jsonify({'strikes': strikes})


if __name__ == "__main__":
    load_dotenv()
    proxy = os.getenv("PROXY")
    BinanceAPI = Binance(proxy)
    app.run(debug=True, port=5000)

