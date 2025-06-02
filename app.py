import requests
from dotenv import load_dotenv
import os
import json
import pprint
from decimal import Decimal, getcontext
import time
from scipy.stats import norm
from scipy.optimize import curve_fit, minimize
import math
import matplotlib.pyplot as plt
from flask import Flask, jsonify, request
from flask_cors import CORS
import numpy as np
getcontext().prec = 20
class Binance:
    def __init__(self, proxy=None):
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
        self.expiry_dates = {}
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
            if asset not in self.expiry_dates:
                self.expiry_dates[asset] = set()
            self.expiry_dates[asset].add((expiry_timestamp, expiry))
        for asset in self.option_markets:
            for expiry in self.option_markets[asset]:
                self.option_markets[asset][expiry]['C'] = sorted(self.option_markets[asset][expiry]['C'], key=lambda x: x['strikePrice'])
                self.option_markets[asset][expiry]['P'] = sorted(self.option_markets[asset][expiry]['P'], key=lambda x: x['strikePrice'])
            self.expiry_dates[asset] = sorted(self.expiry_dates[asset], key=lambda x: x[0])
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
                time_to_expiry = option['time_to_expiry']
                implied_volatility = Decimal(mark_iv)
                total_implied_variance = float(implied_volatility)**2 * time_to_expiry
                mark_data = {
                    'mark_price': mark_price,
                    'mark_iv': mark_iv,
                    'risk_free_rate': risk_free_rate,
                    'log_moneyness': Decimal(spot_price/strike_price).ln(),
                    'moneyness': Decimal(spot_price/strike_price),
                    'total_implied_variance': total_implied_variance,
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
    
    def moneyness_array(self, asset, expiry, side):
        if asset not in self.option_markets:
            return None
        if expiry not in self.option_markets[asset]:
            return None
        if side not in 'CPA':
            return None
        if side == 'A':
            call_options = self.option_markets[asset][expiry]['C']
            put_options = self.option_markets[asset][expiry]['P']
            options_list = call_options + put_options
        else:
            options_list = self.option_markets[asset][expiry][side]
        k = np.array([float(option['log_moneyness']) for option in options_list])
        total_implied_variances = np.array([float(option['total_implied_variance']) for option in options_list])
        return k, total_implied_variances
    
    def raw_svi(self, k, a, b, rho, m, sigma):
        return a + b * (rho * (k - m) + np.sqrt((k - m)**2 + sigma**2))
    
    def natural_svi(self, k, delta, mu, rho, omega, zeta):
        return delta + (omega/2) * (1 + (zeta*rho*(k - mu)) + np.sqrt((zeta*(k-mu) + rho) ** 2 + (1 - rho**2)))
    
    
    def raw_to_svi_jw(a, b, rho, m, sigma, t):
        sqrt_term = np.sqrt(m**2 + sigma**2)
        vt = (a + b * (-rho * m + sqrt_term)) / t
        wt = vt * t
        psit = (b / (2 * np.sqrt(wt))) * (-m / sqrt_term + rho)
        pt = (b / np.sqrt(wt)) * (1 - rho)
        ct = (b / np.sqrt(wt)) * (1 + rho)
        vt_min = (a + b * sigma * np.sqrt(1 - rho**2)) / t
        return {'vt': vt, 'psit': psit, 'pt': pt, 'ct': ct, 'vt_min': vt_min}

    def svi_jw_to_raw(vt, psit, pt, ct, vt_min, t):
        wt = vt * t
        b = 0.5 * np.sqrt(wt) * (pt + ct)
        rho = (ct - pt) / (ct + pt)
        m = -sigma * (psit * 2 * np.sqrt(wt) / b - rho)
        sigma = (vt_min * t - a) / (b * np.sqrt(1 - rho**2))
        a = vt * t - b * (-rho * m + np.sqrt(m**2 + sigma**2))
        return {'a': a, 'b': b, 'rho': rho, 'm': m, 'sigma': sigma}
    
    def raw_svi_paramterization(self, asset, expiry, side):
        """
        Using svi_model function, we try to find the best-fit parameters a, b, rho, m, sigma that minimizes the difference between the model's calculated total implied variance and the actual total implied variance from the option chain.
        each option in the option chain comes pre-calculated with its own total implied variance.
        """
        k, total_implied_variances = self.moneyness_array(asset, expiry, side)
        
        # Initial guess for the parameters a, b, rho, m, sigma
        initial_guess = [total_implied_variances.mean(), 0.5, 0.0, k.mean(), 0.1]
        # Bounds for the parameters a, b, rho, m, sigma
        # a: all real numbers, b >= 0, rho: [-1, 1], m: all real numbers, sigma > 0
        bounds = ([-np.inf, 0, -0.999, -np.inf, 0.001], 
                  [np.inf, np.inf, 0.999, np.inf, np.inf])
        try:
            params, _ = curve_fit(self.raw_svi, k, total_implied_variances, p0=initial_guess, bounds=bounds, maxfev=10000)
        except Exception as e:
            print(f"Error during SVI fit: {e}")
            return None
        return params
    
    def natural_svi_paramterization(self, asset, expiry, side):
        k, total_implied_variances = self.moneyness_array(asset, expiry, side)
        # Initial guess for the parameters delta, mu, rho, omega, zeta
        initial_guess = [total_implied_variances.mean(), k.mean(), 0.0, 0.5, 0.1]
        # Bounds for the parameters delta, mu, rho, omega, zeta
        # delta: all real numbers, mu: all real numbers, rho: [-1, 1], omega >= 0, zeta > 0
        bounds = ([-np.inf, -np.inf, -0.999, 0, 0.001], 
                  [np.inf, np.inf, 0.999, np.inf, np.inf])
        
        try:
            params, _ = curve_fit(self.natural_svi, k, total_implied_variances, p0=initial_guess, bounds=bounds, maxfev=10000)
        except Exception as e:
            print(f"Error during SVI fit: {e}")
            return None
        return params
    
    def svi_jw_paramterization(self, asset, expiry, side):
        a, b, rho, m, sigma = self.raw_svi_paramterization(asset, expiry, side)
        # Convert raw SVI parameters to JW parameters
        t = self.option_markets[asset][expiry]['C'][0]['time_to_expiry'] if side == 'C' else self.option_markets[asset][expiry]['P'][0]['time_to_expiry']
        svi_params = self.raw_to_svi_jw(a, b, rho, m, sigma, t)
        return svi_params['vt'], svi_params['psit'], svi_params['pt'], svi_params['ct'], svi_params['vt_min']
    
    def get_svi_curve_points(self, asset, expiry, side, paramterization_type='raw'):
        """
        Get SVI curve points for a given asset, expiry, and side.
        :param asset: Asset to get SVI curve points for
        :param expiry: Expiry to get SVI curve points for
        :param side: Side to get SVI curve points for
        :return: SVI curve points
        """
        if paramterization_type not in ['raw', 'natural']:
            raise ValueError("Invalid parameterization type. Use 'raw' or 'natural'.")
        if paramterization_type == 'natural':
            params = self.natural_svi_paramterization(asset, expiry, side)
            delta, mu, rho, omega, zeta = params
        elif paramterization_type == 'raw':
            params = self.raw_svi_paramterization(asset, expiry, side)
            a, b, rho, m, sigma = params
        
        k = []
        if side == 'A':
            call_options = self.option_markets[asset][expiry]['C']
            put_options = self.option_markets[asset][expiry]['P']
            options_list = call_options + put_options
            k = [float(option['log_moneyness']) for option in call_options + put_options]
        else:
            options_list = self.option_markets[asset][expiry][side]
            k = [float(option['log_moneyness']) for option in options_list]
        options_list = [(option['log_moneyness'], option['markIV']) for option in options_list if 'markIV' in option]
        x_points = np.linspace(min(k)-0.1, max(k)+0.1, 100)  # Adjust range as needed
        if paramterization_type == 'natural':
            svi_values = self.natural_svi(x_points, delta, mu, rho, omega, zeta)
        elif paramterization_type == 'raw':
            svi_values = self.raw_svi(x_points, a, b, rho, m, sigma)
        points = []
        time_to_expiry = self.option_markets[asset][expiry]['C'][0]['time_to_expiry'] if side == 'C' else self.option_markets[asset][expiry]['P'][0]['time_to_expiry']
        implied_vols = np.sqrt(svi_values / time_to_expiry)  # Convert total implied variance to implied volatility
        self.get_spot_markets()
        spot_price = Decimal(self.spot_prices[self.underlyings[asset]])
        for k_val, iv in zip(x_points, implied_vols):
            strike = spot_price / Decimal(math.exp(k_val))
            moneyness = Decimal(math.exp(k_val))
            points.append({
                'logMoneyness': float(k_val),
                'strikePrice': float(strike),
                'moneyness': float(moneyness),
                'impliedVolatility': float(iv),
            })
        return points
                
        
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

@app.route('/api/expiries', methods=['GET', 'POST'])
def get_available_expiries():
    if request.method == 'POST':
        data = request.get_json()
        asset = data.get('asset')
    else:
        asset = request.args.get('asset')
    if not asset:
        return jsonify(BinanceAPI.expiry_dates)
    if asset not in BinanceAPI.expiry_dates:
        return jsonify({'error': 'Asset not found'}), 404
    expiries = list(BinanceAPI.expiry_dates[asset])
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
    if side == 'A':
        call_strikes = [option['strikePrice'] for option in BinanceAPI.option_markets[asset][expiry]['C']]
        put_strikes = [option['strikePrice'] for option in BinanceAPI.option_markets[asset][expiry]['P']]
        strikes = {'call': call_strikes, 'put': put_strikes}
    else:
        strikes = [option['strikePrice'] for option in BinanceAPI.option_markets[asset][expiry][side]]
    return jsonify({'strikes': strikes})


@app.route('/api/svi_curve', methods=['GET', 'POST'])
def get_svi_curve():
    if request.method == 'POST':
        data = request.get_json()
        asset = data.get('asset')
        expiry = data.get('expiry')
        side = data.get('side')
        parameterization_type = data.get('parameterization_type', 'raw')
    else:
        asset = request.args.get('asset')
        expiry = request.args.get('expiry')
        side = request.args.get('side')
        parameterization_type = request.args.get('parameterization_type', 'raw')
    try:
        points = BinanceAPI.get_svi_curve_points(asset, expiry, side, parameterization_type)
    except Exception as e:
        print(f"Error calculating SVI curve: {e}")
        return jsonify({'error': 'Failed to calculate SVI curve'}), 500
    
    if points is None:
        return jsonify({'error': 'Failed to calculate SVI curve'}), 500
    return jsonify({'points': points})

@app.route("/")
def index():
    return "Hello from Flask on Render!"

if __name__ == "__main__":
    BinanceAPI = Binance()
    app.run(debug=True, port=5000)

